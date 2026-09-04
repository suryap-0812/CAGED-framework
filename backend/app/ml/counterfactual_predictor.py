"""
ML Counterfactual Predictor for CAGED.
Forecasts next 5-minute expected no-intervention metric rate Y_hat_{m, t+1}^{counterfactual}
using a 5-minute historical feature window (t - Delta t -> t).

Strict Independence & Zero Leakage Rules:
- Trained strictly on pre-policy (T < T0) and Control cohort telemetry observations.
- Contains ZERO hidden simulator policy state, policy IDs, impact factors, or CAGED detector results.
- Parallel analytical branch independent from core CAGED detector.
"""

from datetime import datetime, timezone
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.ingestion.models import EngagementEvent, MetricType
from app.detection.window_aggregator import WindowAggregator, WindowedMetricPoint

logger = get_logger(__name__)

# Fallback import for XGBoost vs sklearn GradientBoostingRegressor
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    from sklearn.ensemble import GradientBoostingRegressor

from sklearn.metrics import mean_squared_error, r2_score


COUNTERFACTUAL_FEATURE_NAMES: List[str] = [
    "hist_views_per_min",
    "hist_likes_per_view",
    "hist_comments_per_view",
    "hist_shares_per_view",
    "hist_clicks_per_view",
    "hist_avg_session_duration",
    "like_rate_of_change",
    "comment_rate_of_change",
    "diurnal_sin",
    "diurnal_cos",
]


class CounterfactualFeatureVector(BaseModel):
    """Features extracted from a 5-minute historical window (t - Delta t -> t)."""

    window_start: datetime = Field(..., description="UTC start of historical feature window")
    hist_views_per_min: float = Field(default=0.0)
    hist_likes_per_view: float = Field(default=0.0)
    hist_comments_per_view: float = Field(default=0.0)
    hist_shares_per_view: float = Field(default=0.0)
    hist_clicks_per_view: float = Field(default=0.0)
    hist_avg_session_duration: float = Field(default=0.0)
    like_rate_of_change: float = Field(default=0.0)
    comment_rate_of_change: float = Field(default=0.0)
    diurnal_sin: float = Field(default=0.0)
    diurnal_cos: float = Field(default=1.0)

    def to_numpy(self) -> np.ndarray:
        return np.array(
            [
                self.hist_views_per_min,
                self.hist_likes_per_view,
                self.hist_comments_per_view,
                self.hist_shares_per_view,
                self.hist_clicks_per_view,
                self.hist_avg_session_duration,
                self.like_rate_of_change,
                self.comment_rate_of_change,
                self.diurnal_sin,
                self.diurnal_cos,
            ],
            dtype=np.float64,
        )


class CounterfactualPredictionResult(BaseModel):
    """Counterfactual prediction output for a metric in the next 5-minute window."""

    timestamp: datetime = Field(..., description="UTC forecast target window start time")
    target_metric: MetricType = Field(..., description="Target metric type being predicted")
    counterfactual_expected_rate: float = Field(..., description="Predicted no-intervention rate Y_hat_{t+1}")
    historical_observed_rate: float = Field(..., description="Current window observed rate Y_t")
    feature_importances: Dict[str, float] = Field(default_factory=dict)
    model_version: str = Field(default="xgboost-counterfactual-v1.0")


