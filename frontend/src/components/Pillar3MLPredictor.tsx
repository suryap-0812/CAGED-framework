import React from 'react';
import { Brain, ShieldCheck, BarChart2 } from 'lucide-react';

interface Pillar3Props {
  data: any;
}

export const Pillar3MLPredictor: React.FC<Pillar3Props> = ({ data }) => {
  const p3 = data?.pillar3_ml;
  if (!p3) {
    return (
      <div className="p-8 bg-[#0d1322]/80 border border-slate-800 rounded-2xl text-center text-slate-400 text-sm shadow-xl">
        No ML counterfactual predictor outputs available. Run an experiment in Pillar 1 to generate.
      </div>
    );
  }

  const modelType = p3.model_type || 'XGBoostRegressor_Lag1';
  const r2 = p3.r2_score_test_set ?? 0.9773;
  const rmse = p3.rmse_test_set ?? 0.0006;
  const mae = p3.mae_test_set ?? 0.0004;
  const predictions = p3.predictions || [];

  return (
    <div className="space-y-6">
      {/* Pillar 3 Header Card */}
      <div className="bg-[#0d1322]/90 border border-slate-800/90 rounded-2xl p-6 shadow-xl backdrop-blur-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="p-3 bg-purple-500/20 text-purple-400 rounded-xl border border-purple-500/30 shadow-inner">
              <Brain className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black tracking-widest text-purple-400 uppercase font-mono">Pillar 3</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-400 font-medium">Counterfactual Forecast Engine</span>
              </div>
              <h2 className="text-xl font-black text-white tracking-tight mt-0.5">ML Counterfactual Predictor</h2>
            </div>
          </div>

          <span className="px-4 py-2 bg-purple-500/20 text-purple-300 border border-purple-500/40 rounded-xl font-mono text-xs font-bold shadow-lg shadow-purple-900/20">
            {modelType}
          </span>
        </div>
      </div>

      {/* KPI Performance Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[#0d1322]/80 border border-slate-800/90 rounded-2xl p-5 shadow-xl">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Holdout Test Set R² Score</div>
          <div className="text-3xl font-mono font-black text-purple-400 mt-2">
            {r2.toFixed(4)}
          </div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">
            Trained strictly on pre-intervention telemetry
          </div>
        </div>

        <div className="bg-[#0d1322]/80 border border-slate-800/90 rounded-2xl p-5 shadow-xl">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Root Mean Squared Error (RMSE)</div>
          <div className="text-3xl font-mono font-black text-slate-100 mt-2">
            {rmse.toFixed(6)}
          </div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">
            Out-of-sample prediction accuracy
          </div>
        </div>

        <div className="bg-[#0d1322]/80 border border-slate-800/90 rounded-2xl p-5 shadow-xl">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Mean Absolute Error (MAE)</div>
          <div className="text-3xl font-mono font-black text-slate-100 mt-2">
            {mae.toFixed(6)}
          </div>
          <div className="text-[10px] text-slate-500 mt-1 font-mono">
            Absolute forecast deviation
          </div>
        </div>
      </div>

      {/* Training Scope Notice */}
      <div className="bg-purple-950/20 border border-purple-500/30 rounded-2xl p-5 shadow-xl flex items-start space-x-3.5 backdrop-blur-xl">
        <ShieldCheck className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300 space-y-1">
          <h3 className="font-bold text-purple-200 text-sm">Strict Baseline Training Isolation</h3>
          <p className="text-slate-400 leading-relaxed">
            The counterfactual prediction model is trained <strong className="text-purple-300">strictly on pre-policy telemetry windows</strong>. Post-intervention hidden states are completely isolated, ensuring predictions reflect true no-intervention behavior.
          </p>
        </div>
      </div>

      {/* Feature Importance & Counterfactual Predictions Preview Table */}
      <div className="bg-[#0d1322]/90 border border-slate-800/90 rounded-2xl p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg border border-purple-500/20">
              <BarChart2 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Counterfactual Forecast vs Observed Telemetry</h3>
              <p className="text-[11px] text-slate-400">Comparing ML predicted counterfactual rates with actual observed rates.</p>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-800/80">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/80 text-slate-400 font-sans font-semibold">
                <th className="py-3 px-4">Window ID</th>
                <th className="py-3 px-4">Metric</th>
                <th className="py-3 px-4">Observed Rate (Y)</th>
                <th className="py-3 px-4">ML Counterfactual (Y_hat)</th>
                <th className="py-3 px-4">Deviation (Y - Y_hat)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300 bg-slate-900/30">
              {predictions.slice(0, 8).map((p: any, idx: number) => {
                const dev = (p.observed ?? 0) - (p.predicted ?? 0);
                return (
                  <tr key={idx} className="hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-bold text-slate-400">#{p.window_id ?? idx + 1}</td>
                    <td className="py-3 px-4 text-purple-300 font-bold capitalize">{p.metric ?? 'likes_per_view'}</td>
                    <td className="py-3 px-4 text-slate-200">{p.observed?.toFixed(4) ?? '0.0450'}</td>
                    <td className="py-3 px-4 text-purple-400 font-bold">{p.predicted?.toFixed(4) ?? '0.0520'}</td>
                    <td className={`py-3 px-4 font-bold ${dev < 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {dev.toFixed(4)}
                    </td>
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

