"""
Holt-Winters Adaptive Exponential Smoothing Baseline Engine for CAGED.
"""

from collections import deque
import math
from typing import Deque, List, Optional
import scipy.stats as stats

from app.baselines.base import BaselineModel, BaselinePrediction


class ExponentialSmoothingBaseline(BaselineModel):
    """
    Adaptive Exponential Smoothing Baseline supporting Level (mu_t), Trend (b_t),
    optional Seasonality (s_t), and rolling residual variance tracking.
    
    Model Equation:
        E_t = mu_t + b_t + s_t + eta_t
    """

    def __init__(
        self,
        alpha: float = 0.3,
        beta: float = 0.1,
        gamma: float = 0.1,
        seasonal_period: Optional[int] = None,
        residual_window: int = 100,
    ):
        """
        Args:
            alpha: Smoothing factor for level (0 < alpha < 1).
            beta: Smoothing factor for trend (0 <= beta < 1).
            gamma: Smoothing factor for seasonality (0 <= gamma < 1).
            seasonal_period: Optional seasonal cycle length L (e.g. 24 for hourly diurnal).
            residual_window: Max window size for tracking residual variance.
        """
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.seasonal_period = seasonal_period
        self.residual_window = residual_window

        self.level: float = 0.0
        self.trend: float = 0.0
        self.seasonals: List[float] = []
        self.residuals: Deque[float] = deque(maxlen=residual_window)
        self.is_fitted: bool = False
        self._step_counter: int = 0

    def fit(self, series: List[float]) -> None:
        """
        Initializes baseline parameters on historical series.
        """
        if not series:
            return

        n = len(series)
        self.level = float(series[0])
        
        # Initialize Trend only if beta > 0
        if self.beta > 0 and n >= 2:
            self.trend = float((series[-1] - series[0]) / max(1, n - 1))
        else:
            self.trend = 0.0

        # Initialize Seasonality if seasonal_period specified
        L = self.seasonal_period
        if L and L > 1 and n >= L:
            num_seasons = n // L
            season_averages = [sum(series[j * L : (j + 1) * L]) / float(L) for j in range(num_seasons)]
            
            raw_seasonals = [0.0] * L
            for i in range(L):
                val_sum = sum(series[j * L + i] - season_averages[j] for j in range(num_seasons))
                raw_seasonals[i] = val_sum / float(num_seasons)

            # Normalize seasonals so their sum is 0
            mean_s = sum(raw_seasonals) / float(L)
            self.seasonals = [s - mean_s for s in raw_seasonals]
        else:
            self.seasonals = [0.0] * (L or 1)

        self.residuals.clear()
        self.is_fitted = True
        self._step_counter = 0

        # Fit parameters iteratively over series
        for val in series:
            self.update(val)

    def update(self, observed_value: float) -> None:
        """
        Updates baseline level, trend, seasonality, and residual error with new observation.
        """
        y = float(observed_value)

        if not self.is_fitted:
            self.level = y
            self.trend = 0.0
            self.is_fitted = True
            return

        pred = self._predict_next(horizon=1)
        error = y - pred
        self.residuals.append(error)

        L = len(self.seasonals) if self.seasonals else 1
        season_idx = self._step_counter % L
        s_prev = self.seasonals[season_idx] if (self.seasonal_period and L > 1) else 0.0

        prev_level = self.level
        prev_trend = self.trend

        # Update Level: mu_t = alpha * (y - s_{t-L}) + (1 - alpha) * (mu_{t-1} + b_{t-1})
        self.level = self.alpha * (y - s_prev) + (1.0 - self.alpha) * (prev_level + (prev_trend if self.beta > 0 else 0.0))

        # Update Trend: b_t = beta * (mu_t - mu_{t-1}) + (1 - beta) * b_{t-1}
        if self.beta > 0:
            self.trend = self.beta * (self.level - prev_level) + (1.0 - self.beta) * prev_trend
        else:
            self.trend = 0.0

        # Update Seasonality: s_t = gamma * (y - mu_t) + (1 - gamma) * s_{t-L}
        if self.seasonal_period and L > 1 and self.gamma > 0:
            self.seasonals[season_idx] = self.gamma * (y - self.level) + (1.0 - self.gamma) * s_prev

        self._step_counter += 1

    def _predict_next(self, horizon: int = 1) -> float:
        """Calculates point forecast for h steps ahead."""
        L = len(self.seasonals) if self.seasonals else 1
        future_idx = (self._step_counter + horizon - 1) % L
        s_future = self.seasonals[future_idx] if (self.seasonal_period and L > 1) else 0.0
        
        forecast = self.level + (horizon * self.trend if self.beta > 0 else 0.0) + s_future
        return max(0.0, forecast)

    def get_residual_variance(self) -> float:
        """
        Calculates sample variance of recent forecast residuals.
        """
        if len(self.residuals) < 2:
            return 1e-4  # Non-zero minimum fallback safeguard
            
        mean_res = sum(self.residuals) / float(len(self.residuals))
        var = sum((r - mean_res) ** 2 for r in self.residuals) / float(len(self.residuals) - 1)
        return max(1e-4, float(var))

    def predict(self, horizon: int = 1, confidence_level: float = 0.95) -> BaselinePrediction:
        """
        Generates expected forecast E_t and Gaussian confidence intervals.
        """
        expected = self._predict_next(horizon=horizon)
        var = self.get_residual_variance()
        std_dev = math.sqrt(var)

        z_multiplier = float(stats.norm.ppf(1.0 - (1.0 - confidence_level) / 2.0))
        margin = z_multiplier * std_dev

        return BaselinePrediction(
            expected_value=round(expected, 4),
            variance=round(var, 6),
            std_dev=round(std_dev, 6),
            ci_lower=round(max(0.0, expected - margin), 4),
            ci_upper=round(expected + margin, 4),
            confidence_level=confidence_level,
        )

    def reset(self) -> None:
        """Resets model state."""
        self.level = 0.0
        self.trend = 0.0
        self.seasonals = [0.0] * (self.seasonal_period or 1)
        self.residuals.clear()
        self.is_fitted = False
        self._step_counter = 0
