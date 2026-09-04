export interface MetricData {
  timestamp: string;
  is_post_policy: boolean;
  like_expected: number;
  like_observed: number;
  comment_expected: number;
  comment_observed: number;
  share_expected: number;
  share_observed: number;
}

export interface MetricImpactRow {
  metric: string;
  expected: string;
  actual: string;
  change: string;
  zScore: string;
  status: 'Critical' | 'Warning' | 'Normal';
}

export interface PolicyEventItem {
  id: string;
  name: string;
  time: string;
  active?: boolean;
  description?: string;
  impact_factor?: number;
}

export interface SegmentItem {
  segment: string;
  users: string;
  degradation: string;
  zScore: string;
  status: 'Critical' | 'Warning' | 'Normal';
  engagementProfile?: string;
}

export interface AlertItem {
  id: string;
  title: string;
  subtitle: string;
  time: string;
  type: 'critical' | 'warning' | 'info';
  acknowledged?: boolean;
}

export interface SystemHealthData {
  backend_status: string;
  event_stream_status: string;
  database_status: string;
  caged_engine_status: string;
  event_rate_per_sec: number;
  processing_latency_ms: number;
  uptime: string;
  cpu_usage_pct: number;
  memory_usage_mb: number;
  queue_capacity: number;
  queue_size: number;
}

export interface DataQualityData {
  total_events_received: number;
  valid_events: number;
  duplicate_events: number;
  invalid_timestamps: number;
  filtered_noise_events: number;
  privacy_violations_blocked: number;
  processing_errors: number;
  data_quality_score: number;
}

export interface SettingsData {
  detection_threshold: number;
  target_false_alarm_rate: number;
  analysis_window_seconds: number;
  smoothing_alpha: number;
  cms_width: number;
  cms_depth: number;
  hll_precision: number;
  num_clusters: number;
  ml_enabled: boolean;
  prediction_horizon_minutes: number;
}
