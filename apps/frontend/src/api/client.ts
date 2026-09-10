/**
 * Typed API Client for AstraTrace Backend Services.
 */
import { HealthResponse, SystemStatusResponse, ApiError } from '../types/api';

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
}
