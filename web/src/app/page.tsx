'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

export default function Home() {
  const [status, setStatus] = useState<'loading' | 'connected' | 'error'>('loading');
  const [apiUrl, setApiUrl] = useState<string>('');

  useEffect(() => {
    setApiUrl(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001');

    api.healthCheck()
      .then(() => setStatus('connected'))
      .catch(() => setStatus('error'));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Habit Bot</h1>
        <p className="text-gray-600 mb-6">Personal Health Tracking</p>

        {/* Connection Status */}
        <div className="mb-6">
          <div className="flex items-center justify-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                status === 'connected'
                  ? 'bg-green-500'
                  : status === 'error'
                  ? 'bg-red-500'
                  : 'bg-yellow-500 animate-pulse'
              }`}
            />
            <span className="text-sm text-gray-600">
              {status === 'connected'
                ? 'Connected to backend'
                : status === 'error'
                ? 'Backend unavailable'
                : 'Connecting...'}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">{apiUrl}</p>
        </div>

        {/* Info */}
        <div className="bg-blue-50 rounded-lg p-4 text-left">
          <h2 className="font-semibold text-blue-800 mb-2">How it works</h2>
          <ol className="text-sm text-blue-700 space-y-1 list-decimal list-inside">
            <li>Subscribe to notifications</li>
            <li>Receive check-in reminders</li>
            <li>Tap the link to answer questions</li>
            <li>Your responses are processed by AI</li>
          </ol>
        </div>

        {/* PWA Install hint */}
        <div className="mt-6 text-sm text-gray-500">
          <p>Add to home screen for the best experience</p>
        </div>
      </div>

      {/* Version */}
      <p className="text-gray-400 text-sm mt-4">v0.1.0</p>
    </div>
  );
}
