import React, { useEffect, useState } from 'react';
import { Sidebar } from '../components/Sidebar';
import { Header } from '../components/Header';
import { Pillar1Simulator } from '../components/Pillar1Simulator';
import { Pillar2Detection } from '../components/Pillar2Detection';
import { Pillar3MLPredictor } from '../components/Pillar3MLPredictor';
import { Pillar4DiDCausal } from '../components/Pillar4DiDCausal';
import { apiService } from '../services/api';
import { Layers, Sliders, Activity, Brain, GitCommit } from 'lucide-react';

export const Phase5Dashboard: React.FC = () => {
  const [activePillarTab, setActivePillarTab] = useState<string>('all');
  const [isSimulating, setIsSimulating] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [experimentData, setExperimentData] = useState<any>(null);

  // Pillar 1 Control States
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [scenarioId, setScenarioId] = useState<string>('originality_downrank');
  const [seed, setSeed] = useState<number>(42);
  const [numUsers, setNumUsers] = useState<number>(600);
  const [prePeriods, setPrePeriods] = useState<number>(5);
  const [postPeriods, setPostPeriods] = useState<number>(5);

  useEffect(() => {
    fetchScenarios();
    runExperiment();
  }, []);

  const fetchScenarios = async () => {
    try {
      const res = await apiService.getPhase5Scenarios();
      if (res && res.scenarios) {
        setScenarios(res.scenarios);
      }
    } catch (err) {
      console.warn('Failed to load Phase 5 scenarios:', err);
    }
  };

  const runExperiment = async () => {
    setLoading(true);
    try {
      const res = await apiService.runPhase5Experiment({
        scenario_id: scenarioId,
        random_seed: seed,
        num_users: numUsers,
        pre_periods: prePeriods,
        post_periods: postPeriods,
        minimum_effect_size: 0.05,
        composite_threshold: 4.0,
      });
      setExperimentData(res);
      setIsSimulating(true);
    } catch (err) {
      console.error('Phase 5 experiment execution failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#060911] text-slate-100 font-sans">
      <Sidebar
        activePillarTab={activePillarTab}
        setActivePillarTab={setActivePillarTab}
        isSimulating={isSimulating}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <Header
          activePillarTab={activePillarTab}
          isSimulating={isSimulating}
          onRefresh={runExperiment}
        />

        <main className="p-8 space-y-8 max-w-[1700px] mx-auto w-full">
          {/* Executive Summary Toolbar & 4-Pillar Tabs */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5 bg-gradient-to-r from-slate-900/80 via-slate-900/40 to-slate-900/80 border border-slate-800/90 p-5 rounded-2xl shadow-xl backdrop-blur-xl">
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-black text-white tracking-tight">CAGED Analytical Pillars</h2>
                <span className="px-2.5 py-0.5 bg-gradient-to-r from-blue-500/20 to-indigo-500/20 text-blue-400 border border-blue-500/30 text-[10px] rounded-full font-mono font-bold tracking-wide">
                  Clean Architecture
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Strict analytical separation between Simulation Ground Truth, CAGED Statistical Detection, ML Counterfactual Prediction, and DiD Causal Inference.
              </p>
            </div>

            <div className="flex items-center space-x-1.5 bg-slate-950/90 p-1.5 rounded-xl border border-slate-800 text-xs font-semibold shadow-inner">
              <button
                onClick={() => setActivePillarTab('all')}
                className={`px-3.5 py-2 rounded-lg transition-all flex items-center space-x-2 ${
                  activePillarTab === 'all' 
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold shadow-md shadow-blue-500/25' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>All 4 Pillars</span>
              </button>
              <button
                onClick={() => setActivePillarTab('p1')}
                className={`px-3.5 py-2 rounded-lg transition-all flex items-center space-x-2 ${
                  activePillarTab === 'p1' 
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold shadow-md shadow-blue-500/25' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                }`}
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>Pillar 1</span>
              </button>
              <button
                onClick={() => setActivePillarTab('p2')}
                className={`px-3.5 py-2 rounded-lg transition-all flex items-center space-x-2 ${
                  activePillarTab === 'p2' 
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold shadow-md shadow-blue-500/25' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                }`}
              >
                <Activity className="w-3.5 h-3.5" />
                <span>Pillar 2</span>
              </button>
              <button
                onClick={() => setActivePillarTab('p3')}
                className={`px-3.5 py-2 rounded-lg transition-all flex items-center space-x-2 ${
                  activePillarTab === 'p3' 
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold shadow-md shadow-blue-500/25' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                }`}
              >
                <Brain className="w-3.5 h-3.5" />
                <span>Pillar 3</span>
              </button>
              <button
                onClick={() => setActivePillarTab('p4')}
                className={`px-3.5 py-2 rounded-lg transition-all flex items-center space-x-2 ${
                  activePillarTab === 'p4' 
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold shadow-md shadow-blue-500/25' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                }`}
              >
                <GitCommit className="w-3.5 h-3.5" />
                <span>Pillar 4</span>
              </button>
            </div>
          </div>

          {/* Pillars Render */}
          {(activePillarTab === 'all' || activePillarTab === 'p1') && (
            <Pillar1Simulator
              data={experimentData}
              loading={loading}
              scenarioId={scenarioId}
              setScenarioId={setScenarioId}
              seed={seed}
              setSeed={setSeed}
              numUsers={numUsers}
              setNumUsers={setNumUsers}
              prePeriods={prePeriods}
              setPrePeriods={setPrePeriods}
              postPeriods={postPeriods}
              setPostPeriods={setPostPeriods}
              scenarios={scenarios}
              onRunExperiment={runExperiment}
            />
          )}

          {(activePillarTab === 'all' || activePillarTab === 'p2') && (
            <Pillar2Detection data={experimentData} />
          )}

          {(activePillarTab === 'all' || activePillarTab === 'p3') && (
            <Pillar3MLPredictor data={experimentData} />
          )}

          {(activePillarTab === 'all' || activePillarTab === 'p4') && (
            <Pillar4DiDCausal data={experimentData} />
          )}
        </main>
      </div>
    </div>
  );
};

