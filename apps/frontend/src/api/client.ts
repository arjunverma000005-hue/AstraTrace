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
  SimilarTilesRequest,
  SimilarTilesResponse,
  EvidencePackageExportResponse,
  ProvenanceGraphResponse,
  ClusterListResponse,
  ClusterDetailResponse,
  ExportReportRequest,
  ExportReportResponse,
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
   * Searches for visually and semantically similar satellite tiles given a reference tile ID.
   */
  static async searchSimilarTiles(
    referenceTileId: string,
    topK: number = 5,
    minConfidence: number = 0.0,
  ): Promise<SimilarTilesResponse> {
    try {
      const payload: SimilarTilesRequest = {
        reference_tile_id: referenceTileId,
        top_k: topK,
        min_confidence: minConfidence,
      };

      const response = await fetch(`${API_BASE_URL}/search/similar-tiles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Similar tiles search error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to search similar tiles');
    }
  }

  /**
   * Retrieves full cryptographic provenance DAG (nodes and edges) for a target entity.
   */
  static async getProvenanceGraph(targetId: string): Promise<ProvenanceGraphResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/provenance/graph/${encodeURIComponent(targetId)}`);
      if (!response.ok) {
        throw new Error(`Provenance graph error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to fetch provenance graph');
    }
  }

  /**
   * Exports an offline, air-gapped forensic evidence dossier for a target entity.
   */
  static async exportDossier(targetId: string): Promise<EvidencePackageExportResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/provenance/export/${encodeURIComponent(targetId)}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Dossier export error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to export forensic evidence dossier');
    }
  }

  /**
   * Returns direct API URL for optical tile preview thumbnail.
   */
  static getTilePreviewUrl(tileId: string): string {
    return `${API_BASE_URL}/catalog/tiles/${encodeURIComponent(tileId)}/preview`;
  }

  /**
   * Returns direct API URL for full georeferenced optical scene preview image.
   */
  static getScenePreviewUrl(sceneId: string): string {
    return `${API_BASE_URL}/catalog/scenes/${encodeURIComponent(sceneId)}/preview`;
  }

  /**
   * Returns direct API URL for change mask image.
   */
  static getChangeMaskUrl(changeId: string): string {
    return `${API_BASE_URL}/change/mask/${encodeURIComponent(changeId)}`;
  }

  /**
   * Searches for tiles matching an uploaded reference image.
   */
  static async searchByImage(file: Blob | File, topK: number = 5): Promise<SimilarTilesResponse> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`${API_BASE_URL}/search/image?top_k=${topK}`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Image search error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to execute image similarity search');
    }
  }

  /**
   * Fetches unsupervised clusters across catalog tile embeddings.
   */
  static async getClusters(algorithm?: string): Promise<ClusterListResponse> {
    try {
      const url = algorithm ? `${API_BASE_URL}/clusters?algorithm=${algorithm}` : `${API_BASE_URL}/clusters`;
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Clusters error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to fetch tile clusters');
    }
  }

  /**
   * Fetches details and member tiles for a specific cluster.
   */
  static async getClusterDetail(clusterId: string): Promise<ClusterDetailResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/clusters/${encodeURIComponent(clusterId)}`);
      if (!response.ok) {
        throw new Error(`Cluster detail error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to fetch cluster details');
    }
  }

  /**
   * Generates and downloads a multi-format evidence dossier report.
   */
  static async exportReport(req: ExportReportRequest): Promise<ExportReportResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/export/report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      });
      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Export error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to export report');
    }
  }

  /**
   * Retrieves latest quantitative benchmark evaluation summary report.
   */
  static async getEvaluationSummary(): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/evaluation/summary`);
      if (!response.ok) {
        throw new Error(`Evaluation summary error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to fetch evaluation summary');
    }
  }

  /**
   * Triggers a fresh automated quantitative benchmark run.
   */
  static async triggerEvaluationRun(topK: number = 5): Promise<any> {
    try {
      const response = await fetch(`${API_BASE_URL}/evaluation/run?top_k=${topK}`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`Benchmark run error: HTTP ${response.status}`);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof Error) throw err;
      throw new Error('Failed to trigger benchmark run');
    }
  }
}


