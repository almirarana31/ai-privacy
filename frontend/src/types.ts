export interface ModelParameters {
  epochs: number;
  privacyBudget: number;
}

export interface TrainingData {
  fileName: string;
  data: (string | number)[][];
}

export interface ModelPerformance {
  accuracy: number;
  precision: number;
  recall: number;
  privacyLoss: number;
  errorLoss: number;
}
