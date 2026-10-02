import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ConnectionTest: React.FC = () => {
  const [backendStatus, setBackendStatus] = useState<string>('Checking...');
  const [healthData, setHealthData] = useState<any>(null);

  useEffect(() => {
    const testConnection = async () => {
      try {
        const response = await axios.get('/health');
        setBackendStatus('✅ Connected');
        setHealthData(response.data);
      } catch (error) {
        setBackendStatus('❌ Connection Failed');
        console.error('Backend connection error:', error);
      }
    };

    testConnection();
  }, []);

  return (
    <div className="fixed top-4 right-4 bg-gray-800 text-white p-4 rounded-lg shadow-lg z-50">
      <h3 className="text-sm font-bold mb-2">Backend Status</h3>
      <p className="text-xs">{backendStatus}</p>
      {healthData && (
        <div className="text-xs mt-2">
          <p>Server: {healthData.message}</p>
          <p>Environment: {healthData.environment}</p>
        </div>
      )}
    </div>
  );
};

export default ConnectionTest;
