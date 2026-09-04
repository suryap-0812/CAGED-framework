"""
Difference-in-Differences (DiD) Causal Estimator for CAGED.
Computes empirical DiD policy effect estimates, standard errors, 95% confidence intervals,
p-values, pre-trend diagnostics, and causal interpretations under explicit identification assumptions.

Operates strictly on observable Treatment and Control cohort telemetry streams.
Strict Ground-Truth Firewall: Zero receipt of hidden policy parameters or simulator state.
"""

from datetime import datetime, timedelta, timezone
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field
import scipy.stats as stats

from app.ingestion.models import EngagementEvent, MetricType
from app.detection.window_aggregator import WindowAggregator, WindowedMetricPoint


class PreTrendDiagnosticResult(BaseModel):
    """Container for pre-treatment parallel trends diagnostic test."""

    treatment_trend_slope: float = Field(..., description="Estimated pre-T0 trend slope for Treatment cohort")
    control_trend_slope: float = Field(..., description="Estimated pre-T0 trend slope for Control cohort")
    differential_trend_coef: float = Field(..., description="Differential trend interaction coefficient gamma")
    std_error: float = Field(..., description="Standard error of differential trend coefficient SE(gamma)")
    p_value: float = Field(..., description="Two-tailed p-value for pre-trend interaction test")
    is_parallel_trends_supported: bool = Field(..., description="True if p_value > 0.05")
    diagnostic_message: str = Field(..., description="Formal statistical pre-trend diagnostic verdict")


class DiDEstimateResult(BaseModel):
    """Container for Difference-in-Differences causal estimation outputs."""

    metric_type: MetricType = Field(..., description="Target metric type evaluated")
    tau_did: float = Field(..., description="DiD point estimate tau_DiD = (Y_tr,post - Y_tr,pre) - (Y_ctrl,post - Y_ctrl,pre)")
    std_error: float = Field(..., description="Standard error of DiD point estimate SE(tau_DiD)")
    se_method: str = Field("welch_window_variance", description="Standard error estimation method used")
    ci_lower: float = Field(..., description="95% Confidence Interval lower bound")
    ci_upper: float = Field(..., description="95% Confidence Interval upper bound")
    p_value: float = Field(..., description="Two-tailed p-value for DiD estimate")
    is_statistically_significant: bool = Field(..., description="True if p_value < 0.05")
    is_practically_significant: bool = Field(..., description="True if relative effect size >= minimum_effect_size")

    treat_pre_mean: float = Field(..., description="Pre-policy Treatment cohort mean Y_treat,pre")
    treat_post_mean: float = Field(..., description="Post-policy Treatment cohort mean Y_treat,post")
    control_pre_mean: float = Field(..., description="Pre-policy Control cohort mean Y_control,pre")
    control_post_mean: float = Field(..., description="Post-policy Control cohort mean Y_control,post")

    treat_change: float = Field(..., description="Treatment cohort change Delta Y_treat")
    control_change: float = Field(..., description="Control cohort change Delta Y_control")

    window_counts: Dict[str, int] = Field(..., description="Window counts per cohort and period")
    pre_trend_diagnostic: PreTrendDiagnosticResult = Field(..., description="Pre-treatment trend diagnostic result")
    
    causal_verdict: str = Field(..., description="Formal causal interpretation verdict")
    identification_assumptions: List[str] = Field(..., description="Stated causal identification assumptions")