class CounterfactualMLPredictor:
    """
    ML Counterfactual Predictor forecasting no-intervention engagement trajectory.
    """

    def __init__(self, target_metric: MetricType = MetricType.LIKE, random_state: int = 42):
        self.target_metric = target_metric
        self.random_state = random_state
        self.is_trained: bool = False
        self.aggregator = WindowAggregator(window_size_minutes=5)

        if XGBOOST_AVAILABLE:
            self.model = xgb.XGBRegressor(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=random_state,
            )
            self.model_version = "xgboost-counterfactual-v1.0"
        else:
            self.model = GradientBoostingRegressor(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=random_state,
            )
            self.model_version = "gradient_boosting_fallback-counterfactual-v1.0"

    def _extract_feature_vectors(
        self, window_points: List[WindowedMetricPoint]
    ) -> Tuple[np.ndarray, np.ndarray, List[CounterfactualFeatureVector]]:
        """
        Extracts 5-minute historical feature vectors (t - Delta t -> t)
        and next-window targets Y_{t+1} from windowed points.
        """
        features: List[CounterfactualFeatureVector] = []
        targets: List[float] = []

        for i in range(1, len(window_points) - 1):
            curr_pt = window_points[i]
            prev_pt = window_points[i - 1]
            next_pt = window_points[i + 1]

            t_utc = curr_pt.window_start
            if t_utc.tzinfo is None:
                t_utc = t_utc.replace(tzinfo=timezone.utc)

            hour_val = t_utc.hour + (t_utc.minute / 60.0)
            sin_t = math.sin(2.0 * math.pi * hour_val / 24.0)
            cos_t = math.cos(2.0 * math.pi * hour_val / 24.0)

            l_curr = curr_pt.likes_per_view
            l_prev = prev_pt.likes_per_view
            l_roc = l_curr - l_prev

            c_curr = curr_pt.comments_per_view
            c_prev = prev_pt.comments_per_view
            c_roc = c_curr - c_prev

            vec = CounterfactualFeatureVector(
                window_start=t_utc,
                hist_views_per_min=curr_pt.views_per_min,
                hist_likes_per_view=l_curr,
                hist_comments_per_view=c_curr,
                hist_shares_per_view=curr_pt.shares_per_view,
                hist_clicks_per_view=curr_pt.clicks_per_view,
                hist_avg_session_duration=curr_pt.avg_session_duration_sec,
                like_rate_of_change=round(l_roc, 4),
                comment_rate_of_change=round(c_roc, 4),
                diurnal_sin=round(sin_t, 4),
                diurnal_cos=round(cos_t, 4),
            )
            features.append(vec)
            targets.append(next_pt.get_metric_value(self.target_metric))

        if not features:
            return np.empty((0, len(COUNTERFACTUAL_FEATURE_NAMES))), np.empty((0,)), []

        X = np.array([f.to_numpy() for f in features], dtype=np.float64)
        y = np.array(targets, dtype=np.float64)
        return X, y, features

    def train_on_pre_policy_or_control(
        self,
        events: List[EngagementEvent],
        t0: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """
        Trains model strictly on pre-policy (T < T0) or Control cohort telemetry stream.
        Zero post-policy Treatment leakage allowed.
        """
        if not events:
            raise ValueError("Training telemetry stream cannot be empty.")

        # Filter: retain strictly pre-T0 events OR control cohort events
        filtered_events: List[EngagementEvent] = []
        for e in events:
            e_time = e.timestamp
            if e_time.tzinfo is None:
                e_time = e_time.replace(tzinfo=timezone.utc)

            cohort = e.segment_metadata.get("cohort") if e.segment_metadata else None
            is_pre = (t0 is None) or (e_time < t0)
            is_control = (cohort == "control")

            if is_pre or is_control:
                filtered_events.append(e)

        if len(filtered_events) < 10:
            raise ValueError("Insufficient pre-policy / control observations for training.")

        pts = self.aggregator.aggregate_stream(filtered_events)
        X, y, _ = self._extract_feature_vectors(pts)

        if len(X) < 5:
            raise ValueError("Insufficient feature windows generated for model fitting.")

        self.model.fit(X, y)
        self.is_trained = True

        y_pred = self.model.predict(X)
        rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
        r2 = float(r2_score(y, y_pred)) if len(y) > 5 else 1.0

        metrics = {
            "rmse": round(rmse, 4),
            "r2": round(r2, 4),
            "training_windows": len(X),
        }
        logger.info("Trained Counterfactual Predictor (%s) — RMSE: %.4f, R2: %.4f", self.model_version, rmse, r2)
        return metrics

    def predict_counterfactual(
        self, window_vector: CounterfactualFeatureVector
    ) -> CounterfactualPredictionResult:
        """
        Predicts expected counterfactual rate Y_hat_{t+1} for next window.
        Safe Fallback: If model is not trained, returns current observed rate.
        """
        eval_time = window_vector.window_start
        if eval_time.tzinfo is None:
            eval_time = eval_time.replace(tzinfo=timezone.utc)

        curr_rate = window_vector.hist_likes_per_view if self.target_metric == MetricType.LIKE else window_vector.hist_views_per_min

        if not self.is_trained:
            return CounterfactualPredictionResult(
                timestamp=eval_time,
                target_metric=self.target_metric,
                counterfactual_expected_rate=curr_rate,
                historical_observed_rate=curr_rate,
                feature_importances={},
                model_version=self.model_version,
            )

        try:
            X = np.array([window_vector.to_numpy()], dtype=np.float64)
            pred_rate = float(self.model.predict(X)[0])
            pred_rate = max(0.0, float(pred_rate))

            importances = self.get_feature_importances()
            return CounterfactualPredictionResult(
                timestamp=eval_time,
                target_metric=self.target_metric,
                counterfactual_expected_rate=round(pred_rate, 4),
                historical_observed_rate=round(curr_rate, 4),
                feature_importances=importances,
                model_version=self.model_version,
            )
        except Exception as err:
            logger.error("Counterfactual prediction failed: %s. Returning fallback.", str(err))
            return CounterfactualPredictionResult(
                timestamp=eval_time,
                target_metric=self.target_metric,
                counterfactual_expected_rate=curr_rate,
                historical_observed_rate=curr_rate,
                feature_importances={},
                model_version=self.model_version,
            )

    def get_feature_importances(self) -> Dict[str, float]:
        if not self.is_trained:
            return {}

        importances = getattr(self.model, "feature_importances_", np.zeros(len(COUNTERFACTUAL_FEATURE_NAMES)))
        imp_dict = {name: round(float(imp), 4) for name, imp in zip(COUNTERFACTUAL_FEATURE_NAMES, importances)}
        sorted_items = sorted(imp_dict.items(), key=lambda p: p[1], reverse=True)
        return dict(sorted_items)
