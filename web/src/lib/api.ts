/**
 * API client for communicating with the Habit Bot backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export interface Prompt {
  id: number;
  user_id: number;
  scheduled_time: string;
  sent_at: string | null;
  acknowledged_at: string | null;
  questions: Record<string, string>;
  categories: string[];
  status: string;
  created_at: string;
}

export interface Response {
  id: number;
  prompt_id: number;
  user_id: number;
  question_text: string;
  response_text: string;
  response_structured: Record<string, unknown> | null;
  category: string;
  timestamp: string;
  processing_status: string;
  processing_attempts?: number;
}

export interface ResponseCreate {
  prompt_id: number;
  user_id: number;
  question_text: string;
  response_text: string;
  category: string;
}

export interface QuickLogResponse {
  response_id: number;
  category: string;
  summary: string;
  structured_data: Record<string, unknown> | null;
  processing_status: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API error: ${response.status} - ${error}`);
    }

    return response.json();
  }

  async getPrompt(promptId: number): Promise<Prompt> {
    return this.fetch<Prompt>(`/api/v1/prompts/${promptId}`);
  }

  async acknowledgePrompt(promptId: number): Promise<Prompt> {
    return this.fetch<Prompt>(`/api/v1/prompts/${promptId}/acknowledge`, {
      method: 'POST',
    });
  }

  async submitResponse(data: ResponseCreate): Promise<Response> {
    return this.fetch<Response>('/api/v1/responses/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async processResponseWithLLM(responseId: number): Promise<{ success: boolean }> {
    return this.fetch<{ success: boolean }>('/api/v1/llm/process-response', {
      method: 'POST',
      body: JSON.stringify({ response_id: responseId }),
    });
  }

  async healthCheck(): Promise<{ status: string }> {
    return this.fetch<{ status: string }>('/health');
  }

  async getResponses(params?: {
    user_id?: number;
    category?: string;
    limit?: number;
    offset?: number;
  }): Promise<Response[]> {
    const searchParams = new URLSearchParams();
    if (params?.user_id) searchParams.set('user_id', params.user_id.toString());
    if (params?.category) searchParams.set('category', params.category);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());

    const query = searchParams.toString();
    return this.fetch<Response[]>(`/api/v1/responses/${query ? `?${query}` : ''}`);
  }

  async quickLog(userId: number, text: string, timestamp?: string): Promise<QuickLogResponse> {
    const body: { user_id: number; text: string; timestamp?: string } = { user_id: userId, text };
    if (timestamp) {
      body.timestamp = timestamp;
    }
    return this.fetch<QuickLogResponse>('/api/v1/quicklog/', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async reprocessResponse(responseId: number): Promise<{ success: boolean }> {
    return this.processResponseWithLLM(responseId);
  }

  async deleteResponse(responseId: number): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/responses/${responseId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API error: ${response.status} - ${error}`);
    }
  }

  async getUpcomingPrompts(userId: number, limit: number = 10): Promise<Prompt[]> {
    return this.fetch<Prompt[]>(`/api/v1/prompts/upcoming?user_id=${userId}&limit=${limit}`);
  }
}

export const api = new ApiClient();
