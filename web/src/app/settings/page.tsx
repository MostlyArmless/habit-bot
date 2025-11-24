'use client';

import { useEffect, useState } from 'react';

interface User {
  id: number;
  name: string;
  timezone: string;
  wake_time: string | null;
  sleep_time: string | null;
  screens_off_time: string | null;
  bed_time: string | null;
}

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    timezone: 'UTC',
    wake_time: '',
    sleep_time: '',
    screens_off_time: '',
    bed_time: '',
  });

  const userId = 1;
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

  const loadUser = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/users/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setUser(data);
        setFormData({
          name: data.name || '',
          timezone: data.timezone || 'UTC',
          wake_time: data.wake_time || '',
          sleep_time: data.sleep_time || '',
          screens_off_time: data.screens_off_time || '',
          bed_time: data.bed_time || '',
        });
      }
    } catch (err) {
      console.error('Failed to load user:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUser();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);

    try {
      const updateData: Record<string, string | null> = {
        name: formData.name,
        timezone: formData.timezone,
      };

      // Only include time fields if they have values
      if (formData.wake_time) updateData.wake_time = formData.wake_time;
      if (formData.sleep_time) updateData.sleep_time = formData.sleep_time;
      if (formData.screens_off_time) updateData.screens_off_time = formData.screens_off_time;
      if (formData.bed_time) updateData.bed_time = formData.bed_time;

      const response = await fetch(`${API_URL}/api/v1/users/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updateData),
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Settings saved successfully' });
        loadUser();
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Failed to save' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to connect to server' });
    } finally {
      setSaving(false);
    }
  };

  const timezones = [
    'UTC',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'America/Anchorage',
    'Pacific/Honolulu',
    'Europe/London',
    'Europe/Paris',
    'Europe/Berlin',
    'Asia/Tokyo',
    'Asia/Shanghai',
    'Australia/Sydney',
  ];

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
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Settings</h1>
          <p className="text-gray-500 text-sm">Manage your preferences</p>
        </div>

        {/* Message */}
        {message && (
          <div className={`p-3 rounded-lg text-sm ${
            message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>
            {message.text}
          </div>
        )}

        {/* Profile Settings */}
        <div className="bg-white rounded-lg shadow p-4 space-y-4">
          <h2 className="font-semibold text-gray-700">Profile</h2>

          <div>
            <label className="block text-sm text-gray-600 mb-1">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-600 mb-1">Timezone</label>
            <select
              value={formData.timezone}
              onChange={(e) => setFormData(prev => ({ ...prev, timezone: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
            >
              {timezones.map((tz) => (
                <option key={tz} value={tz}>{tz}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Schedule Settings */}
        <div className="bg-white rounded-lg shadow p-4 space-y-4">
          <h2 className="font-semibold text-gray-700">Daily Schedule</h2>
          <p className="text-xs text-gray-500">Set your typical daily schedule to optimize prompt timing</p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Wake Time</label>
              <input
                type="time"
                value={formData.wake_time}
                onChange={(e) => setFormData(prev => ({ ...prev, wake_time: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Sleep Time</label>
              <input
                type="time"
                value={formData.sleep_time}
                onChange={(e) => setFormData(prev => ({ ...prev, sleep_time: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Screens Off</label>
              <input
                type="time"
                value={formData.screens_off_time}
                onChange={(e) => setFormData(prev => ({ ...prev, screens_off_time: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Bed Time</label>
              <input
                type="time"
                value={formData.bed_time}
                onChange={(e) => setFormData(prev => ({ ...prev, bed_time: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm text-gray-900"
              />
            </div>
          </div>
        </div>

        {/* App Info */}
        <div className="bg-white rounded-lg shadow p-4 space-y-2">
          <h2 className="font-semibold text-gray-700">About</h2>
          <div className="text-sm text-gray-600">
            <p>Habit Bot v0.1.0</p>
            <p className="text-xs text-gray-400 mt-1">Personal Health Tracking with EMA</p>
          </div>
        </div>

        {/* Save Button */}
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
