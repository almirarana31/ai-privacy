import type { ModelParameters, TrainingData, ModelPerformance } from '../types.ts';

const API_BASE_URL = 'http://108.136.50.96:8000/api'; // Replace with your actual backend URL

export const runModel = async (
  parameters: ModelParameters,
  trainingData: TrainingData
): Promise<ModelPerformance> => {
  console.log('Running model with:', { parameters, trainingData });

  // Mock API call - replace with actual fetch to your backend
  await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate network delay

  // In a real implementation, you would use fetch:
  /*
  const response = await fetch(`${API_BASE_URL}/train`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ parameters, trainingData }),
  });

  if (!response.ok) {
    throw new Error('Failed to train model');
  }

  const results: ModelPerformance = await response.json();
  return results;
  */

  // Mock performance data
  const mockPerformance: ModelPerformance = {
    accuracy: Math.random() * 0.2 + 0.75, // 0.75 - 0.95
    precision: Math.random() * 0.2 + 0.7, // 0.7 - 0.9
    recall: Math.random() * 0.2 + 0.7,    // 0.7 - 0.9
    privacyLoss: parameters.privacyBudget * (Math.random() * 0.1 + 0.05),
    errorLoss: (100 - parameters.epochs) / 100 * (Math.random() * 0.1 + 0.05)
  };

  return mockPerformance;
};
