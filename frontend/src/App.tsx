import React, { useState, useRef } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000';

type Config = {
  sampleDataset: string;
  modelType: string;
  dpEnabled: boolean;
  epsilon?: number;
};

type Result = {
  baselineAccuracy: number;
  privateAccuracy?: number;
  accuracyLoss?: number;
  f1Score?: number;
  precision?: number;
  recall?: number;
  epsilon?: number;
  samplesEvaluated: number;
  modelUsed: string;
};

type UploadInfo = {
  fileName: string;
  targetColumn?: string;
};

const App: React.FC = () => {
  const [config, setConfig] = useState<Config>({
    sampleDataset: 'diabetes',
    modelType: 'fnn',
    dpEnabled: false,
    epsilon: 1.0,
  });
  const [status, setStatus] = useState<'idle' | 'running'>('idle');
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [uploadInfo, setUploadInfo] = useState<UploadInfo | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isLoading = status === 'running';

  const runExperiment = async () => {
    setStatus('running');
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/experiment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          dataset: config.sampleDataset,
          model_type: config.modelType,
          dp_enabled: config.dpEnabled,
          epsilon: config.dpEnabled ? config.epsilon : null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to run experiment');
      }

      const data = await response.json();
      setResult({
        baselineAccuracy: data.baseline_accuracy,
        privateAccuracy: data.private_accuracy,
        accuracyLoss: data.accuracy_loss,
        f1Score: data.f1_score,
        precision: data.precision,
        recall: data.recall,
        epsilon: data.epsilon,
        samplesEvaluated: data.samples_evaluated,
        modelUsed: data.model_used,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    }

    setStatus('idle');
  };

  const runExperimentWithUpload = async () => {
    if (!fileInputRef.current?.files?.[0]) {
      setError('Please select a CSV file first');
      return;
    }

    setStatus('running');
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', fileInputRef.current.files[0]);
      formData.append('dataset', config.sampleDataset);
      formData.append('model_type', config.modelType);
      formData.append('dp_enabled', String(config.dpEnabled));
      if (config.dpEnabled && config.epsilon) {
        formData.append('epsilon', String(config.epsilon));
      }
      if (uploadInfo?.targetColumn) {
        formData.append('target_column', uploadInfo.targetColumn);
      }

      const response = await fetch(`${API_BASE_URL}/api/experiment/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to run experiment');
      }

      const data = await response.json();
      setResult({
        baselineAccuracy: data.baseline_accuracy,
        privateAccuracy: data.private_accuracy,
        accuracyLoss: data.accuracy_loss,
        f1Score: data.f1_score,
        precision: data.precision,
        recall: data.recall,
        epsilon: data.epsilon,
        samplesEvaluated: data.samples_evaluated,
        modelUsed: data.model_used,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    }

    setStatus('idle');
  };

  const updateConfig = (newConfig: Partial<Config>) => {
    setConfig((prev) => ({ ...prev, ...newConfig }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadInfo({
        fileName: file.name,
        targetColumn: undefined,
      });
    } else {
      setUploadInfo(null);
    }
  };

  const clearUpload = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setUploadInfo(null);
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🔒 Privacy Playground</h1>
        <p>Test pre-trained models with differential privacy</p>
      </header>

      <main className="main">
        {/* Quick Test Section */}
        <section className="card">
          <h2>Quick Test</h2>
          <div className="quick-tests">
            <button
              className="test-btn baseline"
              onClick={() => {
                updateConfig({
                  sampleDataset: 'diabetes',
                  modelType: 'fnn',
                  dpEnabled: false,
                });
                setTimeout(runExperiment, 100);
              }}
              disabled={isLoading}
            >
              <div className="test-btn-title">Baseline - Diabetes</div>
              <div className="test-btn-desc">FNN, No privacy protection</div>
            </button>

            <button
              className="test-btn dp"
              onClick={() => {
                updateConfig({
                  sampleDataset: 'diabetes',
                  modelType: 'fnn',
                  dpEnabled: true,
                  epsilon: 1.0,
                });
                setTimeout(runExperiment, 100);
              }}
              disabled={isLoading}
            >
              <div className="test-btn-title">DP - Diabetes (ε=1.0)</div>
              <div className="test-btn-desc">FNN-DP, High privacy</div>
            </button>

            <button
              className="test-btn baseline"
              onClick={() => {
                updateConfig({
                  sampleDataset: 'adult',
                  modelType: 'lr',
                  dpEnabled: false,
                });
                setTimeout(runExperiment, 100);
              }}
              disabled={isLoading}
            >
              <div className="test-btn-title">Baseline - Adult</div>
              <div className="test-btn-desc">Logistic Regression</div>
            </button>

            <button
              className="test-btn dp"
              onClick={() => {
                updateConfig({
                  sampleDataset: 'adult',
                  modelType: 'lr',
                  dpEnabled: true,
                  epsilon: 3.0,
                });
                setTimeout(runExperiment, 100);
              }}
              disabled={isLoading}
            >
              <div className="test-btn-title">DP - Adult (ε=3.0)</div>
              <div className="test-btn-desc">LR-DP, Moderate privacy</div>
            </button>
          </div>
        </section>

        {/* Custom Configuration */}
        <section className="card">
          <div className="card-header">
            <h2>Custom Configuration</h2>
            <button 
              className="toggle-advanced"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              {showAdvanced ? '▼ Hide' : '▶ Show'} Advanced
            </button>
          </div>

          <div className="config-grid">
            <div className="field">
              <label>Dataset</label>
              <select
                value={config.sampleDataset}
                onChange={(e) => updateConfig({ sampleDataset: e.target.value })}
              >
                <option value="diabetes">Diabetes (21 features)</option>
                <option value="adult">Adult Income (14 features)</option>
              </select>
            </div>

            <div className="field">
              <label>Model Type</label>
              <select
                value={config.modelType}
                onChange={(e) => updateConfig({ modelType: e.target.value })}
              >
                <option value="fnn">Feedforward Neural Network</option>
                <option value="lr">Logistic Regression</option>
              </select>
            </div>

            <div className="field">
              <label>
                Differential Privacy
                <span className="field-hint">Add noise to protect privacy</span>
              </label>
              <div className="checkbox-row">
                <input
                  type="checkbox"
                  id="dp-toggle"
                  checked={config.dpEnabled}
                  onChange={(e) => updateConfig({ dpEnabled: e.target.checked })}
                />
                <label htmlFor="dp-toggle">Enable</label>
              </div>
            </div>

            {config.dpEnabled && (
              <div className="field">
                <label>
                  Epsilon (ε): {config.epsilon}
                  <span className="field-hint">Lower = more privacy, less accuracy</span>
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="10"
                  step="0.5"
                  value={config.epsilon || 1.0}
                  onChange={(e) => updateConfig({ epsilon: parseFloat(e.target.value) })}
                />
                <div className="epsilon-labels">
                  <span>0.5 (High Privacy)</span>
                  <span>10 (Low Privacy)</span>
                </div>
              </div>
            )}

            {showAdvanced && (
              <div className="field upload-field">
                <label>
                  Upload Custom CSV
                  <span className="field-hint">Test with your own data</span>
                </label>
                <input
                  type="file"
                  ref={fileInputRef}
                  accept=".csv"
                  onChange={handleFileChange}
                  className="file-input"
                />
                {uploadInfo && (
                  <div className="upload-info">
                    <span>📄 {uploadInfo.fileName}</span>
                    <button className="clear-upload" onClick={clearUpload}>×</button>
                  </div>
                )}
                {uploadInfo && (
                  <div className="target-column-field">
                    <label>Target Column (optional)</label>
                    <input
                      type="text"
                      placeholder="e.g., target, label, class"
                      value={uploadInfo.targetColumn || ''}
                      onChange={(e) => setUploadInfo({ ...uploadInfo, targetColumn: e.target.value })}
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="button-row">
            <button
              className="run-btn"
              onClick={runExperiment}
              disabled={isLoading}
            >
              {isLoading ? '⏳ Running...' : '▶ Run with Test Data'}
            </button>
            
            {showAdvanced && uploadInfo && (
              <button
                className="run-btn upload-btn"
                onClick={runExperimentWithUpload}
                disabled={isLoading}
              >
                {isLoading ? '⏳ Running...' : '📤 Run with Upload'}
              </button>
            )}
          </div>
        </section>

        {/* Results */}
        {error && (
          <section className="card error-card">
            <h2>❌ Error</h2>
            <pre className="error-text">{error}</pre>
          </section>
        )}

        {result && (
          <section className="card results-card">
            <h2>📊 Results</h2>
            
            <div className="result-model-info">
              <span className="model-badge">{result.modelUsed}</span>
              <span className="samples-info">{result.samplesEvaluated} samples evaluated</span>
            </div>
            
            <div className="metrics-grid">
              <div className="metric">
                <div className="metric-label">
                  {config.dpEnabled ? 'Private Accuracy' : 'Baseline Accuracy'}
                </div>
                <div className={`metric-value ${config.dpEnabled ? 'private-value' : 'baseline-value'}`}>
                  {config.dpEnabled 
                    ? (result.privateAccuracy ?? result.baselineAccuracy).toFixed(2)
                    : result.baselineAccuracy.toFixed(2)}%
                </div>
              </div>

              {config.dpEnabled && result.accuracyLoss !== undefined && (
                <div className="metric">
                  <div className="metric-label">Accuracy Loss</div>
                  <div className="metric-value loss-value">
                    {result.accuracyLoss.toFixed(2)}%
                  </div>
                </div>
              )}

              {config.dpEnabled && result.epsilon !== undefined && (
                <div className="metric">
                  <div className="metric-label">Epsilon (ε)</div>
                  <div className="metric-value epsilon-value">
                    {result.epsilon}
                  </div>
                </div>
              )}

              {result.f1Score !== undefined && (
                <div className="metric">
                  <div className="metric-label">F1 Score</div>
                  <div className="metric-value">
                    {result.f1Score.toFixed(4)}
                  </div>
                </div>
              )}

              {result.precision !== undefined && (
                <div className="metric">
                  <div className="metric-label">Precision</div>
                  <div className="metric-value">
                    {result.precision.toFixed(4)}
                  </div>
                </div>
              )}

              {result.recall !== undefined && (
                <div className="metric">
                  <div className="metric-label">Recall</div>
                  <div className="metric-value">
                    {result.recall.toFixed(4)}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {isLoading && (
          <section className="card loading-card">
            <div className="loading-spinner"></div>
            <p>Loading pre-trained model and evaluating...</p>
          </section>
        )}
      </main>
    </div>
  );
};

export default App;
