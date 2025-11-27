'use client';

import { useEffect, useState } from 'react';

interface GarminData {
  id: number;
  metric_type: string;
  metric_date: string;
  value: number | null;
  details: Record<string, unknown> | null;
  fetched_at: string;
}

const METRIC_ICONS: Record<string, string> = {
  sleep: '😴',
  hrv: '💓',
  resting_hr: '❤️',
  body_battery: '🔋',
  stress: '😰',
};

const METRIC_LABELS: Record<string, string> = {
  sleep: 'Sleep',
  hrv: 'HRV',
  resting_hr: 'Resting HR',
  body_battery: 'Body Battery',
  stress: 'Stress',
};

const METRIC_UNITS: Record<string, string> = {
  sleep: 'hrs',
  hrv: 'ms',
  resting_hr: 'bpm',
  body_battery: '%',
  stress: '',
};

function formatValue(type: string, value: number | null): string {
  if (value === null) return '--';

  switch (type) {
    case 'sleep':
      // Value is already in hours (e.g., 7.22 hours)
      const hours = Math.floor(value);
      const mins = Math.round((value - hours) * 60);
      return `${hours}h ${mins}m`;
    case 'hrv':
    case 'resting_hr':
      return Math.round(value).toString();
    case 'body_battery':
    case 'stress':
      return Math.round(value).toString();
    default:
      return value.toString();
  }
}

export default function GarminPage() {
  const [latestMetrics, setLatestMetrics] = useState<Record<string, GarminData | null>>({});
  const [recentData, setRecentData] = useState<GarminData[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  const userId = 1;
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

  const loadData = async () => {
    try {
      // Load latest metrics
      const latestRes = await fetch(`${API_URL}/api/v1/garmin/latest?user_id=${userId}`);
      if (latestRes.ok) {
        const latest = await latestRes.json();
        setLatestMetrics(latest);
      }

      // Load recent data (last 7 days)
      const dataRes = await fetch(`${API_URL}/api/v1/garmin/data?user_id=${userId}&limit=50`);
      if (dataRes.ok) {
        const data = await dataRes.json();
        setRecentData(data);
      }
    } catch (err) {
      console.error('Failed to load Garmin data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSync = async (daysBack: number = 7) => {
    setSyncing(true);
    setSyncResult(null);

    try {
      const response = await fetch(`${API_URL}/api/v1/garmin/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, days_back: daysBack }),
      });

      const result = await response.json();
      if (response.ok) {
        setSyncResult(`Synced ${result.synced_count} records`);
        loadData();
      } else {
        setSyncResult(`Error: ${result.detail || 'Sync failed'}`);
      }
    } catch (err) {
      setSyncResult('Error: Failed to connect');
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  const metricTypes = ['sleep', 'hrv', 'resting_hr', 'body_battery', 'stress'];

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Garmin</h1>
            <p className="text-gray-500 text-sm">Health metrics from your watch</p>
          </div>
          <button
            onClick={() => handleSync(7)}
            disabled={syncing}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {syncing ? 'Syncing...' : 'Sync'}
          </button>
        </div>

        {/* Sync Result */}
        {syncResult && (
          <div className={`p-3 rounded-lg text-sm ${
            syncResult.startsWith('Error') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'
          }`}>
            {syncResult}
          </div>
        )}

        {/* Latest Metrics Grid */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {metricTypes.map((type) => {
            const data = latestMetrics[type];
            return (
              <div key={type} className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xl">{METRIC_ICONS[type]}</span>
                  <span className="text-sm text-gray-600">{METRIC_LABELS[type]}</span>
                </div>
                <div className="text-2xl font-bold text-gray-800">
                  {data ? formatValue(type, data.value) : '--'}
                </div>
                {data && METRIC_UNITS[type] && (
                  <div className="text-xs text-gray-500">{METRIC_UNITS[type]}</div>
                )}
                {data && (
                  <div className="text-xs text-gray-400 mt-1">
                    {new Date(data.metric_date).toLocaleDateString()}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Recent History */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="font-semibold text-gray-700">Recent History</h2>
          </div>

          {recentData.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No data yet. Click Sync to fetch from Garmin.
            </div>
          ) : (
            <div className="divide-y max-h-96 overflow-y-auto">
              {recentData.map((item) => (
                <div key={item.id} className="p-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{METRIC_ICONS[item.metric_type] || '📊'}</span>
                    <div>
                      <div className="text-sm font-medium text-gray-700">
                        {METRIC_LABELS[item.metric_type] || item.metric_type}
                      </div>
                      <div className="text-xs text-gray-500">
                        {new Date(item.metric_date).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-gray-800">
                      {formatValue(item.metric_type, item.value)}
                    </div>
                    {METRIC_UNITS[item.metric_type] && (
                      <div className="text-xs text-gray-500">{METRIC_UNITS[item.metric_type]}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
