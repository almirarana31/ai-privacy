import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface DPResult {
  dataset: string;
  model: string;
  epsilon: number;
  accuracy: number;
  std: number;
  baseline: number;
  accuracyLoss: number;
}

export interface FLResult {
  dataset: string;
  model: string;
  aggregation: string;
  accuracy: number;
  std: number;
  baseline: number;
}

export interface BaselineResult {
  dataset: string;
  model: string;
  accuracy: number;
  std: number;
  f1: number;
}

export interface VisualizationData {
  dp: DPResult[];
  fl: FLResult[];
  baseline: BaselineResult[];
  counts: {
    dp: number;
    fl: number;
    baseline: number;
  };
}

export const visualizationService = {
  // Get all visualization data in one call
  async getAllData(): Promise<VisualizationData> {
    const response = await api.get('/api/visualizations/all');
    return response.data;
  },

  // Get DP results only
  async getDPData(): Promise<{ data: DPResult[]; count: number }> {
    const response = await api.get('/api/visualizations/dp-results');
    return response.data;
  },

  // Get FL results only
  async getFLData(): Promise<{ data: FLResult[]; count: number }> {
    const response = await api.get('/api/visualizations/fl-results');
    return response.data;
  },

  // Get baseline results only
  async getBaselineData(): Promise<{ data: BaselineResult[]; count: number }> {
    const response = await api.get('/api/visualizations/baseline-results');
    return response.data;
  },
};

export default visualizationService;
