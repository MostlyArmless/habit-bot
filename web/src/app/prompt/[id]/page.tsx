'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api, Prompt } from '@/lib/api';

interface QuestionResponse {
  questionKey: string;
  questionText: string;
  response: string;
  category: string;
}

export default function PromptPage() {
  const params = useParams();
  const router = useRouter();
  const promptId = Number(params.id);

  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const loadPrompt = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const data = await api.getPrompt(promptId);
      setPrompt(data);

      // Initialize responses object
      const initialResponses: Record<string, string> = {};
      Object.keys(data.questions).forEach((key) => {
        initialResponses[key] = '';
      });
      setResponses(initialResponses);

      // Acknowledge the prompt
      if (data.status === 'sent') {
        await api.acknowledgePrompt(promptId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prompt');
    } finally {
      setLoading(false);
    }
  }, [promptId]);

  useEffect(() => {
    if (promptId) {
      loadPrompt();
    }
  }, [promptId, loadPrompt]);

  const handleResponseChange = (key: string, value: string) => {
    setResponses((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    if (!prompt) return;

    setSubmitting(true);
    setError(null);

    try {
      // Submit each question's response
      const questionEntries = Object.entries(prompt.questions);

      for (let i = 0; i < questionEntries.length; i++) {
        const [key, questionText] = questionEntries[i];
        const responseText = responses[key];

        if (!responseText.trim()) {
          continue; // Skip empty responses
        }

        // Determine category from prompt categories
        const category = prompt.categories[i % prompt.categories.length] || 'general';

        const response = await api.submitResponse({
          prompt_id: promptId,
          user_id: prompt.user_id,
          question_text: questionText,
          response_text: responseText,
          category: category,
        });

        // Trigger LLM processing in background
        api.processResponseWithLLM(response.id).catch(console.error);
      }

      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit responses');
    } finally {
      setSubmitting(false);
    }
  };

  const allAnswered = Object.values(responses).some((r) => r.trim() !== '');

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading questions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full">
          <div className="text-center">
            <div className="text-red-500 text-5xl mb-4">!</div>
            <h1 className="text-xl font-semibold text-gray-800 mb-2">Error</h1>
            <p className="text-gray-600 mb-4">{error}</p>
            <button
              onClick={loadPrompt}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full text-center">
          <div className="text-green-500 text-5xl mb-4">&#10003;</div>
          <h1 className="text-xl font-semibold text-gray-800 mb-2">Thank You!</h1>
          <p className="text-gray-600 mb-4">Your responses have been recorded.</p>
          <button
            onClick={() => router.push('/')}
            className="text-blue-600 hover:underline"
          >
            Return Home
          </button>
        </div>
      </div>
    );
  }

  if (!prompt) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
        <div className="text-center">
          <p className="text-gray-600">Prompt not found</p>
        </div>
      </div>
    );
  }

  const questions = Object.entries(prompt.questions);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          {/* Header */}
          <div className="bg-blue-600 text-white px-6 py-4">
            <h1 className="text-xl font-semibold">Check-in</h1>
            <p className="text-blue-100 text-sm mt-1">
              {prompt.categories.join(', ')}
            </p>
          </div>

          {/* Questions */}
          <div className="p-6 space-y-6">
            {questions.map(([key, questionText], index) => (
              <div key={key} className="space-y-2">
                <label className="block text-gray-800 font-medium">
                  {index + 1}. {questionText}
                </label>
                <textarea
                  value={responses[key] || ''}
                  onChange={(e) => handleResponseChange(key, e.target.value)}
                  placeholder="Type your response here..."
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-gray-900 placeholder-gray-400"
                />
              </div>
            ))}
          </div>

          {/* Submit Button */}
          <div className="px-6 py-4 bg-gray-50 border-t">
            <button
              onClick={handleSubmit}
              disabled={!allAnswered || submitting}
              className={`w-full py-3 rounded-lg font-semibold transition-colors ${
                allAnswered && !submitting
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              }`}
            >
              {submitting ? 'Submitting...' : 'Submit Responses'}
            </button>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-gray-500 text-sm mt-4">
          Prompt #{promptId}
        </p>
      </div>
    </div>
  );
}
