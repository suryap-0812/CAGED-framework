"""
Optional Early-Warning ML Degradation Predictor using XGBoost / Gradient Boosting.
"""

from datetime import datetime, timezone
import os
from typing import Dict, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.ml.dataset import ML_FEATURE_NAMES, MLFeatureVector

logger = get_logger(__name__)

# Fallback import for XGBoost vs sklearn GradientBoostingClassifier
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    from sklearn.ensemble import GradientBoostingClassifier

from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score


class MLPredictionResult(BaseModel):
    """Container for early-warning ML degradation prediction result."""

    timestamp: datetime = Field(..., description="UTC timestamp of evaluation")
    prediction_horizon_minutes: int = Field(default=15, description="Early warning forecast horizon in minutes")
    degradation_probability: float = Field(..., description="Predicted probability of degradation [0.0, 1.0]")
    warning_status: str = Field(..., description="Warning level ('NORMAL', 'WATCH', 'WARNING', 'CRITICAL')")
    feature_importances: Dict[str, float] = Field(default_factory=dict, description="Ranked feature importances")
    model_version: str = Field(default="xgboost-v1.0", description="Model framework identifier")


class XGBoostDegradationPredictor:
    """
    Optional early-warning degradation predictor.
    
    Guaranteed Rule: If ML fails, is un-trained, or is disabled, returns safe
    fallback probability 0.0 without interrupting core statistical CAGED.
    """

    def __init__(self, prediction_horizon_minutes: int = 15, random_state: int = 42):
        self.horizon_minutes = prediction_horizon_minutes
        self.random_state = random_state
        self.is_trained: bool = False

        if XGBOOST_AVAILABLE:
            self.model = xgb.XGBClassifier(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=random_state,
                eval_metric="logloss",
            )
            self.model_version = "xgboost-v1.0"
        else:
            self.model = GradientBoostingClassifier(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=random_state,
            )
            self.model_version = "gradient_boosting_fallback-v1.0"

    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Trains the early warning model and computes validation metrics.
        """
        if len(X) == 0 or len(y) == 0:
            raise ValueError("Training dataset X and y cannot be empty.")

        self.model.fit(X, y)
        self.is_trained = True

        y_pred = self.model.predict(X)
        y_prob = self.model.predict_proba(X)[:, 1] if hasattr(self.model, "predict_proba") else y_pred

        metrics = {
            "auc": round(float(roc_auc_score(y, y_prob)), 4) if len(set(y)) > 1 else 1.0,
            "precision": round(float(precision_score(y, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y, y_pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y, y_pred, zero_division=0)), 4),
        }

        logger.info(
            "Trained ML Degradation Predictor (%s) — AUC: %.4f, F1: %.4f",
            self.model_version, metrics["auc"], metrics["f1"]
        )
        return metrics

    def predict_degradation_probability(self, feature_vector: MLFeatureVector) -> MLPredictionResult:
        """
        Predicts early-warning degradation probability for horizon h minutes ahead.
        """
        eval_time = feature_vector.timestamp
        if eval_time.tzinfo is None:
            eval_time = eval_time.replace(tzinfo=timezone.utc)

        # Safe fallback if model is not trained or ML fails
        if not self.is_trained:
            return MLPredictionResult(
                timestamp=eval_time,
                prediction_horizon_minutes=self.horizon_minutes,
                degradation_probability=0.0,
                warning_status="NORMAL",
                feature_importances={},
                model_version=self.model_version,
            )

        try:
            X = np.array([feature_vector.to_numpy()], dtype=np.float64)
            prob = float(self.model.predict_proba(X)[0, 1])
            prob = float(np.clip(prob, 0.0, 1.0))

            if prob >= 0.80:
                status = "CRITICAL"
            elif prob >= 0.50:
                status = "WARNING"
            elif prob >= 0.25:
                status = "WATCH"
            else:
                status = "NORMAL"

            importances = self.get_feature_importances()

            return MLPredictionResult(
                timestamp=eval_time,
                prediction_horizon_minutes=self.horizon_minutes,
                degradation_probability=round(prob, 4),
                warning_status=status,
                feature_importances=importances,
                model_version=self.model_version,
            )
        except Exception as err:
            logger.error("ML Prediction failed: %s. Returning fallback result.", str(err))
            return MLPredictionResult(
                timestamp=eval_time,
                prediction_horizon_minutes=self.horizon_minutes,
                degradation_probability=0.0,
                warning_status="NORMAL",
                feature_importances={},
                model_version=self.model_version,
            )

    def get_feature_importances(self) -> Dict[str, float]:
        """Returns dict of feature importances."""
        if not self.is_trained:
            return {}

        importances = getattr(self.model, "feature_importances_", np.zeros(len(ML_FEATURE_NAMES)))
        imp_dict = {
            name: round(float(imp), 4) for name, imp in zip(ML_FEATURE_NAMES, importances)
        }
        # Sort descending
        sorted_items = sorted(imp_dict.items(), key=lambda pair: pair[1], reverse=True)
        return dict(sorted_items)
