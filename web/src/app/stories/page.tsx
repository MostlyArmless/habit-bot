'use client';

import { useEffect, useState } from 'react';
import { api, Story } from '@/lib/api';
import { formatTimestamp } from '@/lib/dateUtils';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

export default function StoriesPage() {
  const [stories, setStories] = useState<Story[]>([]);
  const [storyText, setStoryText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const userId = 1; // Default user for now

  const loadStories = async () => {
    try {
      const data = await api.getStories({ user_id: userId, limit: 50 });
      setStories(data);
    } catch (err) {
      console.error('Failed to load stories:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStories();
  }, []);

  // Auto-refresh when there are pending/processing stories
  useEffect(() => {
    const hasPending = stories.some(
      (s) => s.processing_status === 'pending' || s.processing_status === 'processing'
    );
    if (!hasPending) return;

    const interval = setInterval(() => {
      loadStories();
    }, 3000); // Refresh every 3 seconds

    return () => clearInterval(interval);
  }, [stories]);

  const handleSubmit = async () => {
    if (!storyText.trim() || isSubmitting) return;

    setIsSubmitting(true);

    try {
      await api.createStory({ user_id: userId, story_text: storyText });
      setStoryText('');
      loadStories();
    } catch (err) {
      console.error('Story submission failed:', err);
      alert('Failed to submit story. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (storyId: number) => {
    if (!confirm('Delete this story?')) return;

    setDeletingId(storyId);
    try {
      await api.deleteStory(storyId);
      setExpandedId(null);
      loadStories();
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete story.');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-800">Stories</h1>
          <p className="text-gray-500 text-sm">Daily storytelling practice with AI feedback</p>
        </div>

        {/* Story Submission */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="font-semibold text-gray-700 mb-3">Tell a Story</h2>
          <p className="text-sm text-gray-500 mb-3">
            Practice your storytelling skills. Share a personal story, anecdote, or experience.
            You'll receive Toastmaster-style feedback to help you improve.
          </p>
          <textarea
            value={storyText}
            onChange={(e) => setStoryText(e.target.value)}
            placeholder="Once upon a time..."
            className="w-full border rounded-lg p-3 text-sm text-gray-900 resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={6}
            disabled={isSubmitting}
          />
          <div className="flex justify-between items-center mt-3">
            <span className="text-xs text-gray-400">
              {storyText.length} characters
            </span>
            <button
              onClick={handleSubmit}
              disabled={!storyText.trim() || isSubmitting}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-700 transition-colors"
            >
              {isSubmitting ? 'Submitting...' : 'Submit Story'}
            </button>
          </div>
        </div>

        {/* Stories List */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="font-semibold text-gray-700">Your Stories</h2>
          </div>

          {isLoading ? (
            <div className="p-8 text-center text-gray-400">
              Loading...
            </div>
          ) : stories.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No stories yet. Submit your first story above!
            </div>
          ) : (
            <div className="divide-y">
              {stories.map((story) => (
                <div key={story.id} className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs text-gray-400">
                          {formatTimestamp(story.timestamp)}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[story.processing_status] || STATUS_COLORS.pending}`}>
                          {story.processing_status}
                        </span>
                        {story.processing_status === 'processing' && (
                          <span className="text-xs text-blue-600 animate-pulse">
                            Analyzing...
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">
                        {story.story_text.length > 200 && expandedId !== story.id
                          ? `${story.story_text.substring(0, 200)}...`
                          : story.story_text}
                      </p>
                      {story.story_text.length > 200 && (
                        <button
                          onClick={() => setExpandedId(expandedId === story.id ? null : story.id)}
                          className="text-xs text-blue-600 hover:text-blue-800 mt-1"
                        >
                          {expandedId === story.id ? 'Show less' : 'Show more'}
                        </button>
                      )}
                    </div>
                    <button
                      onClick={() => setExpandedId(expandedId === story.id ? null : story.id)}
                      className="text-gray-400 hover:text-gray-600 ml-2"
                    >
                      {expandedId === story.id ? '−' : '+'}
                    </button>
                  </div>

                  {/* Expanded Details - Feedback */}
                  {expandedId === story.id && (
                    <div className="mt-3 pt-3 border-t">
                      {story.feedback ? (
                        <div className="bg-blue-50 rounded-lg p-4">
                          <div className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
                            <span>💡</span>
                            <span>Toastmaster Feedback</span>
                          </div>

                          {(() => {
                            const feedback = story.feedback;
                            const strengths = feedback?.strengths;
                            const improvements = feedback?.improvements;
                            const overall = feedback?.overall;
                            const score = feedback?.score;

                            return (
                              <>
                                {/* Strengths */}
                                {strengths && Array.isArray(strengths) && strengths.length > 0 && (
                                  <div className="mb-3">
                                    <h4 className="text-sm font-medium text-green-700 mb-1">✅ Strengths</h4>
                                    <ul className="list-disc list-inside space-y-1">
                                      {strengths.map((strength, idx) => (
                                        <li key={idx} className="text-sm text-gray-700">{String(strength)}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {/* Areas for Improvement */}
                                {improvements && Array.isArray(improvements) && improvements.length > 0 && (
                                  <div className="mb-3">
                                    <h4 className="text-sm font-medium text-orange-700 mb-1">📈 Areas for Improvement</h4>
                                    <ul className="list-disc list-inside space-y-1">
                                      {improvements.map((improvement, idx) => (
                                        <li key={idx} className="text-sm text-gray-700">{String(improvement)}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {/* Overall Assessment */}
                                {overall && (
                                  <div className="mb-3">
                                    <h4 className="text-sm font-medium text-blue-700 mb-1">📝 Overall</h4>
                                    <p className="text-sm text-gray-700">{String(overall)}</p>
                                  </div>
                                )}

                                {/* Score */}
                                {score && (
                                  <div className="flex items-center gap-2 text-sm">
                                    <span className="font-medium text-blue-700">Score:</span>
                                    <span className="text-gray-700">{String(score)}/10</span>
                                  </div>
                                )}

                                {/* Fallback: show raw JSON if structure is different */}
                                {!strengths && !improvements && !overall && (
                                  <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-x-auto bg-white rounded p-2">
                                    {JSON.stringify(story.feedback, null, 2)}
                                  </pre>
                                )}
                              </>
                            );
                          })()}
                        </div>
                      ) : story.processing_status === 'completed' ? (
                        <div className="bg-yellow-50 rounded p-3 text-sm text-yellow-700">
                          Processing completed but no feedback available
                        </div>
                      ) : story.processing_status === 'failed' ? (
                        <div className="bg-red-50 rounded p-3 text-sm text-red-700">
                          Failed to generate feedback. The story may have encountered an error during processing.
                        </div>
                      ) : (
                        <div className="bg-gray-50 rounded p-3 text-sm text-gray-600">
                          Feedback will appear here once processing is complete...
                        </div>
                      )}

                      <div className="flex items-center gap-4 mt-3">
                        <button
                          onClick={() => handleDelete(story.id)}
                          disabled={deletingId === story.id}
                          className="text-sm text-red-600 hover:text-red-800"
                        >
                          {deletingId === story.id ? 'Deleting...' : 'Delete'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Info Card */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold text-blue-900 mb-2">💡 Tips for Great Storytelling</h3>
          <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>Include specific details and sensory descriptions</li>
            <li>Have a clear beginning, middle, and end</li>
            <li>Show emotions through actions and dialogue</li>
            <li>Make it personal and authentic</li>
            <li>Practice regularly to improve your skills</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
