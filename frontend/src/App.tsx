import React, { useState, useRef } from 'react';
import './App.css';
// import DashboardPage from './pages/DashboardPage';

// Use Docker service name for backend when running in Docker, or localhost for local dev
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://y6mhhtvkvp.ap-southeast-1.awsapprunner.com/api';


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
  aggregator?: string;
  strategy?: 'dp' | 'fl';
};

type ComparisonData = {
  baseline: Result | null;
  private: Result | null;
};

type UploadInfo = {
  fileName: string;
  targetColumn?: string;
};

type EthicsQuestion = {
  id: string;
  question: string;
  options: string[];
  context?: string;
};

type EthicsResponse = {
  questionId: string;
  answer: string;
};

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'playground' | 'survey' | 'dataset' | 'visualization'>('playground');
  const [trainingMode, setTrainingMode] = useState<'dp' | 'fl'>('dp');
  const [aggregator, setAggregator] = useState<'fedavg' | 'fedprox' | 'qffl' | 'scaffold' | 'fedadam'>('fedavg');
  const [config, setConfig] = useState<Config>({
    sampleDataset: 'diabetes',
    modelType: 'fnn',
    dpEnabled: true,
    epsilon: 1.0,
  });
  const [status, setStatus] = useState<'idle' | 'running'>('idle');
  const [comparison, setComparison] = useState<ComparisonData>({
    baseline: null,
    private: null,
  });
  const [error, setError] = useState<string | null>(null);
  const [uploadInfo, setUploadInfo] = useState<UploadInfo | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [showWelcomeModal, setShowWelcomeModal] = useState(true);
  const [showEthicsPrompt, setShowEthicsPrompt] = useState(false);
  const [ethicsResponses, setEthicsResponses] = useState<EthicsResponse[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedDataset, setSelectedDataset] = useState<'diabetes' | 'adult'>('diabetes');
  const [lastEthicsPromptTime, setLastEthicsPromptTime] = useState<number>(0);
  const ETHICS_PROMPT_COOLDOWN_MS = 30000; // 30 seconds cooldown

  const isLoading = status === 'running';

  const aggregatorOptions = [
    {
      value: 'fedavg',
      label: 'FedAvg',
      description: 'Classic federated averaging across participating clients.',
      bestFor: 'Stable, balanced data with similar client sizes.'
    },
    {
      value: 'fedprox',
      label: 'FedProx',
      description: 'Adds a proximal term to stabilize training with heterogeneous data.',
      bestFor: 'Non-IID data where clients drift from the global objective.'
    },
    {
      value: 'qffl',
      label: 'q-FedAvg',
      description: 'Reweights updates to emphasize underperforming clients.',
      bestFor: 'Fairness-sensitive setups and skewed performance across clients.'
    },
    {
      value: 'scaffold',
      label: 'SCAFFOLD',
      description: 'Uses control variates to reduce client drift during aggregation.',
      bestFor: 'Highly non-IID data with client-specific biases.'
    },
    {
      value: 'fedadam',
      label: 'FedAdam',
      description: 'Adaptive federated optimization with momentum and adaptive learning rates.',
      bestFor: 'Fast convergence and handling diverse client distributions.'
    },
  ];

  // Ethics questions that adapt to experiment results
  const getEthicsQuestions = (): EthicsQuestion[] => {
    const accuracyLoss = comparison.baseline && comparison.private
      ? (comparison.baseline.baselineAccuracy - comparison.private.baselineAccuracy).toFixed(2)
      : '0';
    
    const epsilon = comparison.private?.epsilon || config.epsilon;

    return [
      {
        id: 'usecase',
        question: `Given this result (${accuracyLoss}% accuracy loss with ε=${epsilon}), which use case would you feel comfortable deploying this model for?`,
        options: [
          'Healthcare diagnosis (high stakes)',
          'Product recommendations (low stakes)',
          'Financial fraud detection (medium stakes)',
          'I would not deploy this model',
        ],
        context: 'Consider the real-world impact of prediction errors.'
      },
      {
        id: 'acceptable_loss',
        question: 'What is the maximum acceptable accuracy loss for privacy protection in sensitive applications?',
        options: [
          'Less than 1% - Privacy is important but accuracy is critical',
          '1-3% - Moderate tradeoff is acceptable',
          '3-5% - Privacy should be prioritized',
          'More than 5% - Maximum privacy at any cost',
        ],
      },
      {
        id: 'transparency',
        question: 'Should companies using AI models be legally required to disclose their privacy parameters (like epsilon)?',
        options: [
          'Yes, always - Users have a right to know',
          'Only for sensitive data (health, finance)',
          'No, it\'s a business decision',
          'Unsure',
        ],
      },
    ];
  };

  const runExperiment = async (runBaseline: boolean = false) => {
    setStatus('running');
    setError(null);

    try {
      const dpEnabledForRun = runBaseline ? false : config.dpEnabled;
      
      console.log('Sending request:', {
        dataset: config.sampleDataset,
        model_type: config.modelType,
        dp_enabled: dpEnabledForRun,
        epsilon: dpEnabledForRun ? config.epsilon : null,
      });

      const response = await fetch(`${API_BASE_URL}/api/experiment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          dataset: config.sampleDataset,
          model_type: config.modelType,
          dp_enabled: dpEnabledForRun,
          epsilon: dpEnabledForRun ? config.epsilon : null,
        }),
      });

      console.log('Response status:', response.status);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Failed to run experiment');
      }

      const data = await response.json();
      console.log('Response data:', data);

      if (runBaseline) {
        // For baseline run, use baseline_accuracy and baseline metrics
        const result: Result = {
          baselineAccuracy: data.baseline_accuracy || 0,
          f1Score: data.f1_score,
          precision: data.precision,
          recall: data.recall,
          samplesEvaluated: data.samples_evaluated || 0,
          modelUsed: data.model_used || 'Unknown',
          strategy: 'dp',
        };
        setComparison(prev => ({ ...prev, baseline: result }));
      } else {
        // For DP run, use private_accuracy (which is the DP model's accuracy)
        const result: Result = {
          baselineAccuracy: data.private_accuracy || data.baseline_accuracy || 0,
          privateAccuracy: data.private_accuracy,
          accuracyLoss: data.accuracy_loss,
          f1Score: data.f1_score,
          precision: data.precision,
          recall: data.recall,
          epsilon: data.epsilon || config.epsilon,  // Use requested epsilon if backend doesn't return one
          samplesEvaluated: data.samples_evaluated || 0,
          modelUsed: data.model_used || 'Unknown',
          strategy: 'dp',
        };
        setComparison(prev => ({ ...prev, private: result }));
      }
    } catch (err) {
      console.error('Error in runExperiment:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    }

    setStatus('idle');
  };

  const getAggregatorLabel = (value: string) => {
    const option = aggregatorOptions.find((o) => o.value === value);
    return option ? option.label : value;
  };

  const runFederatedExperiment = async () => {
    setStatus('running');
    setError(null);

    try {
      // Map frontend aggregator values to backend values
      const aggregatorMap: Record<string, string> = {
        'fedavg': 'FedAvg',
        'fedprox': 'FedProx',
        'qffl': 'q-FedAvg',
        'scaffold': 'SCAFFOLD',
        'fedadam': 'FedAdam',
      };

      const backendAggregator = aggregatorMap[aggregator] || 'FedAvg';

      const response = await fetch(`${API_BASE_URL}/api/fl/experiment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          dataset: config.sampleDataset,
          model_type: config.modelType,
          aggregation: backendAggregator,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || 'Failed to run federated experiment');
      }

      const data = await response.json();
      const aggLabel = getAggregatorLabel(aggregator);

      const baselineAcc = data.baseline_accuracy || 0;
      const flAccuracy = data.accuracy || 0;
      const result: Result = {
        baselineAccuracy: baselineAcc,
        privateAccuracy: flAccuracy,
        accuracyLoss: data.accuracy_loss !== undefined ? data.accuracy_loss : (baselineAcc - flAccuracy),
        f1Score: data.f1_score,
        precision: data.precision,
        recall: data.recall,
        epsilon: undefined,
        samplesEvaluated: data.samples_evaluated || 0,
        modelUsed: `${aggLabel} (Federated)`,
        aggregator: backendAggregator,
        strategy: 'fl',
      };

      setComparison((prev) => ({ ...prev, private: result }));
    } catch (err) {
      console.error('Error in runFederatedExperiment:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    }

    setStatus('idle');
  };

  const runComparison = async () => {
    setComparison({ baseline: null, private: null });
    setShowEthicsPrompt(false);
    setError(null);

    if (trainingMode === 'dp') {
      await runExperiment(true);  // Run baseline
      if (config.dpEnabled) {
        await runExperiment(false); // Run DP version
        setTimeout(() => {
          // Check cooldown before showing ethics prompt
          const now = Date.now();
          if (now - lastEthicsPromptTime >= ETHICS_PROMPT_COOLDOWN_MS) {
            setShowEthicsPrompt(true);
            setLastEthicsPromptTime(now);
          }
        }, 3000);
      }
    } else {
      await runExperiment(true); // Baseline for comparison
      await runFederatedExperiment();
    }
  };

  const handleSurveyRedirect = () => {
    setShowEthicsPrompt(false);
    setActiveTab('survey');
  };

  const skipSurvey = () => {
    setShowEthicsPrompt(false);
  };

  const handleEthicsAnswer = (answer: string) => {
    const questions = getEthicsQuestions();
    setEthicsResponses([...ethicsResponses, {
      questionId: questions[currentQuestion].id,
      answer
    }]);

    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      setShowEthicsPrompt(false);
    }
  };

  const skipEthicsQuestion = () => {
    const questions = getEthicsQuestions();
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      setShowEthicsPrompt(false);
    }
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

  const hasResults = comparison.baseline || comparison.private;

  return (
    <div className="playground">
      {/* Welcome Modal */}
      {showWelcomeModal && (
        <div className="modal-overlay">
          <div className="modal welcome-modal">
            <h2>Welcome to Privacy Playground</h2>
            <div className="modal-content">
              <p className="lead">
                Explore the ethical dilemma at the heart of modern AI: <strong>privacy vs accuracy</strong>.
              </p>
              
              <div className="ethics-intro">
                <h3>Why Privacy Matters</h3>
                <ul>
                  <li><strong>Real consequences:</strong> AI models can memorize sensitive training data</li>
                  <li><strong>Personal exposure:</strong> Medical records, financial data, personal behaviors can leak</li>
                  <li><strong>Differential Privacy:</strong> Adds mathematical guarantees to protect individuals</li>
                </ul>
              </div>

              <div className="ethics-intro">
                <h3>The Tradeoff</h3>
                <p>
                  Adding privacy protection reduces model accuracy. Your task: explore different 
                  privacy levels and decide what tradeoffs are acceptable.
                </p>
              </div>

              <div className="ethics-question-box">
                <p><strong>💭 Think about:</strong> What if this was <em>your</em> health data? Would you accept less accurate predictions in exchange for privacy?</p>
              </div>

              <button className="modal-button" onClick={() => setShowWelcomeModal(false)}>
                Start Exploring
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Ethics Prompt Modal - Simplified to survey redirect */}
      {showEthicsPrompt && comparison.private && (
        <div className="modal-overlay">
          <div className="modal ethics-modal">
            <div className="modal-header">
              <h2>🤔 Reflect on Your Results</h2>
            </div>
            
            <div className="modal-content">
              <div className="question-context">
                You've just seen the privacy-accuracy tradeoff firsthand!
              </div>
              
              <h3 className="ethics-question">
                Help us understand your perspective on AI privacy and ethics.
              </h3>
              
              <div className="survey-prompt">
                <p>
                  Your experiment showed a <strong>{(comparison.baseline!.baselineAccuracy - comparison.private!.baselineAccuracy).toFixed(2)}% accuracy loss</strong> with 
                  epsilon = <strong>{comparison.private.epsilon}</strong>.
                </p>
                <p>
                  Take our brief survey to share your thoughts on when this tradeoff is acceptable.
                </p>
              </div>

              <div className="ethics-options">
                <button
                  className="ethics-option primary"
                  onClick={handleSurveyRedirect}
                >
                  📋 Take the Ethics Survey
                </button>
                <button
                  className="ethics-option secondary"
                  onClick={skipSurvey}
                >
                  Maybe Later
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <header className="header">
        <h1>🔒 Differential Privacy Playground</h1>
        <nav className="tabs">
          {/* Interactive Dashboard tab removed */}
          <button 
            className={`tab ${activeTab === 'playground' ? 'active' : ''}`}
            onClick={() => setActiveTab('playground')}
          >
            🎮 Playground
          </button>
          <button 
            className={`tab ${activeTab === 'dataset' ? 'active' : ''}`}
            onClick={() => setActiveTab('dataset')}
          >
            📁 Dataset Explorer
          </button>
          <button 
            className={`tab ${activeTab === 'visualization' ? 'active' : ''}`}
            onClick={() => setActiveTab('visualization')}
          >
            📈 Visualization
          </button>
          <button 
            className={`tab ${activeTab === 'survey' ? 'active' : ''}`}
            onClick={() => setActiveTab('survey')}
          >
            📋 Ethics Survey
          </button>
        </nav>
      </header>

      {/* DashboardPage removed */}

      {activeTab === 'playground' && (
      <div className="playground-container">
        {/* Left Panel - Configuration */}
        <aside className="left-panel">
          <section className="control-section">
            <h3>Data</h3>
            <div className="control-group">
              <label>Dataset</label>
              <select
                value={config.sampleDataset}
                onChange={(e) => updateConfig({ sampleDataset: e.target.value })}
              >
                <option value="diabetes">Diabetes</option>
                <option value="adult">Adult Income</option>
              </select>
            </div>
          </section>

          <section className="control-section">
            <h3>Model</h3>
            <div className="control-group">
              <label>Type</label>
              <select
                value={config.modelType}
                onChange={(e) => updateConfig({ modelType: e.target.value })}
              >
                <option value="fnn">Neural Network</option>
                <option value="lr">Logistic Regression</option>
              </select>
            </div>
          </section>

          <section className="control-section">
            <h3>Training Strategy</h3>
            <div className="control-group">
              <label className="checkbox-label">
                <input
                  type="radio"
                  name="training-mode"
                  checked={trainingMode === 'dp'}
                  onChange={() => {
                    setTrainingMode('dp');
                    updateConfig({ dpEnabled: true });
                  }}
                />
                <span>Differential Privacy</span>
              </label>
              <label className="checkbox-label">
                <input
                  type="radio"
                  name="training-mode"
                  checked={trainingMode === 'fl'}
                  onChange={() => {
                    setTrainingMode('fl');
                    updateConfig({ dpEnabled: false });
                  }}
                />
                <span>Federated Learning</span>
              </label>
            </div>

            {trainingMode === 'fl' && (
              <div className="control-group">
                <label>Aggregation Method</label>
                <select
                  value={aggregator}
                  onChange={(e) => setAggregator(e.target.value as typeof aggregator)}
                >
                  {aggregatorOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <small className="hint">
                  {aggregatorOptions.find((o) => o.value === aggregator)?.description}
                </small>
              </div>
            )}
          </section>

          {trainingMode === 'dp' && (
            <section className="control-section">
              <h3>Privacy</h3>
              <div className="control-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={config.dpEnabled}
                    onChange={(e) => updateConfig({ dpEnabled: e.target.checked })}
                  />
                  <span>Enable Differential Privacy</span>
                </label>
              </div>

              {config.dpEnabled && (
                <div className="control-group">
                  <label>Epsilon (ε): {config.epsilon}</label>
                  <input
                    type="range"
                    min="0"
                    max="3"
                    step="1"
                    value={[0.5, 1.0, 3.0, 10.0].indexOf(config.epsilon || 1.0)}
                    onChange={(e) => {
                      const epsilonValues = [0.5, 1.0, 3.0, 10.0];
                      updateConfig({ epsilon: epsilonValues[parseInt(e.target.value)] });
                    }}
                    className="slider"
                  />
                  <div className="epsilon-markers">
                    <span className={config.epsilon === 0.5 ? 'active' : ''}>0.5</span>
                    <span className={config.epsilon === 1.0 ? 'active' : ''}>1.0</span>
                    <span className={config.epsilon === 3.0 ? 'active' : ''}>3.0</span>
                    <span className={config.epsilon === 10.0 ? 'active' : ''}>10.0</span>
                  </div>
                  <div className="slider-labels">
                    <span>More Private</span>
                    <span>Less Private</span>
                  </div>
                </div>
              )}
            </section>
          )}

          <button
            className="run-button"
            onClick={runComparison}
            disabled={isLoading}
          >
            {isLoading ? '⏳ Running...' : trainingMode === 'fl' ? '▶ Run Federated' : '▶ Run Experiment'}
          </button>

          {error && (
            <div className="error-box">
              <strong>Error:</strong> {error}
            </div>
          )}
        </aside>

        {/* Center Panel - Visualization */}
        <main className="center-panel">
          {!hasResults && !isLoading && (
            <div className="placeholder">
              <div className="placeholder-icon">📊</div>
              <h2>Privacy vs Accuracy Tradeoff</h2>
              <p>Configure your experiment and click "Run Experiment" to see results</p>
            </div>
          )}

          {isLoading && (
            <div className="loading-visualization">
              <div className="spinner"></div>
              <p>Evaluating model...</p>
            </div>
          )}

          {hasResults && !isLoading && (
            <div className="visualization">
              <h2>Results</h2>
              
              <div className="comparison-grid">
                {comparison.baseline && (
                  <div className="result-card baseline-card">
                    <h3>🎯 Baseline (No Privacy)</h3>
                    <div className="model-info">{comparison.baseline.modelUsed}</div>
                    <div className="big-metric">
                      <div className="metric-label">Accuracy</div>
                      <div className="metric-value">{comparison.baseline.baselineAccuracy.toFixed(2)}%</div>
                    </div>
                    <div className="small-metrics">
                      <div className="small-metric">
                        <span>F1 Score:</span>
                        <strong>{comparison.baseline.f1Score !== undefined ? `${comparison.baseline.f1Score.toFixed(2)}%` : 'N/A'}</strong>
                      </div>
                      <div className="small-metric">
                        <span>Precision:</span>
                        <strong>{comparison.baseline.precision !== undefined ? `${comparison.baseline.precision.toFixed(2)}%` : 'N/A'}</strong>
                      </div>
                      <div className="small-metric">
                        <span>Recall:</span>
                        <strong>{comparison.baseline.recall !== undefined ? `${comparison.baseline.recall.toFixed(2)}%` : 'N/A'}</strong>
                      </div>
                      <div className="small-metric">
                        <span>Samples:</span>
                        <strong>{comparison.baseline.samplesEvaluated.toLocaleString()}</strong>
                      </div>
                    </div>
                  </div>
                )}

                {comparison.private && trainingMode === 'dp' && config.dpEnabled && (
                  <div className="result-card private-card">
                    <h3>🔒 With Privacy (ε={comparison.private.epsilon})</h3>
                    <div className="model-info">{comparison.private.modelUsed}</div>
                    <div className="big-metric">
                      <div className="metric-label">Accuracy</div>
                      <div className="metric-value">{comparison.private.privateAccuracy?.toFixed(2) || comparison.private.baselineAccuracy.toFixed(2)}%</div>
                    </div>
                    {comparison.baseline && (
                      <div className="accuracy-loss">
                        Loss: {(comparison.baseline.baselineAccuracy - (comparison.private.privateAccuracy || comparison.private.baselineAccuracy)).toFixed(2)}%
                      </div>
                    )}
                    <div className="small-metrics">
                      <div className="small-metric">
                        <span>F1 Score:</span>
                        <strong>{comparison.private.f1Score !== undefined ? `${comparison.private.f1Score.toFixed(2)}%` : 'N/A'}</strong>
                      </div>
                      <div className="small-metric">
                        <span>Precision:</span>
                        <strong>{comparison.private.precision !== undefined ? `${comparison.private.precision.toFixed(2)}%` : 'N/A'}</strong>
                      </div>
                      <div className="small-metric">
                        <span>Recall:</span>
                        <strong>{comparison.private.recall !== undefined ? `${comparison.private.recall.toFixed(2)}%` : 'N/A'}</strong>
                      </div>
                      <div className="small-metric">
                        <span>Samples:</span>
                        <strong>{comparison.private.samplesEvaluated.toLocaleString()}</strong>
                      </div>
                    </div>
                  </div>
                )}

                {comparison.private && trainingMode === 'fl' && (
                  <div className="result-card private-card">
                    <h3>🤝 Federated ({getAggregatorLabel(comparison.private.aggregator || aggregator)})</h3>
                    <div className="model-info">{comparison.private.modelUsed}</div>
                    <div className="big-metric">
                      <div className="metric-label">Accuracy</div>
                      <div className="metric-value">{comparison.private.privateAccuracy?.toFixed(2) || comparison.private.baselineAccuracy.toFixed(2)}%</div>
                    </div>
                    {comparison.baseline && (
                      <div className="accuracy-loss">
                        Diff vs Baseline: {(comparison.baseline.baselineAccuracy - (comparison.private.privateAccuracy || comparison.private.baselineAccuracy)).toFixed(2)}%
                      </div>
                    )}
                    <div className="small-metrics">
                      <div className="small-metric">
                        <span>F1 Score:</span>
                        <strong>{comparison.private.f1Score !== undefined ? `${comparison.private.f1Score.toFixed(2)}%` : 'N/A'}</strong>
                      </div>
                      <div className="small-metric">
                        <span>Precision:</span>
                        <strong>{comparison.private.precision !== undefined ? `${comparison.private.precision.toFixed(2)}%` : 'N/A'}</strong>
                      </div>
                      <div className="small-metric">
                        <span>Recall:</span>
                        <strong>{comparison.private.recall !== undefined ? `${comparison.private.recall.toFixed(2)}%` : 'N/A'}</strong>
                      </div>
                      <div className="small-metric">
                        <span>Samples:</span>
                        <strong>{comparison.private.samplesEvaluated.toLocaleString()}</strong>
                      </div>
                    </div>
                  </div>
                )}

                {!config.dpEnabled && trainingMode === 'dp' && comparison.baseline && (
                  <div className="info-message">
                    <p>💡 Enable Differential Privacy to see the privacy-accuracy tradeoff</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>

        {/* Right Panel - Information */}
        <aside className="right-panel">
          <section className="info-section">
            <h3>About</h3>
            <p>
              This playground demonstrates the tradeoff between <strong>privacy</strong> and <strong>accuracy</strong> in machine learning.
            </p>
          </section>

          <section className="info-section">
            <h3>Federated Learning</h3>
            <p>
              Models train across distributed clients and aggregate updates without collecting raw data.
            </p>
            <ul>
              {aggregatorOptions.map((option) => (
                <li key={option.value}>
                  <strong>{option.label}:</strong> {option.description} <em>Best for {option.bestFor}</em>
                </li>
              ))}
            </ul>
          </section>

          <section className="info-section">
            <h3>Differential Privacy</h3>
            <p>
              Adds controlled noise during training to protect individual privacy.
            </p>
            <p>
              <strong>Epsilon (ε)</strong> controls the privacy level:
            </p>
            <ul>
              <li><strong>Lower ε (0.5-1.0):</strong> More private, less accurate</li>
              <li><strong>Higher ε (3.0-10.0):</strong> Less private, more accurate</li>
            </ul>
          </section>

          <section className="info-section">
            <h3>Datasets</h3>
            <p><strong>Diabetes:</strong> 21 features, binary classification</p>
            <p><strong>Adult Income:</strong> 14 features, income prediction</p>
          </section>

          <section className="info-section">
            <h3>Models</h3>
            <p><strong>Neural Network:</strong> 3 hidden layers [128, 64, 32]</p>
            <p><strong>Logistic Regression:</strong> Linear classifier</p>
          </section>
        </aside>
      </div>
      )}

      {activeTab === 'survey' && (
        <div className="survey-container">
          <div className="survey-header">
          </div>
          <iframe 
          src="https://docs.google.com/forms/d/e/1FAIpQLSdh5hnwsB8AmKSrbLzgdzj2zA3AnltJkCmCup-SfP5ehePC3A/viewform?embedded=true" 
          width="100%" 
          height="90%" 
          style={{ border: 'none', borderRadius: '8px' }}
          >Loading…</iframe>
        </div>
      )}

      {activeTab === 'dataset' && (
        <div className="dataset-container">
          <div className="dataset-content">
            <h2>📊 Dataset Explorer</h2>
            
            <div className="dataset-selector">
              <label>Select Dataset:</label>
              <div className="dataset-buttons">
                <button 
                  className={`dataset-btn ${selectedDataset === 'diabetes' ? 'active' : ''}`}
                  onClick={() => setSelectedDataset('diabetes')}
                >
                  🩺 Diabetes Dataset
                </button>
                <button 
                  className={`dataset-btn ${selectedDataset === 'adult' ? 'active' : ''}`}
                  onClick={() => setSelectedDataset('adult')}
                >
                  👥 Adult Income Dataset
                </button>
              </div>
            </div>

            {selectedDataset === 'diabetes' && (
              <div className="dataset-info">
                <h3>Diabetes Dataset</h3>
                <div className="info-grid">
                  <div className="info-card">
                    <h4>📌 Overview</h4>
                    <p><strong>Features:</strong> 21 numerical features</p>
                    <p><strong>Target:</strong> Binary classification (diabetes/no diabetes)</p>
                    <p><strong>Records:</strong> 768 samples (train: 614, test: 154)</p>
                    <p><strong>Preprocessing:</strong> StandardScaler normalization</p>
                  </div>
                  
                  <div className="info-card">
                    <h4>📊 Class Distribution</h4>
                    <p><strong>Positive (Diabetes):</strong> 268 samples (34.9%)</p>
                    <p><strong>Negative (No Diabetes):</strong> 500 samples (65.1%)</p>
                    <p>✅ Balanced dataset suitable for binary classification</p>
                  </div>

                  <div className="info-card">
                    <h4>🔍 Features</h4>
                    <p><strong>Pregnancies:</strong> Number of pregnancies</p>
                    <p><strong>Glucose:</strong> Plasma glucose concentration</p>
                    <p><strong>BloodPressure:</strong> Diastolic blood pressure (mm Hg)</p>
                    <p><strong>SkinThickness:</strong> Triceps skin fold thickness (mm)</p>
                    <p><strong>Insulin:</strong> 2-Hour serum insulin (mu U/ml)</p>
                    <p><strong>BMI:</strong> Body mass index (weight in kg/(height in m)²)</p>
                    <p><strong>DiabetesPedigreeFunction:</strong> Diabetes pedigree function</p>
                    <p><strong>Age:</strong> Age (years)</p>
                    <p><em>Plus 13 additional numerical features</em></p>
                  </div>

                  <div className="info-card">
                    <h4>✨ Data Quality</h4>
                    <p><strong>Missing Values:</strong> None</p>
                    <p><strong>Duplicates:</strong> None</p>
                    <p><strong>Data Type:</strong> All numerical features</p>
                    <p><strong>Train/Test Split:</strong> 80/20</p>
                  </div>

                  <div className="info-card research-results">
                    <h4>🔬 Research Results (5-Fold CV × 5 Runs)</h4>
                    <p><strong>Logistic Regression:</strong></p>
                    <p>Accuracy: 86.33% ± 0.08% (range: 86.08% - 86.46%)</p>
                    <p>F1-Score: 82.91% ± 0.23%</p>
                    <p><strong>Neural Network (FNN):</strong></p>
                    <p>Accuracy: 86.58% ± 0.07% (range: 86.44% - 86.68%)</p>
                    <p>F1-Score: 82.94% ± 0.53%</p>
                    <p className="note">✅ 25 evaluations per model</p>
                  </div>
                </div>
              </div>
            )}

            {selectedDataset === 'adult' && (
              <div className="dataset-info">
                <h3>Adult Income Dataset</h3>
                <div className="info-grid">
                  <div className="info-card">
                    <h4>📌 Overview</h4>
                    <p><strong>Features:</strong> 14 categorical/numerical features</p>
                    <p><strong>Target:</strong> Binary classification (income ≥$50K / &lt;$50K)</p>
                    <p><strong>Records:</strong> 30,162 samples (train: 24,129, test: 6,033)</p>
                    <p><strong>Preprocessing:</strong> Categorical encoding + StandardScaler</p>
                  </div>
                  
                  <div className="info-card">
                    <h4>📊 Class Distribution</h4>
                    <p><strong>Income ≥$50K:</strong> 7,841 samples (25.98%)</p>
                    <p><strong>Income &lt;$50K:</strong> 22,321 samples (74.02%)</p>
                    <p>⚠️ Imbalanced dataset - more samples in lower income bracket</p>
                  </div>

                  <div className="info-card">
                    <h4>🔍 Features</h4>
                    <p><strong>Age:</strong> Age of person (numerical)</p>
                    <p><strong>Workclass:</strong> Employment type (categorical)</p>
                    <p><strong>Education:</strong> Education level (categorical)</p>
                    <p><strong>Marital Status:</strong> Marital status (categorical)</p>
                    <p><strong>Occupation:</strong> Type of occupation (categorical)</p>
                    <p><strong>Relationship:</strong> Family relationship (categorical)</p>
                    <p><strong>Race:</strong> Race (categorical)</p>
                    <p><strong>Hours-per-week:</strong> Hours worked per week (numerical)</p>
                    <p><em>Plus 6 additional features including country, capital gains/loss</em></p>
                  </div>

                  <div className="info-card">
                    <h4>✨ Data Quality</h4>
                    <p><strong>Missing Values:</strong> Some encoded as '?'</p>
                    <p><strong>Categorical Features:</strong> One-hot encoded</p>
                    <p><strong>Data Type:</strong> Mixed numerical and categorical</p>
                    <p><strong>Train/Test Split:</strong> 80/20</p>
                  </div>

                  <div className="info-card research-results">
                    <h4>🔬 Research Results (5-Fold CV × 5 Runs)</h4>
                    <p><strong>Logistic Regression:</strong></p>
                    <p>Accuracy: 82.44% ± 0.27% (range: 81.93% - 82.92%)</p>
                    <p>F1-Score: 80.98% ± 0.31%</p>
                    <p><strong>Neural Network (FNN):</strong></p>
                    <p>Accuracy: 85.01% ± 0.32% (range: 84.24% - 85.67%)</p>
                    <p>F1-Score: 84.22% ± 0.36%</p>
                    <p className="note">✅ 25 evaluations per model</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'visualization' && (
        <div className="visualization-container">
          <div className="visualization-content">
            <h2>📈 Results Visualization</h2>
            
            {/* Research Results: Baseline Model Comparison image removed as requested */}

            <div className="viz-section">
              <h3>📊 Privacy Levels</h3>
              <div className="privacy-levels">
                <div className="privacy-card">
                  <h4>ε = 0.5</h4>
                  <div className="privacy-bar very-high"></div>
                  <p>🔐 <strong>Very High Privacy</strong></p>
                  <p>Smallest privacy loss</p>
                  <p className="note">↓ Lowest Accuracy</p>
                </div>
                <div className="privacy-card">
                  <h4>ε = 1.0</h4>
                  <div className="privacy-bar high"></div>
                  <p>🔐 <strong>High Privacy</strong></p>
                  <p>Strong privacy guarantee</p>
                </div>
                <div className="privacy-card">
                  <h4>ε = 3.0</h4>
                  <div className="privacy-bar medium"></div>
                  <p>🟡 <strong>Moderate Privacy</strong></p>
                  <p>Balanced privacy-utility</p>
                </div>
                <div className="privacy-card">
                  <h4>ε = 10.0</h4>
                  <div className="privacy-bar low"></div>
                  <p>⚠️ <strong>Low Privacy</strong></p>
                  <p>Weak privacy guarantee</p>
                  <p className="note">↑ Highest Accuracy</p>
                </div>
              </div>
            </div>

            <div className="viz-section">
              <h3>🤝 Federated Learning Aggregation Methods</h3>
              <div className="aggregator-info">
                <div className="aggregator-card">
                  <h4>FedAvg</h4>
                  <p><strong>Mechanism:</strong> Simple averaging of client models</p>
                  <p><strong>Best for:</strong> IID data, homogeneous clients</p>
                  <p><strong>Pros:</strong> Simple, stable</p>
                </div>
                <div className="aggregator-card">
                  <h4>FedProx</h4>
                  <p><strong>Mechanism:</strong> Weighted averaging with proximal term</p>
                  <p><strong>Best for:</strong> Non-IID data, heterogeneous systems</p>
                  <p><strong>Pros:</strong> Better convergence with data heterogeneity</p>
                </div>
                <div className="aggregator-card">
                  <h4>q-FedAvg</h4>
                  <p><strong>Mechanism:</strong> Reweights client contributions by performance</p>
                  <p><strong>Best for:</strong> Fairness-critical applications</p>
                  <p><strong>Pros:</strong> Prioritizes underperforming clients</p>
                </div>
                <div className="aggregator-card">
                  <h4>SCAFFOLD</h4>
                  <p><strong>Mechanism:</strong> Control variates for drift reduction</p>
                  <p><strong>Best for:</strong> Highly non-IID data</p>
                  <p><strong>Pros:</strong> Reduces client drift significantly</p>
                </div>
                <div className="aggregator-card">
                  <h4>FedAdam</h4>
                  <p><strong>Mechanism:</strong> Adaptive learning rates per parameter</p>
                  <p><strong>Best for:</strong> Heterogeneous optimization</p>
                  <p><strong>Pros:</strong> Adaptive, faster convergence</p>
                </div>
              </div>
            </div>

            <div className="viz-section">
              <h3>📚 How to Interpret Results</h3>
              <div className="interpretation-guide">
                <div className="guide-item">
                  <h4>🎯 Accuracy</h4>
                  <p>Percentage of correct predictions. Higher is better. Baseline shows maximum accuracy without privacy constraints.</p>
                </div>
                <div className="guide-item">
                  <h4>🔒 Accuracy Loss</h4>
                  <p>Difference between baseline and private model accuracy. Shows privacy-utility tradeoff: lower ε means higher loss.</p>
                </div>
                <div className="guide-item">
                  <h4>F1 Score</h4>
                  <p>Harmonic mean of precision and recall. Balances false positives and false negatives. Best for imbalanced datasets.</p>
                </div>
                <div className="guide-item">
                  <h4>Precision</h4>
                  <p>Accuracy of positive predictions. Percentage of predicted positives that are actually positive.</p>
                </div>
                <div className="guide-item">
                  <h4>Recall</h4>
                  <p>Coverage of actual positives. Percentage of actual positives correctly identified.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
