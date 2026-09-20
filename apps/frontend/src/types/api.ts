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

export type ReviewDecision = 'PENDING_REVIEW' | 'CONFIRMED' | 'REJECTED' | 'FLAGGED_FOR_INSPECTION';
export type TargetType = 'TILE' | 'CHANGE';
export type SearchMode = 'AUTO' | 'HYBRID' | 'SEMANTIC' | 'KEYWORD' | 'CHANGE';

export interface EvidenceFirstCandidate {
  candidate_id: string;
  target_id: string;
  target_type: TargetType;
  rank: number;
  what: string;
  where: {
    bbox: [number, number, number, number];
    centroid: [number, number];
    geometry: {
      type: string;
      coordinates: number[][][];
    };
    coordinates?: [[number, number], [number, number], [number, number], [number, number]];
    crs?: string;
  };
  when: string | { datetime?: string | null; date?: string; observation_type?: string; [key: string]: any } | null;
  which: {
    sensor: string;
    scene_id?: string;
    tile_id?: string;
    tile_index?: number;
    before_scene_id?: string;
    after_scene_id?: string;
    before_tile_id?: string;
    after_tile_id?: string;
  };
  why: Record<string, unknown>;
  confidence: number;
  quality_status: string;
  quality_flags: string[];
  evidence: {
    preview_url?: string | null;
    mask_url?: string | null;
    usable_fraction: number;
    cloud_fraction: number;
    shadow_fraction: number;
    scene_preview_url?: string | null;
    scene_bbox?: [number, number, number, number] | null;
    scene_coordinates?: [[number, number], [number, number], [number, number], [number, number]] | null;
    before_scene_preview_url?: string | null;
    after_scene_preview_url?: string | null;
    before_date?: string | null;
    after_date?: string | null;
  };
  provenance: Record<string, unknown>;
  review_status: ReviewDecision;
}

export interface UnifiedSearchRequest {
  query?: string;
  search_mode?: SearchMode;
  bbox?: [number, number, number, number];
  point?: [number, number];
  date_from?: string;
  date_to?: string;
  sensor?: string;
  min_confidence?: number;
  allowed_quality_statuses?: string[];
  top_k?: number;
  page?: number;
  page_size?: number;
}

export interface UnifiedSearchResponse {
  query_id: string;
  query: string | null;
  search_mode: SearchMode;
  total_candidates: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: EvidenceFirstCandidate[];
  execution_trace: Record<string, number>;
}

export interface SubmitReviewRequest {
  target_id: string;
  target_type: TargetType;
  decision: ReviewDecision;
  analyst_id?: string;
  notes?: string;
}

export interface ReviewRecordResponse {
  review_id: string;
  target_id: string;
  target_type: TargetType;
  decision: ReviewDecision;
  analyst_id: string;
  notes: string | null;
  confidence_at_review: number;
  quality_status_at_review: string;
  provenance_snapshot: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ReviewQueueItem extends EvidenceFirstCandidate {
  queue_id: string;
  current_review?: ReviewRecordResponse | null;
}

export interface ReviewQueueResponse {
  total: number;
  pending_count: number;
  confirmed_count: number;
  rejected_count: number;
  flagged_count: number;
  items: ReviewQueueItem[];
}

export interface ReviewHistoryResponse {
  target_id: string;
  total_reviews: number;
  history: ReviewRecordResponse[];
}

export interface SimilarTilesRequest {
  reference_tile_id?: string;
  reference_raster_path?: string;
  bbox?: [number, number, number, number];
  sensor?: string;
  top_k?: number;
  min_confidence?: number;
}

export interface SemanticTileResult {
  rank: number;
  tile_id: string;
  scene_id: string;
  semantic_score: number;
  cosine_sim: number;
  baseline_score?: number | null;
  hybrid_score: number;
  bounds_wgs84: number[];
  geometry: Record<string, unknown>;
  checksum: string;
  acquired_at?: string | null;
  sensor: string;
  path: string;
}

export interface SimilarTilesResponse {
  query_id: string;
  search_mode: string;
  model_info: Record<string, unknown>;
  total_indexed: number;
  returned_results: number;
  results: SemanticTileResult[];
  execution_trace: Record<string, number>;
}

export interface EvidencePackageExportResponse {
  export_id: string;
  target_id: string;
  target_type: string;
  package_path: string;
  package_checksum: string;
  package_size_bytes: number;
  exported_at: string;
  contents_summary: Record<string, unknown>;
}

export interface ProvenanceNode {
  id: string;
  node_type: string;
  label: string;
  metadata: Record<string, unknown>;
  checksum?: string | null;
  timestamp?: string | null;
}

export interface ProvenanceEdge {
  source: string;
  target: string;
  edge_type: string;
  metadata?: Record<string, unknown> | null;
}

export interface ProvenanceGraphResponse {
  root_id: string;
  root_type: string;
  nodes: ProvenanceNode[];
  edges: ProvenanceEdge[];
  summary: Record<string, unknown>;
}

export interface ParsedQuerySlots {
  target?: string | null;
  change?: string | null;
  context?: string | null;
  time?: string | null;
  location?: string | null;
  sensor?: string | null;
  quality?: string | null;
}

export interface ScoreDecomposition {
  semantic: number;
  change: number;
  quality: number;
  temporal: number;
  spatial: number;
  final: number;
}

export interface ClusterRecord {
  cluster_id: string;
  label?: string;
  cluster_label?: string;
  size?: number;
  n_samples?: number;
  algorithm?: string;
  representative_tile_id?: string;
  representative_scene_id?: string;
  centroid_lon?: number;
  centroid_lat?: number;
  geographic_bounds?: {
    min_lon: number;
    min_lat: number;
    max_lon: number;
    max_lat: number;
  };
  convex_hull?: number[][];
  avg_similarity?: number;
  similarity_score?: number;
  tags?: string[];
  dominant_semantics?: string[];
  created_at?: string;
}

export interface ClusterListResponse {
  total_clusters?: number;
  algorithm?: string;
  clusters?: ClusterRecord[];
}

export interface ClusterDetailResponse {
  cluster: ClusterRecord;
  member_tile_ids: string[];
}

export interface ExportReportRequest {
  format: 'html' | 'pdf' | 'geojson' | 'csv';
  target_id?: string;
  candidate_ids?: string[];
  include_provenance?: boolean;
  include_evidence_thumbnails?: boolean;
}

export interface ExportReportResponse {
  export_id: string;
  format: string;
  download_url: string;
  file_name: string;
  size_bytes: number;
  checksum_sha256: string;
  created_at: string;
}



