/**
 * Typed API Client for AstraTrace Backend Services.
 */
import {
  HealthResponse,
  SystemStatusResponse,
  ApiError,
  UnifiedSearchRequest,
  UnifiedSearchResponse,
  ReviewDecision,
  ReviewQueueResponse,
  SubmitReviewRequest,
  ReviewRecordResponse,
  ReviewHistoryResponse,
} from '../types/api';

const API_BASE_URL = '/api/v1';

export class ApiClient {
  /**
   * Fetches backend health check.
   */
  static async getHealth(): Promise<HealthResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (!response.ok) {
        const errorData: ApiError = await response.json().catch(() => ({
          type: 'urn:astratrace:error:http',
          title: response.statusText,
          status: response.status,
        }));
        throw new Error(errorData.title || `HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) {
        throw err;
      }
      throw new Error('Unknown error communicating with backend');
    }
  }

  /**
   * Fetches detailed system and service status.
   */
  static async getStatus(): Promise<SystemStatusResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/status`);
      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) {
        throw err;
      }
      throw new Error('Unknown error fetching system status');
    }
  }

  /**
   * Executes unified multi-modal search (keyword, semantic, spatial, temporal).
   */
  static async unifiedSearch(req: UnifiedSearchRequest): Promise<UnifiedSearchResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/search/unified`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      });
      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || errJson.title || `Search error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to execute unified search');
    }
  }

  /**
   * Retrieves paginated items from the analyst review queue.
   */
  static async getReviewQueue(
    status?: ReviewDecision,
    targetType?: string,
    limit: number = 50,
    offset: number = 0,
  ): Promise<ReviewQueueResponse> {
    try {
      const params = new URLSearchParams();
      if (status) params.set('status', status);
      if (targetType) params.set('target_type', targetType);
      params.set('limit', String(limit));
      params.set('offset', String(offset));

      const response = await fetch(`${API_BASE_URL}/review/queue?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`Queue error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to fetch review queue');
    }
  }

  /**
   * Submits a human-in-the-loop analyst review decision.
   */
  static async submitReview(req: SubmitReviewRequest): Promise<ReviewRecordResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/review/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      });
      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Review submission error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to submit analyst review');
    }
  }

  /**
   * Retrieves decision audit history for a specific candidate.
   */
  static async getReviewHistory(targetId: string): Promise<ReviewHistoryResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/review/history/${encodeURIComponent(targetId)}`);
      if (!response.ok) {
        throw new Error(`History error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to fetch review history');
    }
  }

  /**
   * Returns direct API URL for optical tile preview thumbnail.
   */
  static getTilePreviewUrl(tileId: string): string {
    return `${API_BASE_URL}/catalog/tiles/${encodeURIComponent(tileId)}/preview`;
  }

  /**
   * Returns direct API URL for change mask image.
   */
  static getChangeMaskUrl(changeId: string): string {
    return `${API_BASE_URL}/change/mask/${encodeURIComponent(changeId)}`;
  }
}

