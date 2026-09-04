import React from 'react';
import { ShieldCheck, RefreshCw } from 'lucide-react';

interface HeaderProps {
  activePillarTab: string;
  isSimulating: boolean;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({ activePillarTab, onRefresh }) => {

  const getTitle = () => {
    switch (activePillarTab) {
      case 'p1':
        return 'Pillar 1: Micro-Platform Simulator & Scenario Setup';
      case 'p2':
        return 'Pillar 2: CAGED Statistical Degradation Detector';
      case 'p3':
        return 'Pillar 3: ML Counterfactual Predictor (XGBoost/Ridge)';
      case 'p4':
        return 'Pillar 4: Difference-in-Differences (DiD) Causal Analysis';
      default:
        return 'CAGED 4-Pillar Analytical Framework & Evaluation Panel';
    }
  };

  return (
    <header className="px-8 py-5 border-b border-slate-800/80 bg-[#090d16]/90 backdrop-blur-md flex flex-wrap items-center justify-between gap-4 sticky top-0 z-10">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-black text-white tracking-tight font-sans">{getTitle()}</h1>
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/20">
            Phase 5 + 6 Final Spec
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-1 flex items-center gap-2">
          <span>Observable Telemetry Aggregations (5-Minute Windows)</span>
          <span className="text-slate-600">•</span>
          <span className="text-emerald-400 flex items-center gap-1 font-medium">
            <ShieldCheck size={13} /> Ground-Truth Firewall Active
          </span>
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 px-3.5 py-2 rounded-xl text-xs text-slate-300 font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          <span className="text-slate-400">Backend Status:</span>
          <span className="text-emerald-400 font-bold">FastAPI Online</span>
        </div>

        <button
          onClick={onRefresh}
          className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs px-4 py-2 rounded-xl shadow-lg shadow-blue-600/20 transition-all border border-blue-400/30"
        >
          <RefreshCw size={14} className="animate-spin-slow" />
          <span>Re-Run Active Scenario</span>
        </button>
      </div>
    </header>
  );
};

