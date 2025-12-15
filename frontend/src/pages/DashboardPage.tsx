import React, { useState, useEffect } from 'react';
import InteractiveDashboard from '../components/InteractiveDashboard';
import visualizationService, { type VisualizationData } from '../services/visualizationService';

const DashboardPage: React.FC = () => {
  const [data, setData] = useState<VisualizationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        const vizData = await visualizationService.getAllData();
        setData(vizData);
      } catch (err) {
        console.error('Failed to load visualization data:', err);
        setError('Failed to load data. Make sure the backend is running and has results files.');
      } finally {
        setLoading(false);
      }
    };

    loadData();

    // Refresh data every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        fontSize: '24px'
      }}>
        <div>
          <div className="spinner" style={{
            border: '4px solid #f3f3f3',
            borderTop: '4px solid #8884d8',
            borderRadius: '50%',
            width: '60px',
            height: '60px',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 20px'
          }}></div>
          <p>Loading experimental results...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        padding: '40px',
        maxWidth: '800px',
        margin: '0 auto',
        textAlign: 'center'
      }}>
        <h2 style={{ color: '#ff4444', marginBottom: '20px' }}>⚠️ Error Loading Data</h2>
        <p style={{ marginBottom: '20px' }}>{error}</p>
        <p style={{ color: '#666' }}>
          Make sure you have:<br />
          1. Run experiments and generated JSON results<br />
          2. Backend server is running on port 8000<br />
          3. Result files are in the correct directories
        </p>
        <button
          onClick={() => window.location.reload()}
          style={{
            marginTop: '20px',
            padding: '10px 20px',
            fontSize: '16px',
            backgroundColor: '#8884d8',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer'
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!data || (data.dp.length === 0 && data.fl.length === 0)) {
    return (
      <div style={{
        padding: '40px',
        maxWidth: '800px',
        margin: '0 auto',
        textAlign: 'center'
      }}>
        <h2 style={{ marginBottom: '20px' }}>📊 No Results Found</h2>
        <p style={{ color: '#666', marginBottom: '20px' }}>
          No experimental results were found. Please run experiments first using the Jupyter notebooks:
        </p>
        <ul style={{ textAlign: 'left', maxWidth: '500px', margin: '0 auto' }}>
          <li><code>dp_continue_crossvalidation.ipynb</code> - Differential Privacy experiments</li>
          <li><code>dp_adult_complete.ipynb</code> - DP Adult dataset</li>
          <li><code>fl_diabetes_fnn_continue.ipynb</code> - Federated Learning experiments</li>
        </ul>
      </div>
    );
  }

  return (
    <div>
      <InteractiveDashboard
        dpData={data.dp}
        flData={data.fl}
        baselineData={data.baseline[0]}
      />
    </div>
  );
};

export default DashboardPage;
