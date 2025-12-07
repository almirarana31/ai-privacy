import React, { useState } from 'react';
import Papa from 'papaparse';
import type { TrainingData } from '../types.ts';

interface Props {
  onDataChange: (data: TrainingData) => void;
  disabled: boolean;
}

const DataInput: React.FC<Props> = ({ onDataChange, disabled }) => {
  const [fileName, setFileName] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      Papa.parse(file, {
        complete: (results) => {
          onDataChange({ fileName: file.name, data: results.data as (string | number)[][] });
        },
        header: false,
      });
    }
  };

  const handleSampleDataSelect = (sampleFileName: string) => {
    setFileName(sampleFileName);
    fetch(`/data/${sampleFileName}`)
      .then((response) => response.text())
      .then((csvText) => {
        Papa.parse(csvText, {
          complete: (results) => {
            onDataChange({ fileName: sampleFileName, data: results.data as (string | number)[][] });
          },
          header: false,
        });
      });
  };

  return (
    <div className="data-input">
      <h2>Training Data</h2>
      <div className="form-group">
        <label>Upload CSV:</label>
        <input type="file" accept=".csv" onChange={handleFileChange} disabled={disabled} />
      </div>
      <div className="form-group">
        <label>Or select sample data:</label>
        <button onClick={() => handleSampleDataSelect('cdc_diabetes.csv')} disabled={disabled}>
          CDC Diabetes
        </button>
        <button onClick={() => handleSampleDataSelect('us_income.csv')} disabled={disabled}>
          US Income
        </button>
      </div>
      {fileName && <p>Selected: {fileName}</p>}
    </div>
  );
};

export default DataInput;
