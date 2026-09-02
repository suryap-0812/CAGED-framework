"""
False-Alarm Control, Pre-Policy Noise Calibration & Bootstrap Threshold Estimator for CAGED.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field
import scipy.stats as stats

from app.ingestion.models import MetricType


class CalibrationResult(BaseModel):
    """Container for pre-policy noise calibration and estimated thresholds."""

    target_false_alarm_rate: float = Field(..., description="Configured target false alarm rate alpha")
    single_metric_z_threshold: float = Field(..., description="Calibrated Z-score threshold")
    composite_s_threshold: float = Field(..., description="Calibrated multi-metric S score threshold")
    sample_count: int = Field(..., description="Pre-policy calibration samples used")
    estimated_fpr: float = Field(..., description="Empirical False Positive Rate under H0")
    bonferroni_z_threshold: float = Field(..., description="Bonferroni-adjusted Z threshold for multi-testing")


class FalseAlarmCalibrator:
    """
    Statistically calibrates detection thresholds based on pre-policy stream noise
    and target false-alarm rate alpha (e.g. alpha=0.05).
    """

    def __init__(
        self,
        target_false_alarm_rate: float = 0.05,
        num_bootstrap_samples: int = 1000,
        seed: int = 42,
    ):
        """
        Args:
            target_false_alarm_rate: Bounded false-positive rate alpha (default: 0.05).
            num_bootstrap_samples: Number of bootstrap iterations B.
            seed: Random seed for reproducibility.
        """
        if not (0.001 <= target_false_alarm_rate <= 0.50):
            raise ValueError("target_false_alarm_rate must be between 0.001 and 0.50.")

        self.target_alpha = target_false_alarm_rate
        self.num_bootstrap = num_bootstrap_samples
        self.seed = seed
        self.np_rng = np.random.default_rng(seed)

    def calibrate_single_metric_z_threshold(self, pre_policy_residuals: List[float]) -> float:
        """
        Calibrates Z-score threshold for a single metric using empirical residuals.
        """
        if len(pre_policy_residuals) < 10:
            return float(stats.norm.ppf(1.0 - self.target_alpha))

        res_arr = np.array(pre_policy_residuals, dtype=np.float64)
        mean_r = np.mean(res_arr)
        std_r = np.std(res_arr, ddof=1)
        if std_r < 1e-4:
            std_r = 1e-4

        z_scores = (mean_r - res_arr) / std_r
        z_pos = np.maximum(z_scores, 0.0)

        percentile_val = 100.0 * (1.0 - self.target_alpha)
        thresh = float(np.percentile(z_pos, percentile_val))
        
        theoretical_z = float(stats.norm.ppf(1.0 - self.target_alpha))
        return float(max(thresh, theoretical_z))

    def calibrate_composite_s_threshold(
        self, pre_policy_metric_residuals: Dict[MetricType, List[float]]
    ) -> Tuple[float, float]:
        """
        Calibrates multi-metric composite score threshold S_thresh = sum max(Z_k, 0)^2 via bootstrap resampling.
        
        Returns:
            Tuple of (calibrated_s_threshold, estimated_empirical_fpr).
        """
        metrics = list(pre_policy_metric_residuals.keys())
        if not metrics:
            return 4.0, self.target_alpha

        sample_lengths = [len(pre_policy_metric_residuals[m]) for m in metrics]
        min_samples = min(sample_lengths)

        if min_samples < 10:
            K = len(metrics)
            return float(K * 2.0), self.target_alpha

        # Build positive Z-score vectors per metric
        z_pos_vectors = []
        for m in metrics:
            r_arr = np.array(pre_policy_metric_residuals[m], dtype=np.float64)
            mu = np.mean(r_arr)
            sd = max(1e-4, float(np.std(r_arr, ddof=1)))
            z_k = (mu - r_arr) / sd
            z_pos_vectors.append(np.maximum(z_k, 0.0))

        # Matrix: K x N
        z_matrix = np.array(z_pos_vectors)  # (K, N)
        N = z_matrix.shape[1]

        # Compute point-wise composite scores S_i = sum_k (z_{k, i})^2
        point_s_scores = np.sum(z_matrix ** 2, axis=0)

        # Resample B bootstrap instances from point_s_scores
        bootstrap_indices = self.np_rng.choice(N, size=self.num_bootstrap, replace=True)
        resampled_s_scores = point_s_scores[bootstrap_indices]

        percentile_val = 100.0 * (1.0 - self.target_alpha)
        calibrated_s = float(np.percentile(resampled_s_scores, percentile_val))

        # Calculate empirical FPR
        false_positives = np.sum(resampled_s_scores >= calibrated_s)
        empirical_fpr = float(false_positives / len(resampled_s_scores))

        return max(1.0, calibrated_s), round(empirical_fpr, 4)

    def apply_bonferroni_correction(self, num_metrics: int) -> float:
        """
        Calculates Bonferroni-adjusted Z-threshold for simultaneous multi-metric testing.
        
        alpha_adj = alpha / K
        Z_bonferroni = Phi^(-1)(1 - alpha_adj)
        """
        if num_metrics <= 1:
            return float(stats.norm.ppf(1.0 - self.target_alpha))

        alpha_adj = self.target_alpha / float(num_metrics)
        z_bonf = float(stats.norm.ppf(1.0 - alpha_adj))
        return round(z_bonf, 4)

    def apply_benjamini_hochberg(
        self, p_values: Dict[MetricType, float]
    ) -> Dict[MetricType, bool]:
        """
        Applies Benjamini-Hochberg False Discovery Rate (FDR) procedure across metric p-values.
        """
        items = sorted(p_values.items(), key=lambda pair: pair[1])
        K = len(items)
        if K == 0:
            return {}

        rejected: Dict[MetricType, bool] = {m: False for m in p_values.keys()}
        max_k_index = -1

        for idx, (metric, p_val) in enumerate(items):
            rank = idx + 1
            threshold_k = (rank / float(K)) * self.target_alpha
            if p_val <= threshold_k:
                max_k_index = idx

        if max_k_index >= 0:
            for idx in range(max_k_index + 1):
                rejected[items[idx][0]] = True

        return rejected
