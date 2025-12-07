import React from 'react';
import type { ModelParameters } from '../types.ts';

interface Props {
  parameters: ModelParameters;
  onParametersChange: (newParameters: ModelParameters) => void;
  disabled: boolean;
}

const ControlPanel: React.FC<Props> = ({ parameters, onParametersChange, disabled }) => {
  const handleEpochsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onParametersChange({ ...parameters, epochs: parseInt(e.target.value, 10) });
  };

  const handlePrivacyBudgetChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onParametersChange({ ...parameters, privacyBudget: parseFloat(e.target.value) });
  };

  return (
    <div className="control-panel">
      <h2>Model Parameters</h2>
      <div className="form-group">
        <label>Epochs: {parameters.epochs}</label>
        <input
          type="range"
          min="1"
          max="100"
          value={parameters.epochs}
          onChange={handleEpochsChange}
          disabled={disabled}
        />
      </div>
      <div className="form-group">
        <label>Privacy Budget (Epsilon): {parameters.privacyBudget.toFixed(1)}</label>
        <input
          type="range"
          min="0.1"
          max="10"
          step="0.1"
          value={parameters.privacyBudget}
          onChange={handlePrivacyBudgetChange}
          disabled={disabled}
        />
      </div>
    </div>
  );
};

export default ControlPanel;
