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
  sleep_score: '⭐',
  hrv: '💓',
  resting_hr: '❤️',
  body_battery: '🔋',
  stress: '😰',
};

const METRIC_LABELS: Record<string, string> = {
  sleep: 'Sleep',
  sleep_score: 'Sleep Score',
  hrv: 'HRV',
  resting_hr: 'Resting HR',
  body_battery: 'Body Battery',
  stress: 'Stress',
};

const METRIC_UNITS: Record<string, string> = {
  sleep: 'hrs',
  sleep_score: '/100',
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
      return `${hours}h${mins}m`;
    case 'sleep_score':
    case 'hrv':
    case 'resting_hr':
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

  const metricTypes = ['sleep', 'sleep_score', 'hrv', 'resting_hr', 'body_battery', 'stress'];

  // Group recent data by date for table view
  const dataByDate: Record<string, Record<string, GarminData>> = {};
  recentData.forEach((item) => {
    if (!dataByDate[item.metric_date]) {
      dataByDate[item.metric_date] = {};
    }
    dataByDate[item.metric_date][item.metric_type] = item;
  });

  // Get sorted dates (newest first)
  const dates = Object.keys(dataByDate).sort((a, b) => b.localeCompare(a));

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
                  <span className="text-xs text-gray-600">{METRIC_LABELS[type]}</span>
                </div>
                <div className="text-xl font-bold text-gray-800">
                  {data ? formatValue(type, data.value) : '--'}
                </div>
                {data && METRIC_UNITS[type] && (
                  <div className="text-xs text-gray-500">{METRIC_UNITS[type]}</div>
                )}
                {data && (
                  <div className="text-xs text-gray-400 mt-1">
                    {data.metric_date}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Recent History Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="font-semibold text-gray-700">Recent History</h2>
          </div>

          {dates.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No data yet. Click Sync to fetch from Garmin.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Date</th>
                    {metricTypes.map((type) => (
                      <th key={type} className="px-3 py-2 text-center text-xs font-medium text-gray-500">
                        <div className="flex flex-col items-center gap-1">
                          <span>{METRIC_ICONS[type]}</span>
                          <span className="hidden sm:inline">{METRIC_LABELS[type]}</span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {dates.map((date) => {
                    const dayData = dataByDate[date];
                    return (
                      <tr key={date} className="hover:bg-gray-50">
                        <td className="px-3 py-2 text-xs text-gray-600 whitespace-nowrap">
                          {date}
                        </td>
                        {metricTypes.map((type) => {
                          const item = dayData[type];
                          return (
                            <td key={type} className="px-3 py-2 text-center text-xs">
                              {item ? (
                                <span className="font-medium text-gray-800">
                                  {formatValue(type, item.value)}
                                </span>
                              ) : (
                                <span className="text-gray-300">--</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
