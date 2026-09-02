"""
Lightweight AutoRegressive (AR) Baseline Engine for CAGED.
"""

from collections import deque
import math
from typing import Deque, List, Optional
import numpy as np
import scipy.stats as stats

from app.baselines.base import BaselineModel, BaselinePrediction


class ARIMABaseline(BaselineModel):
    """
    Lightweight AutoRegressive AR(p) Baseline Model.
    
    Fits linear autoregressive coefficients on lag terms:
        Y_t = c + phi_1 * Y_{t-1} + ... + phi_p * Y_{t-p} + eta_t
    """

    def __init__(self, p_order: int = 3, residual_window: int = 100):
        self.p_order = p_order
        self.residual_window = residual_window
        self.history: Deque[float] = deque(maxlen=max(500, p_order * 10))
        self.residuals: Deque[float] = deque(maxlen=residual_window)
        
        self.intercept: float = 0.0
        self.phi: np.ndarray = np.zeros(p_order, dtype=np.float64)
        self.is_fitted: bool = False

    def fit(self, series: List[float]) -> None:
        """Fits AR(p) coefficients using Ordinary Least Squares (OLS)."""
        if len(series) <= self.p_order + 2:
            return

        self.history.clear()
        self.history.extend(series)

        # Construct Design Matrix X and Target Vector Y
        n = len(series)
        X_list = []
        Y_list = []

        for t in range(self.p_order, n):
            lags = series[t - self.p_order : t][::-1]  # Y_{t-1}, ..., Y_{t-p}
            X_list.append([1.0] + list(lags))
            Y_list.append(series[t])

        X = np.array(X_list, dtype=np.float64)
        Y = np.array(Y_list, dtype=np.float64)

        # Solve OLS: beta = (X^T X)^(-1) X^T Y
        try:
            beta, _, _, _ = np.linalg.lstsq(X, Y, rcond=None)
            self.intercept = float(beta[0])
            self.phi = beta[1:]
            self.is_fitted = True
        except np.linalg.LinAlgError:
            self.intercept = float(np.mean(series))
            self.phi = np.zeros(self.p_order, dtype=np.float64)
            self.is_fitted = True

        # Calculate residual errors
        self.residuals.clear()
        for t in range(self.p_order, n):
            lags = np.array(series[t - self.p_order : t][::-1], dtype=np.float64)
            pred = self.intercept + np.dot(self.phi, lags)
            self.residuals.append(series[t] - pred)

    def update(self, observed_value: float) -> None:
        """Updates history with new observation and records residual error."""
        y = float(observed_value)
        if self.is_fitted and len(self.history) >= self.p_order:
            pred = self._predict_next()
            self.residuals.append(y - pred)

        self.history.append(y)

    def _predict_next(self) -> float:
        """Predicts next step using AR coefficients."""
        if not self.is_fitted or len(self.history) < self.p_order:
            return float(self.history[-1]) if self.history else 0.0

        recent_lags = np.array(list(self.history)[-self.p_order :][::-1], dtype=np.float64)
        pred = self.intercept + np.dot(self.phi, recent_lags)
        return max(0.0, float(pred))

    def get_residual_variance(self) -> float:
        """Returns sample variance of forecast residuals."""
        if len(self.residuals) < 2:
            return 1e-4

        mean_res = sum(self.residuals) / float(len(self.residuals))
        var = sum((r - mean_res) ** 2 for r in self.residuals) / float(len(self.residuals) - 1)
        return max(1e-4, float(var))

    def predict(self, horizon: int = 1, confidence_level: float = 0.95) -> BaselinePrediction:
        """Computes forecast and confidence bounds."""
        expected = self._predict_next()
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
        """Resets AR model state."""
        self.history.clear()
        self.residuals.clear()
        self.intercept = 0.0
        self.phi.fill(0.0)
        self.is_fitted = False
