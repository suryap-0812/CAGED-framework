import React from 'react';
import { Sliders, ShieldAlert, Cpu, Database } from 'lucide-react';


interface Pillar1Props {
  data: any;
  loading: boolean;
  scenarioId: string;
  setScenarioId: (id: string) => void;
  seed: number;
  setSeed: (seed: number) => void;
  numUsers: number;
  setNumUsers: (n: number) => void;
  prePeriods: number;
  setPrePeriods: (n: number) => void;
  postPeriods: number;
  setPostPeriods: (n: number) => void;
  scenarios: any[];
  onRunExperiment: () => void;
}

export const Pillar1Simulator: React.FC<Pillar1Props> = ({
  data,
  loading,
  scenarioId,
  setScenarioId,
  seed,
  setSeed,
  numUsers,
  setNumUsers,
  prePeriods,
  setPrePeriods,
  postPeriods,
  setPostPeriods,
  scenarios,
  onRunExperiment,
}) => {
  const p1 = data?.pillar1_simulator;
  const groundTruth = p1?.ground_truth_config;
  const telemetry = p1?.telemetry_records || [];

  return (
    <div className="space-y-6">
      {/* Pillar 1 Main Control Header Card */}
      <div className="bg-[#0d1322]/90 border border-slate-800/90 rounded-2xl p-6 shadow-xl backdrop-blur-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
          <div className="flex items-center space-x-3.5">
            <div className="p-3 bg-gradient-to-br from-blue-500/20 to-indigo-500/20 text-blue-400 rounded-xl border border-blue-500/30 shadow-inner">
              <Sliders className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black tracking-widest text-blue-400 uppercase font-mono">Pillar 1</span>
                <span className="text-slate-600">•</span>
                <span className="text-xs text-slate-400 font-medium">Synthetic Micro-Platform Environment</span>
              </div>
              <h2 className="text-xl font-black text-white tracking-tight mt-0.5">Experiment Simulator & Ground-Truth Setup</h2>
            </div>
          </div>

          <button
            onClick={onRunExperiment}
            disabled={loading}
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs rounded-xl transition-all shadow-lg shadow-blue-600/25 flex items-center justify-center space-x-2 disabled:opacity-50 border border-blue-400/30"
          >
            <Cpu className="w-4 h-4" />
            <span>{loading ? 'Executing Pipeline...' : 'Run 4-Pillar Pipeline'}</span>
          </button>
        </div>

        {/* Standard Aligned Control Inputs Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mt-6">
          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-300 tracking-wide uppercase text-[10px]">Policy Scenario</label>
            <select
              value={scenarioId}
              onChange={(e) => setScenarioId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 font-medium focus:outline-none focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/40 transition-all"
            >
              {scenarios.map((s) => (
                <option key={s.scenario_id} value={s.scenario_id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-300 tracking-wide uppercase text-[10px]">Random Seed</label>
            <input
              type="number"
              value={seed}
              onChange={(e) => setSeed(parseInt(e.target.value) || 42)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/40 transition-all"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-300 tracking-wide uppercase text-[10px]">User Population</label>
            <input
              type="number"
              value={numUsers}
              onChange={(e) => setNumUsers(parseInt(e.target.value) || 600)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/40 transition-all"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-300 tracking-wide uppercase text-[10px]">Pre-Periods (5-Min)</label>
            <input
              type="number"
              value={prePeriods}
              onChange={(e) => setPrePeriods(parseInt(e.target.value) || 5)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/40 transition-all"
            />
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-bold text-slate-300 tracking-wide uppercase text-[10px]">Post-Periods (5-Min)</label>
            <input
              type="number"
              value={postPeriods}
              onChange={(e) => setPostPeriods(parseInt(e.target.value) || 5)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/40 transition-all"
            />
          </div>
        </div>
      </div>

      {/* Ground Truth Firewall Notice & Parameters Card */}
      <div className="bg-amber-950/20 border border-amber-500/30 rounded-2xl p-6 shadow-xl relative overflow-hidden backdrop-blur-xl">
        <div className="flex items-start space-x-3.5 mb-4">
          <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 bg-amber-500/20 text-amber-300 font-mono text-[10px] font-extrabold rounded-full border border-amber-500/40 uppercase">
                Ground-Truth Firewall Enforced
              </span>
            </div>
            <h3 className="text-sm font-black text-amber-200 mt-1">
              Simulator Ground-Truth Parameters (Experimental Transparency Display Only)
            </h3>
            <p className="text-xs text-amber-300/70 mt-1 leading-relaxed">
              These internal parameters drive algorithmic policy dynamics inside the micro-platform simulator. To maintain strict causal isolation, these parameters are displayed purely for transparency and are <strong className="text-amber-200">never passed to CAGED, ML, or DiD as analytical inputs</strong>.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/90 rounded-xl p-4 border border-amber-500/20 font-mono text-xs shadow-inner">
          <div>
            <div className="text-[10px] text-slate-400 uppercase font-sans font-bold">Scenario Key</div>
            <div className="text-amber-300 font-bold mt-0.5">{p1?.scenario_id || scenarioId}</div>
          </div>
          <div>
            <div className="text-[10px] text-slate-400 uppercase font-sans font-bold">Time Windows</div>
            <div className="text-slate-200 font-bold mt-0.5">{p1?.total_periods || prePeriods + postPeriods} x 5-Min</div>
          </div>
          <div>
            <div className="text-[10px] text-slate-400 uppercase font-sans font-bold">Policy Weight Shift</div>
            <div className="text-slate-200 font-bold mt-0.5">
              {groundTruth?.policy_weight_shifts?.originality_weight_shift ?? '-2.5'}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-slate-400 uppercase font-sans font-bold">Detector Rule</div>
            <div className="text-emerald-400 font-bold mt-0.5">S_thresh = {groundTruth?.composite_threshold_s_thresh ?? 4.0}</div>
          </div>
        </div>
      </div>

      {/* Generated Telemetry Streams Preview Table */}
      <div className="bg-[#0d1322]/90 border border-slate-800/90 rounded-2xl p-6 shadow-xl backdrop-blur-xl">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg border border-blue-500/20">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100">Observable Telemetry Stream (5-Minute Windows)</h3>
              <p className="text-[11px] text-slate-400">Aggregated non-sensitive observable user metrics emitted by micro-platform.</p>
            </div>
          </div>
          <span className="text-xs text-slate-400 font-mono bg-slate-900 px-3 py-1 rounded-lg border border-slate-800">
            {telemetry.length} windows active
          </span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-800/80">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/80 text-slate-400 font-sans font-semibold">
                <th className="py-3 px-4">Window ID</th>
                <th className="py-3 px-4">Start Time (UTC)</th>
                <th className="py-3 px-4">Views / Min</th>
                <th className="py-3 px-4">Likes / View</th>
                <th className="py-3 px-4">Comments / View</th>
                <th className="py-3 px-4">Shares / View</th>
                <th className="py-3 px-4">Clicks / View</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300 bg-slate-900/30">
              {telemetry.slice(0, 10).map((t: any, idx: number) => {
                const isPost = idx >= prePeriods;
                return (
                  <tr key={idx} className={isPost ? 'bg-amber-950/15 hover:bg-amber-900/20' : 'hover:bg-slate-800/40'}>
                    <td className="py-2.5 px-4 font-bold text-slate-400">#{t.window_id}</td>
                    <td className="py-2.5 px-4 text-slate-300">
                      {new Date(t.window_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-2.5 px-4 text-blue-300 font-bold">{t.views_per_min?.toFixed(1)}</td>
                    <td className="py-2.5 px-4 text-emerald-300">{t.likes_per_view?.toFixed(4)}</td>
                    <td className="py-2.5 px-4 text-purple-300">{t.comments_per_view?.toFixed(4)}</td>
                    <td className="py-2.5 px-4 text-amber-300">{t.shares_per_view?.toFixed(4)}</td>
                    <td className="py-2.5 px-4 text-sky-300">{t.clicks_per_view?.toFixed(4)}</td>
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
