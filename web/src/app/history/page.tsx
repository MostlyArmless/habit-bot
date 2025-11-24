'use client';

import { useEffect, useState } from 'react';
import { api, Response as ApiResponse } from '@/lib/api';

const CATEGORY_COLORS: Record<string, string> = {
  sleep: 'bg-indigo-100 text-indigo-800',
  nutrition: 'bg-green-100 text-green-800',
  physical_activity: 'bg-orange-100 text-orange-800',
  substances: 'bg-purple-100 text-purple-800',
  stress_anxiety: 'bg-red-100 text-red-800',
  mental_state: 'bg-yellow-100 text-yellow-800',
  physical_symptoms: 'bg-pink-100 text-pink-800',
  social_interaction: 'bg-cyan-100 text-cyan-800',
  work_productivity: 'bg-blue-100 text-blue-800',
  default: 'bg-gray-100 text-gray-800',
};

const CATEGORIES = [
  'all',
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

function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.default;
}

function formatDate(timestamp: string): string {
  const utcTimestamp = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z';
  const date = new Date(utcTimestamp);
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export default function HistoryPage() {
  const [responses, setResponses] = useState<ApiResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const limit = 20;

  const userId = 1;

  const loadResponses = async (reset: boolean = false) => {
    const newOffset = reset ? 0 : offset;

    try {
      const params: { user_id: number; limit: number; offset: number; category?: string } = {
        user_id: userId,
        limit: limit + 1, // Fetch one extra to check if there's more
        offset: newOffset,
      };

      if (selectedCategory !== 'all') {
        params.category = selectedCategory;
      }

      const data = await api.getResponses(params);

      if (data.length > limit) {
        setHasMore(true);
        data.pop(); // Remove the extra item
      } else {
        setHasMore(false);
      }

      if (reset) {
        setResponses(data);
        setOffset(limit);
      } else {
        setResponses(prev => [...prev, ...data]);
        setOffset(newOffset + limit);
      }
    } catch (err) {
      console.error('Failed to load responses:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    loadResponses(true);
  }, [selectedCategory]);

  if (loading && responses.length === 0) {
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
          <h1 className="text-2xl font-bold text-gray-800">History</h1>
          <p className="text-gray-500 text-sm">All your logged entries</p>
        </div>

        {/* Category Filter */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                selectedCategory === cat
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100'
              }`}
            >
              {cat === 'all' ? 'All' : cat.replace(/_/g, ' ')}
            </button>
          ))}
        </div>

        {/* Responses List */}
        <div className="bg-white rounded-lg shadow">
          {responses.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No entries found for this category.
            </div>
          ) : (
            <div className="divide-y">
              {responses.map((response) => (
                <div key={response.id} className="p-4">
                  <div
                    className="flex items-start justify-between cursor-pointer"
                    onClick={() => setExpandedId(expandedId === response.id ? null : response.id)}
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${getCategoryColor(response.category)}`}>
                          {response.category?.replace(/_/g, ' ')}
                        </span>
                        <span className="text-xs text-gray-400">
                          {formatDate(response.timestamp)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700">{response.response_text}</p>
                    </div>
                    <span className="text-gray-400 ml-2">
                      {expandedId === response.id ? '−' : '+'}
                    </span>
                  </div>

                  {/* Expanded Details */}
                  {expandedId === response.id && (
                    <div className="mt-3 pt-3 border-t">
                      <div className="text-xs text-gray-500 mb-2">
                        Question: {response.question_text}
                      </div>

                      {response.response_structured ? (
                        <div className="bg-gray-50 rounded p-3">
                          <div className="text-sm font-medium text-gray-700 mb-2">Analysis</div>
                          <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-x-auto">
                            {JSON.stringify(response.response_structured, null, 2)}
                          </pre>
                        </div>
                      ) : (
                        <div className="bg-yellow-50 rounded p-3 text-sm text-yellow-700">
                          No analysis available
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Load More */}
          {hasMore && responses.length > 0 && (
            <div className="p-4 border-t">
              <button
                onClick={() => loadResponses(false)}
                className="w-full py-2 text-sm text-blue-600 hover:text-blue-800"
              >
                Load more
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
