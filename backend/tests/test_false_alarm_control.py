"""
Unit Tests for False-Alarm Control & Statistical Calibration.
"""

import numpy as np
import pytest

from app.detection.false_alarm import FalseAlarmCalibrator
from app.ingestion.models import MetricType


def test_false_alarm_calibrator_invalid_target_alpha():
    """Verifies ValueError raised for invalid target false alarm rates."""
    with pytest.raises(ValueError):
        FalseAlarmCalibrator(target_false_alarm_rate=0.0)

    with pytest.raises(ValueError):
        FalseAlarmCalibrator(target_false_alarm_rate=0.80)


def test_single_metric_z_threshold_calibration():
    """Tests bootstrap noise calibration for single metric Z-score threshold."""
    calibrator = FalseAlarmCalibrator(target_false_alarm_rate=0.05, seed=42)

    # Generate synthetic pre-policy residuals (mean=0, std=1)
    np_rng = np.random.default_rng(42)
    residuals = np_rng.normal(loc=0.0, scale=1.0, size=500).tolist()

    z_thresh = calibrator.calibrate_single_metric_z_threshold(residuals)

    # Standard Gaussian Z_0.05 = 1.6449
    assert z_thresh >= 1.64


def test_bonferroni_correction():
    """Tests Bonferroni correction across simultaneous metric tests."""
    calibrator = FalseAlarmCalibrator(target_false_alarm_rate=0.05)

    # K = 1 metric -> standard Z = 1.6449
    z_k1 = calibrator.apply_bonferroni_correction(num_metrics=1)
    assert abs(z_k1 - 1.6449) <= 0.05

    # K = 5 metrics -> alpha_adj = 0.05 / 5 = 0.01 -> Z_0.01 = 2.3263
    z_k5 = calibrator.apply_bonferroni_correction(num_metrics=5)
    assert z_k5 > z_k1
    assert abs(z_k5 - 2.3263) <= 0.05


def test_benjamini_hochberg_fdr():
    """Tests Benjamini-Hochberg False Discovery Rate (FDR) procedure."""
    calibrator = FalseAlarmCalibrator(target_false_alarm_rate=0.05)

    p_values = {
        MetricType.LIKE: 0.001,      # Highly significant
        MetricType.COMMENT: 0.008,   # Significant
        MetricType.SHARE: 0.040,     # Borderline
        MetricType.VIEW: 0.450,      # Non-significant
    }

    fdr_results = calibrator.apply_benjamini_hochberg(p_values)

    assert fdr_results[MetricType.LIKE] is True
    assert fdr_results[MetricType.COMMENT] is True
    assert fdr_results[MetricType.VIEW] is False


def test_composite_s_threshold_calibration():
    """Tests bootstrap multi-metric composite S threshold calibration."""
    calibrator = FalseAlarmCalibrator(target_false_alarm_rate=0.05, num_bootstrap_samples=200, seed=42)

    np_rng = np.random.default_rng(42)
    pre_residuals = {
        MetricType.LIKE: np_rng.normal(0, 1.0, size=200).tolist(),
        MetricType.COMMENT: np_rng.normal(0, 1.0, size=200).tolist(),
        MetricType.SHARE: np_rng.normal(0, 1.0, size=200).tolist(),
    }

    s_thresh, empirical_fpr = calibrator.calibrate_composite_s_threshold(pre_residuals)

    assert s_thresh > 1.0
    assert empirical_fpr <= 0.10  # Confirms empirical FPR is bounded
