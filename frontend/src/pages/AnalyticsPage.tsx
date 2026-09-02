import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Activity,
  Calendar,
  FileText,
  Radio,
  RefreshCw,
  ShieldAlert,
  TrendingDown,
  Users,
  Zap,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface MetricItem {
  timestamp: string;
  is_post_policy: boolean;
  like_expected: number;
  like_observed: number;
  comment_expected: number;
  comment_observed: number;
  share_expected: number;
  share_observed: number;
}

interface DashboardMetrics {
  timestamp: string;
  policy_t0: string;
  active_policy_id: string;
  composite_score: number;
  composite_threshold: number;
  is_degraded: boolean;
  top_contributor: string | null;
  metric_results: Record<string, any>;
  time_series: MetricItem[];
}

interface AlertItem {
  alert_id: string;
  policy_id: string;
  timestamp: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  composite_score: number;
  max_z_score: number;
  message: string;
}

export const AnalyticsPage: React.FC = () => {
  const [data, setData] = useState<DashboardMetrics | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [segmentData, setSegmentData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [sseConnected, setSseConnected] = useState<boolean>(false);
  const [activeMetric, setActiveMetric] = useState<'like' | 'comment' | 'share'>('like');
  const [reportMarkdown, setReportMarkdown] = useState<string | null>(null);
  const [showReportModal, setShowReportModal] = useState<boolean>(false);
  const [simulating, setSimulating] = useState<boolean>(false);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [mRes, aRes, sRes] = await Promise.all([
        fetch('http://localhost:8000/api/v1/dashboard/metrics'),
        fetch('http://localhost:8000/api/v1/dashboard/alerts'),
        fetch('http://localhost:8000/api/v1/dashboard/segments'),
      ]);

      if (mRes.ok) setData(await mRes.json());
      if (aRes.ok) {
        const aData = await aRes.json();
        setAlerts(aData.alerts || []);
      }
      if (sRes.ok) setSegmentData(await sRes.json());
    } catch (err) {
      console.error('Failed to fetch dashboard metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchReport = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/dashboard/report?format=markdown');
      if (res.ok) {
        const json = await res.json();
        setReportMarkdown(json.content);
        setShowReportModal(true);
      }
    } catch (err) {
      console.error('Failed to fetch report:', err);
    }
  };

  const handleSimulatePolicy = async () => {
    try {
      setSimulating(true);
      await fetch('http://localhost:8000/api/v1/dashboard/simulate_policy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          policy_id: `P00${Math.floor(Math.random() * 89 + 10)}`,
          policy_name: 'Strict Privacy Filter',
          impact_factor: 0.65,
          description: 'Simulated strict engagement filter change at T0',
        }),
      });
      await fetchDashboardData();
    } catch (err) {
      console.error('Failed to simulate policy:', err);
    } finally {
      setSimulating(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();

    // Server-Sent Events (SSE) Streaming Connection
    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource('http://localhost:8000/api/v1/dashboard/stream');

      eventSource.onopen = () => {
        setSseConnected(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const sseData = JSON.parse(event.data);
          if (sseData && sseData.composite_score !== undefined) {
            setData((prev) => {
              if (!prev) return prev;
              const newTs = [...prev.time_series];
              if (newTs.length > 0) {
                const last = { ...newTs[newTs.length - 1] };
                last.timestamp = sseData.timestamp;
                last.like_observed = sseData.metrics.like.observed;
                last.comment_observed = sseData.metrics.comment.observed;
                last.share_observed = sseData.metrics.share.observed;
                newTs[newTs.length - 1] = last;
              }
              return {
                ...prev,
                composite_score: sseData.composite_score,
                is_degraded: sseData.is_degraded,
                top_contributor: sseData.top_contributor,
                time_series: newTs,
              };
            });
          }
        } catch (e) {
          console.error('SSE JSON parse error:', e);
        }
      };

      eventSource.onerror = () => {
        setSseConnected(false);
        eventSource?.close();
      };
    } catch (e) {
      setSseConnected(false);
    }

    return () => {
      eventSource?.close();
    };
  }, []);

  if (loading && !data) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-100">
        <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl backdrop-blur-md">
          <RefreshCw className="h-6 w-6 animate-spin text-cyan-400" />
          <span className="font-semibold tracking-wide">Loading CAGED Causal Framework...</span>
        </div>
      </div>
    );
  }

  const latestAlert = alerts.length > 0 ? alerts[0] : null;

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-slate-100 font-sans">
      {/* Top Header */}
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <ShieldAlert className="h-7 w-7 text-cyan-400" />
            <h1 className="text-2xl font-bold tracking-tight text-white">
              CAGED <span className="text-xs font-semibold uppercase tracking-widest text-cyan-400">v1.0</span>
            </h1>
            <span
              className={`flex items-center gap-1.5 rounded-full px-3 py-0.5 text-xs font-bold uppercase tracking-wider ${
                sseConnected
                  ? 'border border-emerald-500/40 bg-emerald-950/60 text-emerald-300'
                  : 'border border-amber-500/40 bg-amber-950/60 text-amber-300'
              }`}
            >
              <Radio className={`h-3 w-3 ${sseConnected ? 'animate-pulse text-emerald-400' : 'text-amber-400'}`} />
              {sseConnected ? 'LIVE STREAMING' : 'POLLING'}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Causal Analysis for Guaranteed Engagement Degradation — Real-Time Policy Monitoring
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchDashboardData}
            className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-2 text-xs font-medium text-slate-300 transition hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>

          <button
            onClick={handleSimulatePolicy}
            disabled={simulating}
            className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-lg transition hover:brightness-110 disabled:opacity-50"
          >
            <Zap className="h-4 w-4" /> {simulating ? 'Simulating...' : 'Simulate Policy Change'}
          </button>

          <button
            onClick={fetchReport}
            className="flex items-center gap-2 rounded-lg border border-purple-500/30 bg-purple-950/40 px-4 py-2 text-xs font-semibold text-purple-300 transition hover:bg-purple-900/50"
          >
            <FileText className="h-4 w-4" /> View Causal Report
          </button>
        </div>
      </header>

      {/* Alert Banner */}
      {data?.is_degraded && (
        <div className="mb-6 flex items-center justify-between rounded-xl border border-rose-500/40 bg-gradient-to-r from-rose-950/70 via-rose-900/30 to-slate-900/90 p-4 shadow-xl backdrop-blur-md animate-pulse">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-rose-500/20 p-2 text-rose-400">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <div>
              <h3 className="font-bold text-rose-200">
                CRITICAL ENGAGEMENT DEGRADATION DETECTED
              </h3>
              <p className="text-xs text-rose-300/80">
                Composite Score <span className="font-bold">S = {data.composite_score.toFixed(2)}</span> (Threshold: {data.composite_threshold.toFixed(2)}). Top Contributor: <span className="uppercase text-white font-bold">{data.top_contributor}</span>
              </p>
            </div>
          </div>
          <span className="rounded-full bg-rose-500/20 px-3 py-1 text-xs font-bold uppercase tracking-wider text-rose-300">
            {latestAlert ? latestAlert.severity : 'CRITICAL'}
          </span>
        </div>
      )}

      {/* Overview Metric Cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-md">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Composite Score (S)</span>
            <Activity className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white">{data?.composite_score.toFixed(2)}</span>
            <span className="text-xs text-slate-400">/ thresh {data?.composite_threshold.toFixed(1)}</span>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Status:{' '}
            {data?.is_degraded ? (
              <span className="font-semibold text-rose-400">DEGRADED</span>
            ) : (
              <span className="font-semibold text-emerald-400">STABLE</span>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-md">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Active Policy ID</span>
            <Calendar className="h-4 w-4 text-purple-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-purple-300">
            {data?.active_policy_id || 'None'}
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Enacted At: {data ? new Date(data.policy_t0).toLocaleTimeString() : 'N/A'}
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-md">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Top Degraded Metric</span>
            <TrendingDown className="h-4 w-4 text-amber-400" />
          </div>
          <div className="mt-2 text-2xl font-bold uppercase text-amber-300">
            {data?.top_contributor || 'None'}
          </div>
          <div className="mt-2 text-xs text-slate-400">
            {data?.top_contributor && data.metric_results[data.top_contributor]
              ? `Z-Score: +${data.metric_results[data.top_contributor].positive_z_score.toFixed(2)}`
              : 'Within Normal Baseline'}
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-md">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Most Affected Segment</span>
            <Users className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2 text-2xl font-bold uppercase text-cyan-300">
            {segmentData?.most_degraded_segment || 'All Uniform'}
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Impact:{' '}
            {segmentData?.is_localized ? (
              <span className="font-semibold text-amber-400">LOCALIZED COMMUNITY</span>
            ) : (
              <span className="font-semibold text-emerald-400">UNIFORM PLATFORM</span>
            )}
          </div>
        </div>
      </div>

      {/* Main Chart Section: Observed vs Counterfactual Baseline */}
      <div className="mb-6 rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl backdrop-blur-md">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white">
              Causal Stream Degradation — Observed vs Frozen Baseline
            </h2>
            <p className="text-xs text-slate-400">
              Vertical red reference line marks Policy Trigger T0. Shaded region shows non-contaminated counterfactual expectation.
            </p>
          </div>

          <div className="flex rounded-lg border border-slate-800 bg-slate-950 p-1">
            {(['like', 'comment', 'share'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setActiveMetric(m)}
                className={`rounded-md px-3 py-1 text-xs font-semibold transition ${
                  activeMetric === m
                    ? 'bg-cyan-500 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {m.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data?.time_series || []} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="expectedGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="observedGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} />
              <XAxis
                dataKey="timestamp"
                stroke="#94a3b8"
                tickFormatter={(ts) => new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                tick={{ fontSize: 11 }}
              />
              <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                labelFormatter={(label) => new Date(label).toLocaleString()}
              />
              <Legend />
              {data && (
                <ReferenceLine
                  x={data.policy_t0}
                  stroke="#ef4444"
                  strokeDasharray="4 4"
                  strokeWidth={2}
                  label={{ value: 'Policy T0 Enacted', fill: '#ef4444', fontSize: 12, position: 'top' }}
                />
              )}
              <Area
                type="monotone"
                dataKey={`${activeMetric}_expected`}
                name="Frozen Counterfactual Baseline (Expected)"
                stroke="#06b6d4"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#expectedGradient)"
              />
              <Area
                type="monotone"
                dataKey={`${activeMetric}_observed`}
                name="Post-Policy Stream (Observed)"
                stroke="#f43f5e"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#observedGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom Grid: Metric Z-Score Heatmap Grid & Segment Breakdown */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Metric Z-Scores */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 backdrop-blur-md">
          <h3 className="mb-4 text-base font-bold text-white">
            Metric Z-Score Standardized Deviations
          </h3>
          <div className="space-y-3">
            {data &&
              Object.entries(data.metric_results).map(([mName, mRes]: [string, any]) => {
                const zPos = mRes.positive_z_score;
                const isDeg = mRes.is_degraded;
                return (
                  <div
                    key={mName}
                    className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 p-3"
                  >
                    <div>
                      <span className="font-bold text-white uppercase">{mName}</span>
                      <div className="text-xs text-slate-400">
                        Obs: {mRes.observed_value} | Exp: {mRes.expected_value} (D: {mRes.deviation > 0 ? `+${mRes.deviation}` : mRes.deviation})
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <div className="text-sm font-bold text-white">Z = +{zPos.toFixed(2)}</div>
                        <div className="text-xs text-slate-400">p = {mRes.p_value.toFixed(4)}</div>
                      </div>
                      <span
                        className={`rounded-lg px-2.5 py-1 text-xs font-bold uppercase ${
                          isDeg ? 'bg-rose-500/20 text-rose-300' : 'bg-emerald-500/20 text-emerald-300'
                        }`}
                      >
                        {isDeg ? 'DEGRADED' : 'STABLE'}
                      </span>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>

        {/* User Segment Localization */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 backdrop-blur-md">
          <h3 className="mb-4 text-base font-bold text-white">
            Community Segment Localization
          </h3>
          {segmentData?.segment_results ? (
            <div className="space-y-3">
              {Object.entries(segmentData.segment_results).map(([segId, segRes]: [string, any]) => (
                <div
                  key={segId}
                  className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 p-3"
                >
                  <div>
                    <span className="font-bold text-white capitalize">{segId} Users</span>
                    <div className="text-xs text-slate-400">
                      Top Degraded: {segRes.top_degraded_metric ? segRes.top_degraded_metric.toUpperCase() : 'None'}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-sm font-bold text-cyan-300">
                        S_s = {segRes.composite_score.toFixed(2)}
                      </div>
                    </div>
                    <span
                      className={`rounded-lg px-2.5 py-1 text-xs font-bold uppercase ${
                        segRes.is_degraded ? 'bg-rose-500/20 text-rose-300' : 'bg-emerald-500/20 text-emerald-300'
                      }`}
                    >
                      {segRes.is_degraded ? 'DEGRADED' : 'STABLE'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">Segment data loading...</p>
          )}
        </div>
      </div>

      {/* Report Modal */}
      {showReportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm">
          <div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 text-slate-100 shadow-2xl">
            <div className="mb-4 flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-cyan-400">CAGED Causal Degradation Report</h3>
              <button
                onClick={() => setShowReportModal(false)}
                className="rounded-lg bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-300 hover:bg-slate-700"
              >
                Close
              </button>
            </div>
            <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-200">
              {reportMarkdown}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
