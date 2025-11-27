'use client';

import { useEffect, useState } from 'react';
import { api, Reminder } from '@/lib/api';
import { formatUpcomingTime } from '@/lib/dateUtils';

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
  const [upcomingReminders, setUpcomingReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generateMessage, setGenerateMessage] = useState<string | null>(null);
  const [newReminder, setNewReminder] = useState({
    scheduledTime: '',
    category: 'mental_state',
    question: '',
  });

  const userId = 1;

  const loadReminders = async () => {
    try {
      const data = await api.getUpcomingReminders(userId, 20);
      setUpcomingReminders(data);
    } catch (err) {
      console.error('Failed to load reminders:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReminders();
  }, []);

  const handleGenerateReminders = async () => {
    setGenerating(true);
    setGenerateMessage(null);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/v1/reminders/generate?user_id=${userId}`, {
        method: 'POST',
      });

      const result = await response.json();
      if (response.ok) {
        if (result.scheduled > 0) {
          setGenerateMessage(`Created ${result.scheduled} new reminders`);
        } else {
          setGenerateMessage('No new reminders needed - schedule is up to date');
        }
        loadReminders();
      } else {
        setGenerateMessage(`Error: ${result.detail || 'Failed to generate'}`);
      }
    } catch (err) {
      setGenerateMessage('Error: Failed to connect');
    } finally {
      setGenerating(false);
    }
  };

  const handleCreateReminder = async () => {
    if (!newReminder.scheduledTime || !newReminder.question) return;

    setCreating(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api/v1/reminders/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          scheduled_time: new Date(newReminder.scheduledTime).toISOString(),
          questions: { q1: newReminder.question },
          categories: [newReminder.category],
        }),
      });

      if (response.ok) {
        setNewReminder({ scheduledTime: '', category: 'mental_state', question: '' });
        setShowCreateForm(false);
        loadReminders();
      }
    } catch (err) {
      console.error('Failed to create reminder:', err);
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
            <p className="text-gray-500 text-sm">Manage your check-in reminders</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleGenerateReminders}
              disabled={generating}
              className="bg-green-600 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {generating ? 'Generating...' : 'Auto-Generate'}
            </button>
            <button
              onClick={() => {
                setShowCreateForm(!showCreateForm);
                if (!newReminder.scheduledTime) {
                  setNewReminder(prev => ({ ...prev, scheduledTime: getDefaultTime() }));
                }
              }}
              className="bg-blue-600 text-white px-3 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              {showCreateForm ? 'Cancel' : '+ New'}
            </button>
          </div>
        </div>

        {/* Generate Message */}
        {generateMessage && (
          <div className={`p-3 rounded-lg text-sm ${
            generateMessage.startsWith('Error') ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'
          }`}>
            {generateMessage}
          </div>
        )}

        {/* Create Form */}
        {showCreateForm && (
          <div className="bg-white rounded-lg shadow p-4 space-y-4">
            <h2 className="font-semibold text-gray-700">Create New Reminder</h2>

            <div>
              <label className="block text-sm text-gray-600 mb-1">When</label>
              <input
                type="datetime-local"
                value={newReminder.scheduledTime}
                onChange={(e) => setNewReminder(prev => ({ ...prev, scheduledTime: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Category</label>
              <select
                value={newReminder.category}
                onChange={(e) => setNewReminder(prev => ({ ...prev, category: e.target.value }))}
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
                value={newReminder.question}
                onChange={(e) => setNewReminder(prev => ({ ...prev, question: e.target.value }))}
                placeholder="e.g., How are you feeling right now?"
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
              />
            </div>

            <button
              onClick={handleCreateReminder}
              disabled={creating || !newReminder.scheduledTime || !newReminder.question}
              className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-blue-700"
            >
              {creating ? 'Creating...' : 'Create Reminder'}
            </button>
          </div>
        )}

        {/* Upcoming Reminders */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="font-semibold text-gray-700">Upcoming Reminders</h2>
          </div>

          {upcomingReminders.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No scheduled reminders. Create one above!
            </div>
          ) : (
            <div className="divide-y">
              {upcomingReminders.map((reminder) => (
                <div key={reminder.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {reminder.categories?.map((cat) => (
                          <span key={cat} className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(cat)}`}>
                            {cat.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                      <p className="text-sm text-gray-700">
                        {Object.values(reminder.questions)[0]}
                      </p>
                    </div>
                    <span className="text-xs text-gray-500 whitespace-nowrap ml-4">
                      {formatUpcomingTime(reminder.scheduled_time)}
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
