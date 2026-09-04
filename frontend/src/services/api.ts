const API_BASE = 'http://localhost:8000/api/v1';

export const apiService = {
  getMetrics: async () => {
    const res = await fetch(`${API_BASE}/dashboard/metrics`);
    if (!res.ok) throw new Error('Failed to fetch metrics');
    return res.json();
  },

  getPolicies: async () => {
    const res = await fetch(`${API_BASE}/dashboard/policies`);
    if (!res.ok) throw new Error('Failed to fetch policies');
    return res.json();
  },

  getSegments: async () => {
    const res = await fetch(`${API_BASE}/dashboard/segments`);
    if (!res.ok) throw new Error('Failed to fetch segments');
    return res.json();
  },

  getAlerts: async () => {
    const res = await fetch(`${API_BASE}/dashboard/alerts`);
    if (!res.ok) throw new Error('Failed to fetch alerts');
    return res.json();
  },

  getReport: async (format: 'json' | 'markdown' = 'json') => {
    const res = await fetch(`${API_BASE}/dashboard/report?format=${format}`);
    if (!res.ok) throw new Error('Failed to fetch report');
    return res.json();
  },

  simulatePolicy: async (payload: {
    policy_id: string;
    policy_name: string;
    impact_factor: number;
    description: string;
  }) => {
    const res = await fetch(`${API_BASE}/dashboard/simulate_policy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to simulate policy');
    return res.json();
  },

  toggleSimulation: async (start: boolean) => {
    const endpoint = start ? `${API_BASE}/simulation/start` : `${API_BASE}/simulation/stop`;
    const res = await fetch(endpoint, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to toggle simulation');
    return res.json();
  },

  getSystemHealth: async () => {
    const res = await fetch(`${API_BASE}/dashboard/system_health`);
    if (!res.ok) throw new Error('Failed to fetch system health');
    return res.json();
  },

  getDataQuality: async () => {
    const res = await fetch(`${API_BASE}/dashboard/data_quality`);
    if (!res.ok) throw new Error('Failed to fetch data quality');
    return res.json();
  },

  getSettings: async () => {
    const res = await fetch(`${API_BASE}/dashboard/settings`);
    if (!res.ok) throw new Error('Failed to fetch settings');
    return res.json();
  },

  updateSettings: async (settings: any) => {
    const res = await fetch(`${API_BASE}/dashboard/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    if (!res.ok) throw new Error('Failed to update settings');
    return res.json();
  },

  getMLPrediction: async () => {
    const res = await fetch(`${API_BASE}/dashboard/ml_prediction`);
    if (!res.ok) throw new Error('Failed to fetch ML prediction');
    return res.json();
  },

  // --- Phase 5 4-Pillar Architecture API Methods ---

  getPhase5Scenarios: async () => {
    const res = await fetch(`${API_BASE}/phase5/scenarios`);
    if (!res.ok) throw new Error('Failed to fetch Phase 5 scenarios');
    return res.json();
  },

  runPhase5Experiment: async (payload: {
    scenario_id?: string;
    num_users?: number;
    num_creators?: number;
    num_items?: number;
    pre_periods?: number;
    post_periods?: number;
    random_seed?: number;
    originality_weight_shift?: number;
    minimum_effect_size?: number;
    composite_threshold?: number;
  }) => {
    const res = await fetch(`${API_BASE}/phase5/run-experiment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to execute Phase 5 experiment');
    return res.json();
  },

  estimateDiD: async (payload: {
    metric_type?: string;
    pre_periods?: number;
    post_periods?: number;
    treatment_pre_values: number[];
    treatment_post_values: number[];
    control_pre_values: number[];
    control_post_values: number[];
    minimum_effect_size?: number;
  }) => {
    const res = await fetch(`${API_BASE}/phase5/did-estimate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to compute DiD estimate');
    return res.json();
  },

  predictMLCounterfactual: async (payload: {
    metric_type?: string;
    pre_periods?: number;
    post_periods?: number;
    telemetry_records: any[];
  }) => {
    const res = await fetch(`${API_BASE}/phase5/ml-counterfactual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to compute ML counterfactual prediction');
    return res.json();
  },
};