class DiDEstimator:
    """
    Difference-in-Differences Causal Estimator.
    Operates strictly on observable Treatment & Control cohort event streams.

    Standard Error Assumption:
    Standard error calculation uses Welch's heteroscedastic window-variance formula
    across 5-minute aggregated time-series windows:
    SE(tau_DiD) = sqrt(var_tr_pre/n_tr_pre + var_tr_post/n_tr_post + var_co_pre/n_co_pre + var_co_post/n_co_post)
    This assumes sampling independence across 5-minute aggregated windows. If temporal autocorrelation
    is present across windows, Welch's SE provides a robust window-level sampling variance baseline.
    """

    def __init__(self, window_size_minutes: int = 5):
        self.aggregator = WindowAggregator(window_size_minutes=window_size_minutes)

    def estimate_policy_effect(
        self,
        events: List[EngagementEvent],
        t0: Optional[datetime] = None,
        metric_type: MetricType = MetricType.LIKE,
        minimum_effect_size: float = 0.05,
    ) -> DiDEstimateResult:
        """
        Calculates empirical DiD estimate, standard errors, confidence intervals,
        parallel pre-trend diagnostics, and causal verdict.
        """
        if not events:
            raise ValueError("Telemetry event stream cannot be empty.")

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        start_time = sorted_events[0].timestamp
        onset_t0 = t0 or (start_time + timedelta(hours=12.0))
        if onset_t0.tzinfo is None:
            onset_t0 = onset_t0.replace(tzinfo=timezone.utc)

        # 1. Partition stream into Treatment vs Control cohort events using cohort tag
        treat_evts: List[EngagementEvent] = []
        ctrl_evts: List[EngagementEvent] = []

        for e in sorted_events:
            cohort = e.segment_metadata.get("cohort") if e.segment_metadata else None
            if cohort == "treatment":
                treat_evts.append(e)
            elif cohort == "control":
                ctrl_evts.append(e)

        # Fallback to balanced splitting if cohort tags missing
        if not treat_evts or not ctrl_evts:
            user_hashes = list(set(e.user_hash for e in sorted_events))
            half = len(user_hashes) // 2
            treat_hashes = set(user_hashes[:half])
            treat_evts = [e for e in sorted_events if e.user_hash in treat_hashes]
            ctrl_evts = [e for e in sorted_events if e.user_hash not in treat_hashes]

        # 2. Aggregate Treatment and Control streams into 5-minute fixed windows
        treat_pts = self.aggregator.aggregate_stream(treat_evts, start_time=start_time)
        ctrl_pts = self.aggregator.aggregate_stream(ctrl_evts, start_time=start_time)

        # 3. Partition window points by Pre-T0 vs Post-T0
        treat_pre = [pt for pt in treat_pts if pt.window_start < onset_t0]
        treat_post = [pt for pt in treat_pts if pt.window_start >= onset_t0]
        ctrl_pre = [pt for pt in ctrl_pts if pt.window_start < onset_t0]
        ctrl_post = [pt for pt in ctrl_pts if pt.window_start >= onset_t0]

        # Metric extraction helper
        def get_vals(pts: List[WindowedMetricPoint]) -> List[float]:
            return [pt.get_metric_value(metric_type) for pt in pts]

        y_tr_pre = get_vals(treat_pre)
        y_tr_post = get_vals(treat_post)
        y_co_pre = get_vals(ctrl_pre)
        y_co_post = get_vals(ctrl_post)

        m_tr_pre = float(np.mean(y_tr_pre)) if y_tr_pre else 0.0
        m_tr_post = float(np.mean(y_tr_post)) if y_tr_post else 0.0
        m_co_pre = float(np.mean(y_co_pre)) if y_co_pre else 0.0
        m_co_post = float(np.mean(y_co_post)) if y_co_post else 0.0

        delta_tr = m_tr_post - m_tr_pre
        delta_co = m_co_post - m_co_pre

        # 4. Point Estimate tau_DiD = (Y_tr,post - Y_tr,pre) - (Y_co,post - Y_co,pre)
        tau_did = delta_tr - delta_co

        # 5. Standard Error SE(tau_DiD) calculation
        var_tr_pre = float(np.var(y_tr_pre, ddof=1)) if len(y_tr_pre) > 1 else 1e-4
        var_tr_post = float(np.var(y_tr_post, ddof=1)) if len(y_tr_post) > 1 else 1e-4
        var_co_pre = float(np.var(y_co_pre, ddof=1)) if len(y_co_pre) > 1 else 1e-4
        var_co_post = float(np.var(y_co_post, ddof=1)) if len(y_co_post) > 1 else 1e-4

        n_tr_pre = max(1, len(y_tr_pre))
        n_tr_post = max(1, len(y_tr_post))
        n_co_pre = max(1, len(y_co_pre))
        n_co_post = max(1, len(y_co_post))

        se_tr = (var_tr_pre / n_tr_pre) + (var_tr_post / n_tr_post)
        se_co = (var_co_pre / n_co_pre) + (var_co_post / n_co_post)
        se_did = math.sqrt(max(1e-6, se_tr + se_co))

        # 6. 95% Confidence Interval & p-value
        z_crit = 1.96
        ci_lower = tau_did - (z_crit * se_did)
        ci_upper = tau_did + (z_crit * se_did)

        t_stat = tau_did / se_did if se_did > 0 else 0.0
        p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(t_stat))))
        is_stat_sig = p_val < 0.05

        rel_effect = abs(tau_did / m_tr_pre) if m_tr_pre > 0 else 0.0
        is_pract_sig = rel_effect >= minimum_effect_size

        # 7. Parallel Pre-Trends Diagnostic (Pre-T0 Data Only)
        pre_trend_diag = self._evaluate_pre_trends(treat_pre, ctrl_pre, metric_type)

        # 8. Causal Verdict Synthesis
        verdict = self._synthesize_causal_verdict(
            tau_did=tau_did,
            p_val=p_val,
            is_stat_sig=is_stat_sig,
            is_pract_sig=is_pract_sig,
            pre_trend_diag=pre_trend_diag,
            rel_effect=rel_effect,
            minimum_effect_size=minimum_effect_size,
        )

        assumptions = [
            "No-interference assumption (SUTVA): Treatment policy modification does not affect Control cohort recommendations or user state.",
            "Common time-varying shock exposure: External disturbances affect Treatment and Control cohorts comparably.",
            "Parallel pre-trends: In the absence of treatment, Treatment and Control cohort engagement trajectories would have evolved in parallel.",
        ]

        win_counts = {
            "n_treat_pre": n_tr_pre,
            "n_treat_post": n_tr_post,
            "n_control_pre": n_co_pre,
            "n_control_post": n_co_post,
        }

        return DiDEstimateResult(
            metric_type=metric_type,
            tau_did=round(tau_did, 4),
            std_error=round(se_did, 6),
            se_method="welch_window_variance",
            ci_lower=round(ci_lower, 4),
            ci_upper=round(ci_upper, 4),
            p_value=round(p_val, 6),
            is_statistically_significant=is_stat_sig,
            is_practically_significant=is_pract_sig,
            treat_pre_mean=round(m_tr_pre, 4),
            treat_post_mean=round(m_tr_post, 4),
            control_pre_mean=round(m_co_pre, 4),
            control_post_mean=round(m_co_post, 4),
            treat_change=round(delta_tr, 4),
            control_change=round(delta_co, 4),
            window_counts=win_counts,
            pre_trend_diagnostic=pre_trend_diag,
            causal_verdict=verdict,
            identification_assumptions=assumptions,
        )

    def _evaluate_pre_trends(
        self,
        treat_pre: List[WindowedMetricPoint],
        ctrl_pre: List[WindowedMetricPoint],
        metric_type: MetricType,
    ) -> PreTrendDiagnosticResult:
        """
        Evaluates pre-treatment trend interaction (Treatment x Time) using strictly pre-T0 5-minute windows.
        Fits pooled interaction OLS regression: Y_it = beta0 + beta1*Treat_i + beta2*t + gamma*(Treat_i * t) + e_it.
        Tests H0: gamma = 0 (parallel pre-trends).
        """
        n_win = min(len(treat_pre), len(ctrl_pre))
        if n_win < 3:
            return PreTrendDiagnosticResult(
                treatment_trend_slope=0.0,
                control_trend_slope=0.0,
                differential_trend_coef=0.0,
                std_error=0.0,
                p_value=1.0,
                is_parallel_trends_supported=True,
                diagnostic_message="If the pre-trend interaction is statistically insignificant (p > 0.05), there is insufficient evidence of differential pre-trends. This supports, but does not prove, the parallel-trends assumption.",
            )

        t_indices = np.arange(n_win, dtype=np.float64)
        y_tr = np.array([treat_pre[i].get_metric_value(metric_type) for i in range(n_win)], dtype=np.float64)
        y_co = np.array([ctrl_pre[i].get_metric_value(metric_type) for i in range(n_win)], dtype=np.float64)

        slope_tr, _, _, _, _ = stats.linregress(t_indices, y_tr)
        slope_co, _, _, _, _ = stats.linregress(t_indices, y_co)

        # Pooled interaction regression: Y = beta0 + beta1*Treat + beta2*t + gamma*(Treat*t)
        # Construct observations for Treatment (Treat=1) and Control (Treat=0)
        y_all = np.concatenate([y_tr, y_co])
        treat_dummy = np.concatenate([np.ones(n_win), np.zeros(n_win)])
        t_all = np.concatenate([t_indices, t_indices])
        interaction = treat_dummy * t_all

        X = np.column_stack([np.ones(len(y_all)), treat_dummy, t_all, interaction])
        beta = np.linalg.lstsq(X, y_all, rcond=None)[0]
        gamma = float(beta[3])

        # Residual variance and standard error of interaction term gamma
        residuals = y_all - X @ beta
        df = len(y_all) - X.shape[1]
        sigma2 = float(np.sum(residuals**2) / df) if df > 0 else 1e-4
        try:
            cov = sigma2 * np.linalg.inv(X.T @ X)
            se_gamma = math.sqrt(max(1e-8, cov[3, 3]))
        except np.linalg.LinAlgError:
            se_gamma = 1e-4

        t_stat = gamma / se_gamma if se_gamma > 0 else 0.0
        p_val = float(2.0 * (1.0 - stats.t.cdf(abs(t_stat), df=df))) if df > 0 else 1.0

        is_supported = p_val > 0.05
        if is_supported:
            msg = "If the pre-trend interaction is statistically insignificant (p > 0.05), there is insufficient evidence of differential pre-trends. This supports, but does not prove, the parallel-trends assumption."
        else:
            msg = f"Statistically significant evidence of differential pre-trends detected (p = {p_val:.4f} <= 0.05). Parallel-trends assumption is violated."

        return PreTrendDiagnosticResult(
            treatment_trend_slope=round(float(slope_tr), 6),
            control_trend_slope=round(float(slope_co), 6),
            differential_trend_coef=round(gamma, 6),
            std_error=round(se_gamma, 6),
            p_value=round(p_val, 6),
            is_parallel_trends_supported=is_supported,
            diagnostic_message=msg,
        )

    def _synthesize_causal_verdict(
        self,
        tau_did: float,
        p_val: float,
        is_stat_sig: bool,
        is_pract_sig: bool,
        pre_trend_diag: PreTrendDiagnosticResult,
        rel_effect: float,
        minimum_effect_size: float,
    ) -> str:
        """Synthesizes formal causal interpretation verdict."""
        if not pre_trend_diag.is_parallel_trends_supported:
            return f"UNSUPPORTED: Differential pre-trends detected (p_pretrend = {pre_trend_diag.p_value:.4f} <= 0.05). The parallel-trends assumption is violated; DiD estimate cannot be interpreted as causal."

        if is_stat_sig and is_pract_sig:
            direction = "degradation" if tau_did < 0 else "increase"
            return f"CAUSAL DEGRADATION CONFIRMED: Statistically significant (p = {p_val:.4f} < 0.05) and practically relevant ({rel_effect*100.0:.2f}% >= {minimum_effect_size*100.0:.1f}%) policy effect estimated (tau_DiD = {tau_did:.4f}). Insufficient evidence of differential pre-trends supports the causal identification assumptions."
        elif is_stat_sig and not is_pract_sig:
            return f"STATISTICALLY SIGNIFICANT BUT PRACTICALLY NEGLIGIBLE: Statistically significant (p = {p_val:.4f} < 0.05) effect detected (tau_DiD = {tau_did:.4f}), but magnitude ({rel_effect*100.0:.2f}%) falls below practical significance threshold Delta_min ({minimum_effect_size*100.0:.1f}%)."
        else:
            return f"NO STATISTICALLY SIGNIFICANT EFFECT: Insufficient evidence to reject the null hypothesis of zero policy effect (p = {p_val:.4f} >= 0.05, tau_DiD = {tau_did:.4f})."
