import axios from 'axios';
import { HealthStatusResponse } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 5000,
});

export const fetchHealthStatus = async (): Promise<{
  data: HealthStatusResponse;
  latencyMs: number;
}> => {
  const startTime = performance.now();
  const response = await apiClient.get<HealthStatusResponse>('/health');
  const endTime = performance.now();
  return {
    data: response.data,
    latencyMs: Math.round(endTime - startTime),
  };
};
