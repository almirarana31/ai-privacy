import React from 'react';
import type { ModelPerformance } from '../types.ts';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface Props {
  performance: ModelPerformance | null;
}

const Visualization: React.FC<Props> = ({ performance }) => {
  if (!performance) {
    return <div className="visualization"><h2>Results</h2><p>Run the model to see the results.</p></div>;
  }

  const data = [
    { name: 'Accuracy', value: performance.accuracy },
    { name: 'Precision', value: performance.precision },
    { name: 'Recall', value: performance.recall },
  ];

  const lossData = [
    { name: 'Privacy Loss', value: performance.privacyLoss },
    { name: 'Error Loss', value: performance.errorLoss },
  ];

  return (
    <div className="visualization">
      <h2>Results</h2>
      <div className="charts">
        <div className="chart">
          <h3>Performance Metrics</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="chart">
          <h3>Loss Metrics</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={lossData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="tables">
        <h3>Performance Details</h3>
        <table>
          <thead>
            <tr>
              <th>Metric</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Accuracy</td>
              <td>{performance.accuracy.toFixed(4)}</td>
            </tr>
            <tr>
              <td>Precision</td>
              <td>{performance.precision.toFixed(4)}</td>
            </tr>
            <tr>
              <td>Recall</td>
              <td>{performance.recall.toFixed(4)}</td>
            </tr>
            <tr>
              <td>Privacy Loss</td>
              <td>{performance.privacyLoss.toFixed(4)}</td>
            </tr>
            <tr>
              <td>Error Loss</td>
              <td>{performance.errorLoss.toFixed(4)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Visualization;
