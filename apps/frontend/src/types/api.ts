/**
 * API Type Definitions matching Backend Schemas.
 */

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  offline_mode: boolean;
  timestamp: string;
}

export interface SystemStatusResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
  offline_mode: boolean;
  services: Record<string, string>;
  timestamp: string;
}

export interface ApiError {
  type: string;
  title: string;
  status: number;
  details?: Record<string, unknown>;
  request_id?: string;
}
