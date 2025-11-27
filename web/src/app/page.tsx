'use client';

import { useEffect, useState } from 'react';
import { api, Response as ApiResponse, QuickLogResponse, Reminder, Summaries } from '@/lib/api';

const CATEGORY_COLORS: Record<string, string> = {
  sleep: 'bg-indigo-100 text-indigo-800',
  nutrition: 'bg-green-100 text-green-800',
  physical_activity: 'bg-orange-100 text-orange-800',
  substances: 'bg-purple-100 text-purple-800',
  stress_anxiety: 'bg-red-100 text-red-800',
  mood: 'bg-yellow-100 text-yellow-800',
  social: 'bg-pink-100 text-pink-800',
  productivity: 'bg-blue-100 text-blue-800',
  default: 'bg-gray-100 text-gray-800',
};

function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.default;
}

function formatTimestamp(timestamp: string): string {
  // API returns UTC timestamps without 'Z' suffix, so append it
  const utcTimestamp = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
  const date = new Date(utcTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function formatUpcomingTime(timestamp: string): string {
  const utcTimestamp = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
  const date = new Date(utcTimestamp);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  if (diffMins < 1) return 'now';
  if (diffMins < 60) return `in ${diffMins}m`;
  if (diffHours < 24) return `in ${diffHours}h ${diffMins % 60}m`;

  // Show day of week and time for reminders more than 24h away
  return date.toLocaleDateString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' });
}

export default function Home() {
  const [status, setStatus] = useState<'loading' | 'connected' | 'error'>('loading');
  const [responses, setResponses] = useState<ApiResponse[]>([]);
  const [quickLogText, setQuickLogText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [logResult, setLogResult] = useState<QuickLogResponse | null>(null);
  const [showBackdate, setShowBackdate] = useState(false);
  const [backdateValue, setBackdateValue] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [reprocessingId, setReprocessingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [upcomingReminders, setUpcomingReminders] = useState<Reminder[]>([]);
  const [summaries, setSummaries] = useState<Summaries | null>(null);

  const userId = 1; // Default user for now

  const loadResponses = async () => {
    try {
      const data = await api.getResponses({ user_id: userId, limit: 20 });
      setResponses(data);
    } catch (err) {
      console.error('Failed to load responses:', err);
    }
  };

  const loadUpcomingReminders = async () => {
    try {
      const data = await api.getUpcomingReminders(userId, 5);
      setUpcomingReminders(data);
    } catch (err) {
      console.error('Failed to load upcoming reminders:', err);
    }
  };

  const loadSummaries = async () => {
    try {
      const data = await api.getSummaries(userId);
      setSummaries(data);
    } catch (err) {
      console.error('Failed to load summaries:', err);
    }
  };

  useEffect(() => {
    api.healthCheck()
      .then(() => {
        setStatus('connected');
        loadResponses();
        loadUpcomingReminders();
        loadSummaries();
      })
      .catch(() => setStatus('error'));
  }, []);

  // Auto-refresh when there are pending/processing entries
  useEffect(() => {
    const hasPending = responses.some(
      (r) => r.processing_status === 'pending' || r.processing_status === 'processing'
    );
    if (!hasPending) return;

    const interval = setInterval(() => {
      loadResponses();
    }, 3000); // Refresh every 3 seconds

    return () => clearInterval(interval);
  }, [responses]);

  const handleQuickLog = async () => {
    if (!quickLogText.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setLogResult(null);

    try {
      // Convert local datetime to ISO string if backdating
      const timestamp = backdateValue ? new Date(backdateValue).toISOString() : undefined;
      const result = await api.quickLog(userId, quickLogText, timestamp);
      setLogResult(result);
      setQuickLogText('');
      setBackdateValue('');
      setShowBackdate(false);
      loadResponses();
      loadSummaries();
    } catch (err) {
      console.error('Quick log failed:', err);
      alert('Failed to submit. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReprocess = async (responseId: number) => {
    setReprocessingId(responseId);
    try {
      await api.reprocessResponse(responseId);
      loadResponses();
    } catch (err) {
      console.error('Reprocess failed:', err);
    } finally {
      setReprocessingId(null);
    }
  };

  const handleDelete = async (responseId: number) => {
    if (!confirm('Delete this entry?')) return;

    setDeletingId(responseId);
    try {
      await api.deleteResponse(responseId);
      setExpandedId(null);
      loadResponses();
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete entry.');
    } finally {
      setDeletingId(null);
    }
  };

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Connecting...</div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="w-3 h-3 rounded-full bg-red-500 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-gray-800 mb-2">Backend Unavailable</h1>
          <p className="text-gray-600">Unable to connect to the API server.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800">Habit Bot</h1>
          <p className="text-gray-500 text-sm">Personal Health Tracking</p>
        </div>

        {/* Quick Log */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold text-gray-700 mb-3">Quick Log</h2>
          <textarea
            value={quickLogText}
            onChange={(e) => setQuickLogText(e.target.value)}
            placeholder="What's happening? (e.g., 'took vitamins', 'feeling stressed', 'went for a run')"
            className="w-full border rounded-lg p-3 text-sm text-gray-900 resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={3}
            disabled={isSubmitting}
          />
          {/* Backdate toggle and input */}
          <div className="flex items-center gap-2 mt-2">
            <button
              type="button"
              onClick={() => setShowBackdate(!showBackdate)}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              {showBackdate ? '− Hide time' : '+ Set time'}
            </button>
            {showBackdate && (
              <input
                type="datetime-local"
                value={backdateValue}
                onChange={(e) => setBackdateValue(e.target.value)}
                className="text-xs border rounded px-2 py-1 text-gray-600"
                disabled={isSubmitting}
              />
            )}
            {backdateValue && (
              <button
                type="button"
                onClick={() => { setBackdateValue(''); setShowBackdate(false); }}
                className="text-xs text-red-500 hover:text-red-700"
              >
                Clear
              </button>
            )}
          </div>

          <div className="flex justify-between items-center mt-2">
            <span className="text-xs text-gray-400">
              {backdateValue ? `Logging for: ${new Date(backdateValue).toLocaleString()}` : 'Auto-categorized by AI'}
            </span>
            <button
              onClick={handleQuickLog}
              disabled={!quickLogText.trim() || isSubmitting}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
            >
              {isSubmitting ? 'Processing...' : 'Log Entry'}
            </button>
          </div>

          {/* Quick Log Result */}
          {logResult && (
            <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200">
              <div className="flex items-center gap-2 mb-1">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(logResult.category)}`}>
                  {logResult.category}
                </span>
                <span className="text-green-600 text-sm">Logged successfully</span>
              </div>
              <p className="text-sm text-gray-600">{logResult.summary}</p>
            </div>
          )}
        </div>

        {/* Upcoming Reminders */}
        {upcomingReminders.length > 0 && (
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h2 className="font-semibold text-gray-700">Upcoming Check-ins</h2>
            </div>
            <div className="divide-y">
              {upcomingReminders.map((reminder) => (
                <div key={reminder.id} className="p-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-blue-400" />
                    <div>
                      <div className="flex items-center gap-2">
                        {reminder.categories?.map((cat) => (
                          <span key={cat} className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(cat)}`}>
                            {cat.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {Object.values(reminder.questions)[0]}
                      </p>
                    </div>
                  </div>
                  <span className="text-sm text-gray-500 whitespace-nowrap">
                    {formatUpcomingTime(reminder.scheduled_time)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Activity Summaries */}
        {summaries && (
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
              <h2 className="font-semibold text-gray-700">Activity Summaries</h2>
            </div>
            <div className="divide-y">
              {/* Today */}
              {summaries.today.entry_count > 0 && (
                <div className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-700">Today</h3>
                    <span className="text-xs text-gray-500">{summaries.today.entry_count} entries</span>
                  </div>
                  <p className="text-sm text-gray-600 leading-relaxed">{summaries.today.summary}</p>
                  {summaries.today.categories.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {summaries.today.categories.map((cat) => (
                        <span key={cat} className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(cat)}`}>
                          {cat.replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Yesterday */}
              {summaries.yesterday.entry_count > 0 && (
                <div className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-gray-700">Yesterday</h3>
                    <span className="text-xs text-gray-500">{summaries.yesterday.entry_count} entries</span>
                  </div>
                  <p className="text-sm text-gray-600 leading-relaxed">{summaries.yesterday.summary}</p>
                  {summaries.yesterday.categories.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {summaries.yesterday.categories.map((cat) => (
                        <span key={cat} className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(cat)}`}>
                          {cat.replace('_', ' ')}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Past Week */}
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-700">Past 7 Days</h3>
                  <span className="text-xs text-gray-500">{summaries.week.entry_count} entries</span>
                </div>
                <p className="text-sm text-gray-600 leading-relaxed">{summaries.week.summary}</p>
                {summaries.week.categories.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {summaries.week.categories.map((cat) => (
                      <span key={cat} className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(cat)}`}>
                        {cat.replace('_', ' ')}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Recent Entries */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="font-semibold text-gray-700">Recent Entries</h2>
          </div>

          {responses.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No entries yet. Use Quick Log above to start tracking.
            </div>
          ) : (
            <div className="divide-y">
              {responses.map((response) => (
                <div key={response.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(response.category)}`}>
                          {response.category}
                        </span>
                        <span className="text-xs text-gray-400">
                          {formatTimestamp(response.timestamp)}
                        </span>
                        {response.processing_status === 'pending' && (
                          <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                            pending
                          </span>
                        )}
                        {response.processing_status === 'processing' && (
                          <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 animate-pulse">
                            processing
                          </span>
                        )}
                        {response.processing_status === 'failed' && (
                          <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                            failed
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-700">{response.response_text}</p>
                    </div>
                    <button
                      onClick={() => setExpandedId(expandedId === response.id ? null : response.id)}
                      className="text-gray-400 hover:text-gray-600 ml-2"
                    >
                      {expandedId === response.id ? '−' : '+'}
                    </button>
                  </div>

                  {/* Expanded Details */}
                  {expandedId === response.id && (
                    <div className="mt-3 pt-3 border-t">
                      <div className="text-xs text-gray-500 mb-2">
                        Question: {response.question_text}
                      </div>

                      {response.response_structured ? (
                        <div className="bg-gray-50 rounded p-3">
                          <div className="text-sm font-medium text-gray-700 mb-2">
                            Analysis
                          </div>
                          <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-x-auto">
                            {JSON.stringify(response.response_structured, null, 2)}
                          </pre>
                        </div>
                      ) : (
                        <div className="bg-yellow-50 rounded p-3 text-sm text-yellow-700">
                          No analysis available
                        </div>
                      )}

                      <div className="flex items-center gap-4 mt-3">
                        {response.processing_status === 'failed' && (
                          <button
                            onClick={() => handleReprocess(response.id)}
                            disabled={reprocessingId === response.id}
                            className="text-sm text-blue-600 hover:text-blue-800"
                          >
                            {reprocessingId === response.id ? 'Reprocessing...' : 'Retry Analysis'}
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(response.id)}
                          disabled={deletingId === response.id}
                          className="text-sm text-red-600 hover:text-red-800"
                        >
                          {deletingId === response.id ? 'Deleting...' : 'Delete'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center text-xs text-gray-400">
          v0.1.0
        </div>
      </div>
    </div>
  );
}
