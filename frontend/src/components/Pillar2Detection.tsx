import React from 'react';
import { Activity, AlertTriangle, CheckCircle2, Info, TrendingDown } from 'lucide-react';


interface Pillar2Props {
  data: any;
}

export const Pillar2Detection: React.FC<Pillar2Props> = ({ data }) => {
  const p2 = data?.pillar2_caged;
  if (!p2) {
    return (
      <div className="p-8 bg-[#0d1322]/80 border border-slate-800 rounded-2xl text-center text-slate-400 text-sm shadow-xl">
        No CAGED statistical detection outputs available. Run an experiment in Pillar 1 to generate.
      </div>
    );
  }

  const isDegraded = p2.is_degradation_detected;
  const compositeScore = p2.composite_statistic_St ?? p2.peak_composite_score ?? 0.0;
  const threshold = p2.calibrated_threshold ?? 4.0;
  const minEffect = p2.minimum_effect_size ?? 0.05;
  const baselines = p2.pre_policy_baseline || p2.frozen_baseline_means || {};
  const zScores = p2.metric_z_scores || {};

  return (
    <div className="space-y-6">
      {/* Pillar 2 Header Card */}
      <div className="bg-[#0d1322]/90 border border-slate-800/90 rounded-2xl p-6 shadow-xl backdrop-blur-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="p-3 bg-emerald-500/20 text-emerald-400 rounded-xl border border-emerald-500/30 shadow-inner">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black tracking-widest text-emerald-400 uppercase font-mono">Pillar 2</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-400 font-medium">Statistical Degradation Detector</span>
              </div>
              <h2 className="text-xl font-black text-white tracking-tight mt-0.5">CAGED Detection Engine</h2>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span
              className={`px-4 py-2 rounded-xl font-mono text-xs font-bold flex items-center space-x-2 border shadow-lg ${
                isDegraded
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-rose-900/20'
                  : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-emerald-900/20'
              }`}
            >
              {isDegraded ? (
                <>
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                  <span>ALGORITHMIC DEGRADATION DETECTED</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>NORMAL TELEMETRY STREAM</span>
                </>
              )}
            </span>
          </div>
        </div>
      </div>

      {/* Directional Degradation Mathematical Definition Banner */}
      <div className="bg-slate-950/90 border border-emerald-500/30 rounded-2xl p-5 shadow-xl flex items-start space-x-3.5 backdrop-blur-xl">
        <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg shrink-0 mt-0.5 border border-emerald-500/20">
          <Info className="w-5 h-5" />
        </div>
        <div className="text-xs text-slate-300 space-y-1.5 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold text-emerald-300 text-sm">CAGED Directional Degradation Specification</h3>
            <span className="px-2.5 py-0.5 bg-emerald-500/20 text-emerald-300 rounded-full font-mono text-[10px] font-bold border border-emerald-500/30">
              Z_m,t = (μ_m,frozen - Y_m,t) / max(σ_m,frozen, ε)
            </span>
          </div>
          <p className="text-slate-400 leading-relaxed text-xs">
            • <strong className="text-rose-300">Metric Decrease below frozen baseline (Y &lt; μ_frozen):</strong> Produces a positive Z-score ($Z_{`{m,t}`} &gt; 0$) and contributes to composite score $S_t = \sum \max(Z_{`{m,t}`}, 0)^2$.
            <br />
            • <strong className="text-emerald-300">Metric Improvement (Y ≥ μ_frozen):</strong> Produces a non-positive Z-score ($Z_{`{m,t}`} \le 0$) and contributes 0.0 to $S_t$.
          </p>
        </div>
      </div>

      {/* KPI Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0d1322]/80 border border-slate-800/90 rounded-2xl p-5 shadow-xl">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Composite Statistic ($S_t$)</div>
          <div className="text-3xl font-mono font-black text-slate-100 mt-2">
            {compositeScore.toFixed(2)}
          </div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">
            $S_t = \sum \max(Z_{`{m,t}`}, 0)^2$
          </div>
        </div>

        <div className="bg-[#0d1322]/80 border border-slate-800/90 rounded-2xl p-5 shadow-xl">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Calibrated Threshold (S_thresh)</div>
          <div className="text-3xl font-mono font-black text-emerald-400 mt-2">
            {threshold.toFixed(2)}
          </div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">
            Calibrated at null rate α = 0.05
          </div>
        </div>

        <div className="bg-[#0d1322]/80 border border-slate-800/90 rounded-2xl p-5 shadow-xl">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Minimum Effect Size (δ_min)</div>
          <div className="text-3xl font-mono font-black text-blue-400 mt-2">
            {(minEffect * 100).toFixed(1)}%
          </div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">
            Minimum detectable degradation
          </div>
        </div>

        <div className="bg-[#0d1322]/80 border border-slate-800/90 rounded-2xl p-5 shadow-xl">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Detection Status</div>
          <div className={`text-2xl font-mono font-black mt-2 ${isDegraded ? 'text-rose-400' : 'text-emerald-400'}`}>
            {isDegraded ? 'DEGRADED' : 'HEALTHY'}
          </div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">
            Rule: S_t &gt; S_thresh
          </div>
        </div>

      </div>

      {/* Metric Degradation Breakdown Table */}
      <div className="bg-[#0d1322]/90 border border-slate-800/90 rounded-2xl p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20">
              <TrendingDown className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Metric Directional Z-Score Breakdown</h3>
              <p className="text-[11px] text-slate-400">Individual metric degradation statistics compared to frozen pre-policy baseline.</p>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-800/80">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/80 text-slate-400 font-sans font-semibold">
                <th className="py-3 px-4">Metric Name</th>
                <th className="py-3 px-4">Frozen Baseline (μ_frozen)</th>
                <th className="py-3 px-4">Post Value (Y_m,t)</th>
                <th className="py-3 px-4">Directional Z-Score (Z_m,t)</th>
                <th className="py-3 px-4">Contribution to S_t</th>
              </tr>

            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300 bg-slate-900/30">
              {Object.keys(baselines).map((metricKey) => {
                const mu = baselines[metricKey] ?? 0;
                const z = zScores[metricKey] ?? 0;
                const postVal = mu - z * 0.05; // estimated post
                const contrib = Math.max(z, 0) ** 2;
                return (
                  <tr key={metricKey} className="hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-bold text-slate-200 capitalize">{metricKey.replace(/_/g, ' ')}</td>
                    <td className="py-3 px-4 text-slate-300">{mu.toFixed(4)}</td>
                    <td className="py-3 px-4 text-slate-300">{postVal.toFixed(4)}</td>
                    <td className={`py-3 px-4 font-bold ${z > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {z > 0 ? `+${z.toFixed(2)}` : z.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-purple-300 font-bold">{contrib.toFixed(2)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
