"""
Unit Tests for Adaptive Baseline Engine (Exponential Smoothing & ARIMA).
"""

import math
import numpy as np
import pytest

from app.baselines.arima_baseline import ARIMABaseline
from app.baselines.exponential_smoothing import ExponentialSmoothingBaseline


def test_stationary_stream_exponential_smoothing():
    """Tests Exponential Smoothing baseline on a stationary stream (constant mean = 100.0 + Gaussian noise)."""
    np_rng = np.random.default_rng(42)
    clean_mean = 100.0
    noise = np_rng.normal(loc=0.0, scale=2.0, size=200)
    series = (clean_mean + noise).tolist()

    model = ExponentialSmoothingBaseline(alpha=0.2, beta=0.0)
    model.fit(series[:50])

    # Predict next
    pred = model.predict(confidence_level=0.95)
    
    # Expected forecast should be close to 100.0
    assert abs(pred.expected_value - clean_mean) <= 2.0
    assert pred.ci_lower <= pred.expected_value <= pred.ci_upper
    assert pred.std_dev > 0.0


def test_trend_stream_exponential_smoothing():
    """Tests double exponential smoothing on a linear trend stream (y_t = 10 + 0.5*t + noise)."""
    np_rng = np.random.default_rng(42)
    t_vals = np.arange(100)
    trend_series = (10.0 + 0.5 * t_vals + np_rng.normal(0, 0.5, size=100)).tolist()

    model = ExponentialSmoothingBaseline(alpha=0.3, beta=0.2)
    model.fit(trend_series[:50])

    for val in trend_series[50:90]:
        model.update(val)

    pred = model.predict(horizon=1)
    
    # Expected value at t=90 should be ~ (10 + 0.5*90) = 55.0
    expected_true = 10.0 + 0.5 * 90
    assert abs(pred.expected_value - expected_true) <= 2.0
    assert model.trend > 0.1  # Confirms positive trend captured


def test_seasonal_stream_exponential_smoothing():
    """Tests triple exponential smoothing on a seasonal stream (diurnal period = 24)."""
    np_rng = np.random.default_rng(42)
    period = 24
    t_vals = np.arange(144)  # 6 full cycles
    seasonal_pattern = 15.0 * np.sin(2.0 * np.pi * t_vals / float(period))
    seasonal_series = (100.0 + seasonal_pattern + np_rng.normal(0, 1.0, size=144)).tolist()

    model = ExponentialSmoothingBaseline(alpha=0.3, beta=0.0, gamma=0.2, seasonal_period=period)
    model.fit(seasonal_series[:96])  # Fit on first 4 cycles

    # Predict across cycle 5
    errors = []
    for val in seasonal_series[96:]:
        pred = model.predict()
        errors.append(abs(val - pred.expected_value))
        model.update(val)

    mae = np.mean(errors)
    assert mae <= 3.0  # Low prediction error on seasonal stream


test_cases_confidence_interval = [
    (ExponentialSmoothingBaseline(alpha=0.2), "ExponentialSmoothing"),
    (ARIMABaseline(p_order=2), "ARIMA"),
]

@pytest.mark.parametrize("model, model_name", test_cases_confidence_interval)
def test_confidence_interval_coverage(model, model_name):
    """Verifies that ~95% of normal stream observations fall within 95% confidence intervals."""
    np_rng = np.random.default_rng(42)
    clean_series = (50.0 + np_rng.normal(0.0, 1.5, size=200)).tolist()

    model.fit(clean_series[:50])

    coverage_count = 0
    test_eval_series = clean_series[50:]
    
    for val in test_eval_series:
        pred = model.predict(confidence_level=0.95)
        if pred.ci_lower <= val <= pred.ci_upper:
            coverage_count += 1
        model.update(val)

    coverage_pct = coverage_count / float(len(test_eval_series))
    assert coverage_pct >= 0.88, f"{model_name} CI coverage too low: {coverage_pct*100:.1f}%"


def test_arima_baseline_stationary_and_trend():
    """Tests ARIMABaseline on stationary and trend streams."""
    np_rng = np.random.default_rng(42)
    stationary = (200.0 + np_rng.normal(0, 3.0, size=100)).tolist()

    arima = ARIMABaseline(p_order=3)
    arima.fit(stationary[:50])

    pred = arima.predict()
    assert abs(pred.expected_value - 200.0) <= 4.0
    assert arima.get_residual_variance() > 0.0

    # Model reset
    arima.reset()
    assert arima.is_fitted is False
    assert len(arima.history) == 0
