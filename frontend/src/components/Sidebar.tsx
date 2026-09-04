import React from 'react';
import { Layers, Sliders, Activity, Brain, GitCommit, ShieldCheck, Zap } from 'lucide-react';

interface SidebarProps {
  activePillarTab: string;
  setActivePillarTab: (tab: string) => void;
  isSimulating: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ activePillarTab, setActivePillarTab, isSimulating }) => {
  const navItems = [
    { id: 'all', name: 'Overview & 4 Pillars', icon: Layers, description: 'Unified multi-pillar dashboard' },
    { id: 'p1', name: 'Pillar 1: Simulation', icon: Sliders, description: 'Micro-platform scenario engine' },
    { id: 'p2', name: 'Pillar 2: CAGED Detection', icon: Activity, description: 'Z-score & statistical alerts' },
    { id: 'p3', name: 'Pillar 3: ML Prediction', icon: Brain, description: 'XGBoost counterfactual forecast' },
    { id: 'p4', name: 'Pillar 4: DiD Analysis', icon: GitCommit, description: 'Difference-in-Differences effect' },
  ];

  return (
    <aside className="w-72 flex-shrink-0 bg-[#090d16] border-r border-slate-800/80 flex flex-col justify-between p-5 select-none shadow-2xl z-20">
      <div>
        {/* Brand Header */}
        <div className="flex items-center gap-3.5 mb-8 px-1">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 via-indigo-600 to-violet-700 flex items-center justify-center text-white shadow-lg shadow-blue-500/25 ring-1 ring-white/20">
            <Zap size={22} className="fill-current text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black text-white tracking-wider font-mono">CAGED</h1>
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">v2.0</span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium tracking-tight">Causal Analysis & Detection</p>
          </div>
        </div>

        {/* 4 Pillars Navigation Items */}
        <div className="space-y-2">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-3 mb-2">
            Analytical Pillars
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activePillarTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActivePillarTab(item.id)}
                className={`w-full flex items-start gap-3 p-3 rounded-xl transition-all duration-200 text-left border ${
                  isActive
                    ? 'bg-gradient-to-r from-blue-600/20 to-indigo-600/10 border-blue-500/50 text-white shadow-lg shadow-blue-500/10'
                    : 'bg-slate-900/30 border-transparent text-slate-400 hover:bg-slate-800/40 hover:text-slate-200 hover:border-slate-800'
                }`}
              >
                <div className={`p-2 rounded-lg mt-0.5 ${isActive ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30' : 'bg-slate-800/60 text-slate-400'}`}>
                  <Icon size={16} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className={`text-xs font-bold ${isActive ? 'text-white' : 'text-slate-300'}`}>{item.name}</div>
                  <div className="text-[10px] text-slate-500 truncate mt-0.5">{item.description}</div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Engine Security & Status Box */}
      <div className="mt-6 space-y-3">
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/90 space-y-2.5 backdrop-blur-md">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-bold text-slate-400 tracking-wider text-[10px] uppercase">Engine Status</span>
            <span className={`px-2 py-0.5 rounded-full font-bold text-[10px] flex items-center gap-1.5 border ${
              isSimulating 
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isSimulating ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
              {isSimulating ? 'ACTIVE' : 'STANDBY'}
            </span>
          </div>

          <div className="space-y-1.5 text-[11px] pt-1 border-t border-slate-800/60 font-mono">
            <div className="flex justify-between text-slate-400">
              <span>Telemetry Windows</span>
              <span className="text-slate-200 font-semibold">10 x 5-Min</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Detection Rule</span>
              <span className="text-emerald-400 font-semibold">$S_t \ge 4.0$</span>
            </div>
          </div>
        </div>

        {/* Ground Truth Firewall Shield */}
        <div className="px-3 py-2 rounded-lg bg-emerald-500/5 border border-emerald-500/20 flex items-center gap-2 text-[10px] text-emerald-400">
          <ShieldCheck size={14} className="flex-shrink-0 text-emerald-400" />
          <span className="font-medium">Ground-Truth Firewall Enabled</span>
        </div>
      </div>
    </aside>
  );
};

