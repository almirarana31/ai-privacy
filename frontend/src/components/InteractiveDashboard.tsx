import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, Area, AreaChart, ComposedChart, ReferenceLine
} from 'recharts';

interface DPResult {
  dataset: string;
  model: string;
  epsilon: number;
  accuracy: number;
  std: number;
  baseline: number;
  accuracyLoss: number;
}

interface FLResult {
  dataset: string;
  model: string;
  aggregation: string;
  accuracy: number;
  std: number;
  baseline: number;
}

interface DashboardProps {
  dpData?: DPResult[];
  flData?: FLResult[];
  baselineData?: any;
}

const COLORS = {
  primary: '#8884d8',
  secondary: '#82ca9d',
  tertiary: '#ffc658',
  quaternary: '#ff8042',
  danger: '#ff4444',
  success: '#00C49F',
  warning: '#FFBB28',
};

const EPSILON_COLORS = ['#ff4444', '#ff8844', '#ffbb44', '#88cc88', '#4488ff'];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip" style={{
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        padding: '15px',
        border: '2px solid #8884d8',
        borderRadius: '8px',
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
      }}>
        <p style={{ fontWeight: 'bold', marginBottom: '8px' }}>{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} style={{ color: entry.color, margin: '4px 0' }}>
            {entry.name}: <strong>{entry.value?.toFixed(2)}%</strong>
            {entry.payload.std && ` (±${entry.payload.std.toFixed(2)}%)`}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const InteractiveDashboard: React.FC<DashboardProps> = ({ dpData = [], flData = [], baselineData }) => {
  const [selectedDataset, setSelectedDataset] = useState<string>('all');
  const [selectedModel, setSelectedModel] = useState<string>('all');
  const [selectedMetric, setSelectedMetric] = useState<'accuracy' | 'loss'>('accuracy');
  const [showErrorBars, setShowErrorBars] = useState(true);
  const [comparisonMode, setComparisonMode] = useState<'dp' | 'fl' | 'both'>('both');

  // Get unique datasets and models
  const datasets = ['all', ...new Set([...dpData.map(d => d.dataset), ...flData.map(d => d.dataset)])];
  const models = ['all', ...new Set([...dpData.map(d => d.model), ...flData.map(d => d.model)])];

  // Filter data based on selections
  const filteredDPData = dpData.filter(d => 
    (selectedDataset === 'all' || d.dataset === selectedDataset) &&
    (selectedModel === 'all' || d.model === selectedModel)
  );

  const filteredFLData = flData.filter(d =>
    (selectedDataset === 'all' || d.dataset === selectedDataset) &&
    (selectedModel === 'all' || d.model === selectedModel)
  );

  // Prepare privacy-accuracy tradeoff data (DP)
  const privacyTradeoffData = filteredDPData
    .sort((a, b) => a.epsilon - b.epsilon)
    .map(d => ({
      epsilon: d.epsilon,
      accuracy: d.accuracy,
      baseline: d.baseline,
      accuracyLoss: d.accuracyLoss,
      std: d.std,
      model: d.model,
      dataset: d.dataset
    }));

  // Prepare FL comparison data
  const flComparisonData = filteredFLData.map(d => ({
    name: `${d.aggregation}`,
    accuracy: d.accuracy,
    baseline: d.baseline,
    std: d.std,
    dataset: d.dataset,
    model: d.model
  }));

  // Prepare accuracy loss heatmap data
  const heatmapData = filteredDPData.map(d => ({
    epsilon: `ε=${d.epsilon}`,
    model: d.model,
    loss: d.accuracyLoss,
    accuracy: d.accuracy
  }));

  // Method comparison (DP vs FL vs Baseline)
  const methodComparisonData = () => {
    const comparison: any[] = [];
    
    // Baseline
    if (baselineData) {
      comparison.push({
        method: 'Baseline',
        accuracy: baselineData.accuracy || 85,
        privacy: 0,
        type: 'Baseline'
      });
    }

    // Best DP (highest epsilon)
    if (filteredDPData.length > 0) {
      const bestDP = filteredDPData.reduce((prev, curr) => 
        curr.epsilon > prev.epsilon ? curr : prev
      );
      comparison.push({
        method: `DP (ε=${bestDP.epsilon})`,
        accuracy: bestDP.accuracy,
        privacy: 100 / bestDP.epsilon,
        type: 'DP'
      });
    }

    // Best FL
    if (filteredFLData.length > 0) {
      const bestFL = filteredFLData.reduce((prev, curr) => 
        curr.accuracy > prev.accuracy ? curr : prev
      );
      comparison.push({
        method: `FL (${bestFL.aggregation})`,
        accuracy: bestFL.accuracy,
        privacy: 50, // Arbitrary privacy score for FL
        type: 'FL'
      });
    }

    return comparison;
  };

  return (
    <div className="interactive-dashboard" style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '30px', color: '#333' }}>
        🔒 Privacy-Preserving ML Dashboard
      </h1>

      {/* Control Panel */}
      <div className="controls" style={{
        display: 'flex',
        gap: '20px',
        marginBottom: '30px',
        padding: '20px',
        backgroundColor: '#f5f5f5',
        borderRadius: '10px',
        flexWrap: 'wrap'
      }}>
        <div>
          <label style={{ fontWeight: 'bold', marginRight: '10px' }}>Dataset:</label>
          <select 
            value={selectedDataset} 
            onChange={(e) => setSelectedDataset(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: '5px', border: '1px solid #ccc' }}
          >
            {datasets.map(d => <option key={d} value={d}>{d.toUpperCase()}</option>)}
          </select>
        </div>

        <div>
          <label style={{ fontWeight: 'bold', marginRight: '10px' }}>Model:</label>
          <select 
            value={selectedModel} 
            onChange={(e) => setSelectedModel(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: '5px', border: '1px solid #ccc' }}
          >
            {models.map(m => <option key={m} value={m}>{m.toUpperCase()}</option>)}
          </select>
        </div>

        <div>
          <label style={{ fontWeight: 'bold', marginRight: '10px' }}>View:</label>
          <select 
            value={comparisonMode} 
            onChange={(e) => setComparisonMode(e.target.value as any)}
            style={{ padding: '8px 12px', borderRadius: '5px', border: '1px solid #ccc' }}
          >
            <option value="both">All Methods</option>
            <option value="dp">Differential Privacy</option>
            <option value="fl">Federated Learning</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label>
            <input
              type="checkbox"
              checked={showErrorBars}
              onChange={(e) => setShowErrorBars(e.target.checked)}
              style={{ marginRight: '5px' }}
            />
            Show Error Bars
          </label>
        </div>
      </div>

      {/* Main Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(600px, 1fr))', gap: '30px' }}>
        
        {/* Privacy-Accuracy Tradeoff (DP) */}
        {(comparisonMode === 'both' || comparisonMode === 'dp') && privacyTradeoffData.length > 0 && (
          <div className="chart-container" style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '10px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ marginBottom: '20px', color: '#333' }}>
              📊 Privacy-Accuracy Tradeoff (Differential Privacy)
            </h3>
            <ResponsiveContainer width="100%" height={400}>
              <ComposedChart data={privacyTradeoffData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey="epsilon" 
                  label={{ value: 'Privacy Budget (ε)', position: 'insideBottom', offset: -5 }}
                  scale="log"
                  domain={['auto', 'auto']}
                  tickFormatter={(value) => value.toFixed(1)}
                />
                <YAxis 
                  label={{ value: 'Accuracy (%)', angle: -90, position: 'insideLeft' }}
                  domain={[60, 100]}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                
                {/* Baseline reference line */}
                {privacyTradeoffData[0]?.baseline && (
                  <ReferenceLine 
                    y={privacyTradeoffData[0].baseline} 
                    stroke="#ff4444" 
                    strokeDasharray="5 5"
                    label={{ value: 'Baseline', position: 'right' }}
                  />
                )}
                
                {/* DP accuracy line with area */}
                <Area
                  type="monotone"
                  dataKey="accuracy"
                  fill={COLORS.primary}
                  stroke={COLORS.primary}
                  fillOpacity={0.2}
                />
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  stroke={COLORS.primary}
                  strokeWidth={3}
                  dot={{ r: 6, fill: COLORS.primary }}
                  activeDot={{ r: 8 }}
                  name="DP Accuracy"
                />
              </ComposedChart>
            </ResponsiveContainer>
            <p style={{ marginTop: '10px', fontSize: '13px', color: '#666', textAlign: 'center' }}>
              Lower ε = stronger privacy, higher accuracy loss
            </p>
          </div>
        )}

        {/* FL Aggregation Comparison */}
        {(comparisonMode === 'both' || comparisonMode === 'fl') && flComparisonData.length > 0 && (
          <div className="chart-container" style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '10px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ marginBottom: '20px', color: '#333' }}>
              🌐 Federated Learning Aggregation Comparison
            </h3>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={flComparisonData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" />
                <YAxis 
                  label={{ value: 'Accuracy (%)', angle: -90, position: 'insideLeft' }}
                  domain={[60, 100]}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                
                {/* Baseline reference */}
                {flComparisonData[0]?.baseline && (
                  <ReferenceLine 
                    y={flComparisonData[0].baseline} 
                    stroke="#ff4444" 
                    strokeDasharray="5 5"
                    label="Baseline"
                  />
                )}
                
                <Bar dataKey="accuracy" name="FL Accuracy">
                  {flComparisonData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={Object.values(COLORS)[index % 7]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Accuracy Loss Heatmap */}
        {(comparisonMode === 'both' || comparisonMode === 'dp') && heatmapData.length > 0 && (
          <div className="chart-container" style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '10px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ marginBottom: '20px', color: '#333' }}>
              🔥 Accuracy Loss Heatmap (vs Baseline)
            </h3>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart 
                data={heatmapData}
                layout="vertical"
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis type="number" label={{ value: 'Accuracy Loss (%)', position: 'insideBottom', offset: -5 }} />
                <YAxis type="category" dataKey="epsilon" />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Bar dataKey="loss" name="Accuracy Loss">
                  {heatmapData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.loss > 10 ? '#ff4444' : entry.loss > 5 ? '#ffbb44' : '#88cc88'} 
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Method Comparison Scatter */}
        {comparisonMode === 'both' && (
          <div className="chart-container" style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '10px',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ marginBottom: '20px', color: '#333' }}>
              ⚖️ Privacy vs Accuracy Tradeoff (All Methods)
            </h3>
            <ResponsiveContainer width="100%" height={400}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  type="number" 
                  dataKey="privacy" 
                  name="Privacy Score"
                  label={{ value: 'Privacy Protection →', position: 'insideBottom', offset: -5 }}
                />
                <YAxis 
                  type="number" 
                  dataKey="accuracy" 
                  name="Accuracy"
                  label={{ value: 'Accuracy (%) →', angle: -90, position: 'insideLeft' }}
                  domain={[60, 100]}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                <Legend />
                <Scatter 
                  name="Methods" 
                  data={methodComparisonData()} 
                  fill={COLORS.primary}
                >
                  {methodComparisonData().map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={
                        entry.type === 'Baseline' ? '#888888' :
                        entry.type === 'DP' ? COLORS.primary :
                        COLORS.secondary
                      } 
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
            <p style={{ marginTop: '10px', fontSize: '13px', color: '#666', textAlign: 'center' }}>
              Higher privacy score = stronger privacy guarantees
            </p>
          </div>
        )}

        {/* Statistical Summary Cards */}
        <div className="stats-cards" style={{
          gridColumn: '1 / -1',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '20px',
          marginTop: '20px'
        }}>
          {/* DP Stats */}
          {filteredDPData.length > 0 && (
            <div style={{
              backgroundColor: '#e3f2fd',
              padding: '20px',
              borderRadius: '10px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}>
              <h4 style={{ marginBottom: '15px', color: '#1976d2' }}>🔒 Differential Privacy</h4>
              <p><strong>Configurations:</strong> {filteredDPData.length}</p>
              <p><strong>Best Accuracy:</strong> {Math.max(...filteredDPData.map(d => d.accuracy)).toFixed(2)}%</p>
              <p><strong>Min Privacy Loss:</strong> {Math.min(...filteredDPData.map(d => d.accuracyLoss)).toFixed(2)}%</p>
              <p><strong>ε Range:</strong> {Math.min(...filteredDPData.map(d => d.epsilon))} - {Math.max(...filteredDPData.map(d => d.epsilon))}</p>
            </div>
          )}

          {/* FL Stats */}
          {filteredFLData.length > 0 && (
            <div style={{
              backgroundColor: '#e8f5e9',
              padding: '20px',
              borderRadius: '10px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}>
              <h4 style={{ marginBottom: '15px', color: '#388e3c' }}>🌐 Federated Learning</h4>
              <p><strong>Aggregations:</strong> {new Set(filteredFLData.map(d => d.aggregation)).size}</p>
              <p><strong>Best Accuracy:</strong> {Math.max(...filteredFLData.map(d => d.accuracy)).toFixed(2)}%</p>
              <p><strong>Best Method:</strong> {
                filteredFLData.reduce((prev, curr) => curr.accuracy > prev.accuracy ? curr : prev).aggregation
              }</p>
            </div>
          )}

          {/* Baseline Stats */}
          {baselineData && (
            <div style={{
              backgroundColor: '#fff3e0',
              padding: '20px',
              borderRadius: '10px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
            }}>
              <h4 style={{ marginBottom: '15px', color: '#f57c00' }}>📊 Baseline</h4>
              <p><strong>Accuracy:</strong> {baselineData.accuracy?.toFixed(2) || 'N/A'}%</p>
              <p><strong>Privacy:</strong> None</p>
              <p><strong>Status:</strong> Maximum Utility</p>
            </div>
          )}
        </div>
      </div>

      {/* Data Table */}
      {(filteredDPData.length > 0 || filteredFLData.length > 0) && (
        <div style={{
          marginTop: '40px',
          backgroundColor: 'white',
          padding: '20px',
          borderRadius: '10px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          overflowX: 'auto'
        }}>
          <h3 style={{ marginBottom: '20px' }}>📋 Detailed Results</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ backgroundColor: '#f5f5f5' }}>
                <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Dataset</th>
                <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Model</th>
                <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Method</th>
                <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #ddd' }}>Accuracy</th>
                <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #ddd' }}>Std Dev</th>
                <th style={{ padding: '12px', textAlign: 'right', borderBottom: '2px solid #ddd' }}>vs Baseline</th>
              </tr>
            </thead>
            <tbody>
              {filteredDPData.map((d, i) => (
                <tr key={`dp-${i}`} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '12px' }}>{d.dataset}</td>
                  <td style={{ padding: '12px' }}>{d.model}</td>
                  <td style={{ padding: '12px' }}>DP (ε={d.epsilon})</td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>{d.accuracy.toFixed(2)}%</td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>±{d.std.toFixed(2)}%</td>
                  <td style={{ 
                    padding: '12px', 
                    textAlign: 'right',
                    color: d.accuracyLoss > 5 ? '#ff4444' : '#88cc88'
                  }}>
                    -{d.accuracyLoss.toFixed(2)}%
                  </td>
                </tr>
              ))}
              {filteredFLData.map((d, i) => (
                <tr key={`fl-${i}`} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '12px' }}>{d.dataset}</td>
                  <td style={{ padding: '12px' }}>{d.model}</td>
                  <td style={{ padding: '12px' }}>FL ({d.aggregation})</td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>{d.accuracy.toFixed(2)}%</td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>±{d.std.toFixed(2)}%</td>
                  <td style={{ 
                    padding: '12px', 
                    textAlign: 'right',
                    color: (d.baseline - d.accuracy) > 2 ? '#ff4444' : '#88cc88'
                  }}>
                    -{(d.baseline - d.accuracy).toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default InteractiveDashboard;
