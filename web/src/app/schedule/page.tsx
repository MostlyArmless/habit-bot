'use client';

import { useEffect, useState } from 'react';
import { api, Prompt } from '@/lib/api';

const CATEGORY_COLORS: Record<string, string> = {
  sleep: 'bg-indigo-100 text-indigo-800',
  nutrition: 'bg-green-100 text-green-800',
  physical_activity: 'bg-orange-100 text-orange-800',
  substances: 'bg-purple-100 text-purple-800',
  stress_anxiety: 'bg-red-100 text-red-800',
  mental_state: 'bg-yellow-100 text-yellow-800',
  default: 'bg-gray-100 text-gray-800',
};

function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.default;
}

function formatScheduledTime(timestamp: string): string {
  const utcTimestamp = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
  const date = new Date(utcTimestamp);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  const timeStr = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });

  if (diffMins < 0) return `${timeStr} (past)`;
  if (diffMins < 60) return `${timeStr} (in ${diffMins}m)`;
  if (diffHours < 24) return `${timeStr} (in ${diffHours}h)`;

  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });
}

const CATEGORIES = [
  'mental_state',
  'sleep',
  'nutrition',
  'physical_activity',
  'stress_anxiety',
  'substances',
  'physical_symptoms',
  'social_interaction',
  'work_productivity',
];

export default function SchedulePage() {
  const [upcomingPrompts, setUpcomingPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newPrompt, setNewPrompt] = useState({
    scheduledTime: '',
    category: 'mental_state',
    question: '',
  });

  const userId = 1;

  const loadPrompts = async () => {
    try {
      const data = await api.getUpcomingPrompts(userId, 20);
      setUpcomingPrompts(data);
    } catch (err) {
      console.error('Failed to load prompts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPrompts();
  }, []);

  const handleCreatePrompt = async () => {
    if (!newPrompt.scheduledTime || !newPrompt.question) return;

    setCreating(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/v1/prompts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          scheduled_time: new Date(newPrompt.scheduledTime).toISOString(),
          questions: { q1: newPrompt.question },
          categories: [newPrompt.category],
        }),
      });

      if (response.ok) {
        setNewPrompt({ scheduledTime: '', category: 'mental_state', question: '' });
        setShowCreateForm(false);
        loadPrompts();
      }
    } catch (err) {
      console.error('Failed to create prompt:', err);
    } finally {
      setCreating(false);
    }
  };

  // Set default time to 1 hour from now
  const getDefaultTime = () => {
    const date = new Date();
    date.setHours(date.getHours() + 1);
    date.setMinutes(0);
    return date.toISOString().slice(0, 16);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Schedule</h1>
            <p className="text-gray-500 text-sm">Manage your check-in prompts</p>
          </div>
          <button
            onClick={() => {
              setShowCreateForm(!showCreateForm);
              if (!newPrompt.scheduledTime) {
                setNewPrompt(prev => ({ ...prev, scheduledTime: getDefaultTime() }));
              }
            }}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            {showCreateForm ? 'Cancel' : '+ New'}
          </button>
        </div>

        {/* Create Form */}
        {showCreateForm && (
          <div className="bg-white rounded-lg shadow p-4 space-y-4">
            <h2 className="font-semibold text-gray-700">Create New Prompt</h2>

            <div>
              <label className="block text-sm text-gray-600 mb-1">When</label>
              <input
                type="datetime-local"
                value={newPrompt.scheduledTime}
                onChange={(e) => setNewPrompt(prev => ({ ...prev, scheduledTime: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Category</label>
              <select
                value={newPrompt.category}
                onChange={(e) => setNewPrompt(prev => ({ ...prev, category: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Question</label>
              <input
                type="text"
                value={newPrompt.question}
                onChange={(e) => setNewPrompt(prev => ({ ...prev, question: e.target.value }))}
                placeholder="e.g., How are you feeling right now?"
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
              />
            </div>

            <button
              onClick={handleCreatePrompt}
              disabled={creating || !newPrompt.scheduledTime || !newPrompt.question}
              className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-blue-700"
            >
              {creating ? 'Creating...' : 'Create Prompt'}
            </button>
          </div>
        )}

        {/* Upcoming Prompts */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="font-semibold text-gray-700">Upcoming Prompts</h2>
          </div>

          {upcomingPrompts.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No scheduled prompts. Create one above!
            </div>
          ) : (
            <div className="divide-y">
              {upcomingPrompts.map((prompt) => (
                <div key={prompt.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {prompt.categories?.map((cat) => (
                          <span key={cat} className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(cat)}`}>
                            {cat.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                      <p className="text-sm text-gray-700">
                        {Object.values(prompt.questions)[0]}
                      </p>
                    </div>
                    <span className="text-xs text-gray-500 whitespace-nowrap ml-4">
                      {formatScheduledTime(prompt.scheduled_time)}
                    </span>
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
