"""
Abstract Baseline Model Interface & Prediction Schema for CAGED.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class BaselinePrediction(BaseModel):
    """Container for baseline expected metric forecast and confidence intervals."""

    expected_value: float = Field(..., description="Forecasted expected metric value E_t")
    variance: float = Field(default=0.0, ge=0.0, description="Estimated residual noise variance sigma^2_eta")
    std_dev: float = Field(default=0.0, ge=0.0, description="Estimated standard deviation sigma_eta")
    ci_lower: float = Field(..., description="Lower bound of confidence interval")
    ci_upper: float = Field(..., description="Upper bound of confidence interval")
    confidence_level: float = Field(default=0.95, description="Confidence level (e.g. 0.95 for 95% CI)")


class BaselineModel(ABC):
    """Abstract base class for adaptive baseline models."""

    @abstractmethod
    def fit(self, series: List[float]) -> None:
        """Initializes/fits baseline model parameters on a historical time series."""
        pass

    @abstractmethod
    def update(self, observed_value: float) -> None:
        """Updates baseline model state with a new incoming observation."""
        pass

    @abstractmethod
    def predict(self, horizon: int = 1, confidence_level: float = 0.95) -> BaselinePrediction:
        """Computes expected forecast and confidence interval for future step."""
        pass

    @abstractmethod
    def get_residual_variance(self) -> float:
        """Returns current residual noise variance sigma^2_eta."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets baseline model parameters."""
        pass
