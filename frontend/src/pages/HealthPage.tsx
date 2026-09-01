import React, { useEffect, useState, useCallback } from 'react';
import { fetchHealthStatus } from '../services/api';
import { HealthStatusResponse } from '../types/api';
import { Activity, RefreshCw, CheckCircle2, AlertTriangle, Server, Clock, Zap, Cpu } from 'lucide-react';

export const HealthPage: React.FC = () => {
  const [healthData, setHealthData] = useState<HealthStatusResponse | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  const checkHealth = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchHealthStatus();
      setHealthData(res.data);
      setLatency(res.latencyMs);
      setError(null);
      setLastUpdated(new Date());
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to connect to CAGED backend service';
      setError(message);
      setHealthData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    if (!autoRefresh) return;
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, [checkHealth, autoRefresh]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Page Banner Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Activity style={{ color: 'var(--accent-primary)' }} />
            Backend System Health
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Real-time operational monitoring and API readiness metrics for CAGED services.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`btn ${autoRefresh ? 'btn-primary' : 'btn-outline'}`}
          >
            <RefreshCw size={16} className={autoRefresh && loading ? 'spin' : ''} />
            {autoRefresh ? 'Auto-Refresh ON (5s)' : 'Auto-Refresh OFF'}
          </button>

          <button onClick={checkHealth} className="btn btn-outline" disabled={loading}>
            Refresh Now
          </button>
        </div>
      </div>

      {/* Main Status Overview Card */}
      <div className="glass-card" style={{ padding: '32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '16px',
                background: error ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: error ? 'var(--danger)' : 'var(--success)',
              }}
            >
              {error ? <AlertTriangle size={32} /> : <CheckCircle2 size={32} />}
            </div>

            <div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Service Status
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700, color: error ? 'var(--danger)' : 'var(--success)' }}>
                {error ? 'UNREACHABLE' : 'OPERATIONAL'}
              </div>
            </div>
          </div>

          {!error && healthData && (
            <div className="badge badge-success" style={{ fontSize: '0.9rem', padding: '6px 16px' }}>
              <span className="status-dot active"></span>
              GET /health 200 OK
            </div>
          )}
        </div>

        {error ? (
          <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', padding: '16px', borderRadius: 'var(--radius-sm)', color: '#fca5a5' }}>
            <strong>Connection Exception:</strong> {error}
            <div style={{ marginTop: '8px', fontSize: '0.85rem' }}>
              Ensure the FastAPI backend server is running on <code>http://localhost:8000</code>.
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginTop: '24px' }}>
            <div style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-color)', padding: '20px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '6px' }}>
                <Server size={16} /> Service Name
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 600 }} className="mono">
                {healthData?.service}
              </div>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-color)', padding: '20px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '6px' }}>
                <Zap size={16} /> API Latency
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--accent-cyan)' }} className="mono">
                {latency !== null ? `${latency} ms` : '--'}
              </div>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-color)', padding: '20px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '6px' }}>
                <Clock size={16} /> Last Polled
              </div>
              <div style={{ fontSize: '1rem', fontWeight: 500 }} className="mono">
                {lastUpdated ? lastUpdated.toLocaleTimeString() : '--'}
              </div>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-color)', padding: '20px', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '6px' }}>
                <Cpu size={16} /> Environment
              </div>
              <div style={{ fontSize: '1.25rem', fontWeight: 600 }} className="mono">
                development
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Raw Payload Card */}
      {healthData && (
        <div className="glass-card" style={{ padding: '24px' }}>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '12px' }}>Raw Endpoint Response</h3>
          <pre className="mono" style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', overflowX: 'auto', color: '#a5f3fc' }}>
            {JSON.stringify(healthData, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};
