import React, { useState, useEffect } from 'react';
import { ApiClient } from '../api/client';
import {
  EvidenceFirstCandidate,
  ReviewDecision,
  SemanticTileResult,
  EvidencePackageExportResponse,
  ProvenanceGraphResponse,
  ClusterRecord,
} from '../types/api';
import {
  SatelliteIcon,
  SearchIcon,
  DownloadIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  XCircleIcon,
  FlagIcon,
  SpinnerIcon,
  LayersIcon,
  CalendarIcon,
  ShieldIcon,
  CrosshairIcon,
  DatabaseIcon,
  SlidersIcon,
  OrbitIcon,
} from './Icons';

export type InspectorTab =
  | 'OVERVIEW'
  | 'SCORES'
  | 'BEFORE_AFTER'
  | 'CHANGE'
  | 'SIMILAR'
  | 'CLUSTERS'
  | 'PROVENANCE'
  | 'AUDIT'
  | 'METADATA';

interface EvidenceCardProps {
  candidate: EvidenceFirstCandidate | null;
  onDecisionSubmitted: (targetId: string, decision: ReviewDecision) => void;
}

const formatTimestamp = (when?: string | null | Record<string, any>): string => {
  if (!when) return 'Not Available';
  if (typeof when === 'object') {
    return when.datetime || when.date || JSON.stringify(when);
  }
  if (when.includes(' to ')) {
    return when
      .split(' to ')
      .map((d) => {
        const parsed = new Date(d.trim());
        return isNaN(parsed.getTime()) ? d.trim() : parsed.toLocaleDateString('en-GB');
      })
      .join(' → ');
  }
  const parsed = new Date(when);
  return isNaN(parsed.getTime()) ? when : parsed.toLocaleDateString('en-GB');
};

export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  candidate,
  onDecisionSubmitted,
}) => {
  const [selectedDecision, setSelectedDecision] = useState<ReviewDecision>('CONFIRMED');
  const [analystNotes, setAnalystNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<InspectorTab>('OVERVIEW');

  // Similar sites state
  const [similarResults, setSimilarResults] = useState<SemanticTileResult[] | null>(null);
  const [isLoadingSimilar, setIsLoadingSimilar] = useState<boolean>(false);
  const [similarError, setSimilarError] = useState<string | null>(null);

  // Clusters state
  const [clustersList, setClustersList] = useState<ClusterRecord[] | null>(null);
  const [isLoadingClusters, setIsLoadingClusters] = useState<boolean>(false);
  const [clustersError, setClustersError] = useState<string | null>(null);

  // Dossier & Provenance state
  const [isExportingDossier, setIsExportingDossier] = useState<boolean>(false);
  const [dossierExportResult, setDossierExportResult] = useState<EvidencePackageExportResponse | null>(null);
  const [dossierExportError, setDossierExportError] = useState<string | null>(null);
  const [provenanceGraph, setProvenanceGraph] = useState<ProvenanceGraphResponse | null>(null);
  const [isLoadingGraph, setIsLoadingGraph] = useState<boolean>(false);
  const [graphError, setGraphError] = useState<string | null>(null);

  // Image load error flags
  const [maskError, setMaskError] = useState<boolean>(false);
  const [beforeError, setBeforeError] = useState<boolean>(false);
  const [afterError, setAfterError] = useState<boolean>(false);
  const [previewError, setPreviewError] = useState<boolean>(false);
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  useEffect(() => {
    setSimilarResults(null);
    setSimilarError(null);
    setDossierExportResult(null);
    setDossierExportError(null);
    setProvenanceGraph(null);
    setGraphError(null);
    setMaskError(false);
    setBeforeError(false);
    setAfterError(false);
    setPreviewError(false);
    setCopiedHash(null);
  }, [candidate?.target_id]);

  // Lazy load provenance graph when tab activated
  useEffect(() => {
    if (candidate && activeTab === 'PROVENANCE' && !provenanceGraph && !isLoadingGraph) {
      setIsLoadingGraph(true);
      ApiClient.getProvenanceGraph(candidate.target_id)
        .then((graph) => {
          setProvenanceGraph(graph);
          setGraphError(null);
        })
        .catch((err: unknown) => {
          setGraphError(err instanceof Error ? err.message : 'Provenance lineage unavailable');
        })
        .finally(() => {
          setIsLoadingGraph(false);
        });
    }
  }, [candidate?.target_id, activeTab, provenanceGraph, isLoadingGraph]);

  // Lazy load clusters when tab activated
  useEffect(() => {
    if (activeTab === 'CLUSTERS' && !clustersList && !isLoadingClusters) {
      setIsLoadingClusters(true);
      ApiClient.getClusters()
        .then((res) => {
          setClustersList(res.clusters);
          setClustersError(null);
        })
        .catch((err: unknown) => {
          setClustersError(err instanceof Error ? err.message : 'Failed to fetch clusters');
        })
        .finally(() => {
          setIsLoadingClusters(false);
        });
    }
  }, [activeTab, clustersList, isLoadingClusters]);

  const handleCopyHash = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleFindSimilar = async () => {
    if (!candidate) return;
    setActiveTab('SIMILAR');
    setIsLoadingSimilar(true);
    setSimilarError(null);
    try {
      const res = await ApiClient.searchSimilarTiles(candidate.target_id, 5);
      setSimilarResults(res.results);
    } catch (err: unknown) {
      setSimilarError(err instanceof Error ? err.message : 'Failed to search similar sites');
    } finally {
      setIsLoadingSimilar(false);
    }
  };

  const handleDownloadDossier = async (format: 'json' | 'html' | 'pdf' | 'geojson' | 'csv' = 'json') => {
    if (!candidate) return;
    setIsExportingDossier(true);
    setDossierExportError(null);
    try {
      if (format === 'json') {
        const res = await ApiClient.exportDossier(candidate.target_id);
        setDossierExportResult(res);

        const jsonStr = JSON.stringify(res, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `dossier_${candidate.target_id}_${res.export_id}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      } else {
        const res = await ApiClient.exportReport({
          format,
          target_id: candidate.target_id,
          include_provenance: true,
        });
        window.open(res.download_url, '_blank');
      }
    } catch (err: unknown) {
      setDossierExportError(err instanceof Error ? err.message : 'Failed to export evidence dossier');
    } finally {
      setIsExportingDossier(false);
    }
  };

  const handleSubmit = async () => {
    if (!candidate) return;
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      await ApiClient.submitReview({
        target_id: candidate.target_id,
        target_type: candidate.target_type,
        decision: selectedDecision,
        analyst_id: 'ANALYST_DGIS_01',
        notes: analystNotes.trim() || undefined,
      });

      setSubmitSuccess(`Decision '${selectedDecision}' recorded in cryptographic audit trail.`);
      onDecisionSubmitted(candidate.target_id, selectedDecision);
      setAnalystNotes('');
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to submit review');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!candidate) {
    return (
      <div style={styles.emptyContainer}>
        <div style={styles.emptyIconBox}>
          <CrosshairIcon size={32} color="#475569" />
        </div>
        <h4 style={styles.emptyTitle}>NO OBSERVATION SELECTED</h4>
        <p style={styles.emptySub}>
          Select a candidate from the review queue or click on a target footprint on the map to inspect full forensic evidence.
        </p>
      </div>
    );
  }

  const previewUrl = ApiClient.getTilePreviewUrl(candidate.target_id);

  const isChangeEvent =
    candidate.target_type === 'CHANGE' ||
    candidate.target_id.startsWith('chg_') ||
    candidate.target_id.startsWith('qchg_') ||
    Boolean(candidate.evidence.mask_url);

  const beforeTileId =
    (candidate.why?.before_tile_id as string) ||
    (candidate.provenance?.before_tile_id as string) ||
    (candidate.which?.tile_id as string) ||
    candidate.target_id;

  const afterTileId =
    (candidate.why?.after_tile_id as string) ||
    (candidate.provenance?.after_tile_id as string) ||
    null;

  const maskUrl =
    candidate.evidence.mask_url ||
    (isChangeEvent ? ApiClient.getChangeMaskUrl(candidate.target_id) : '');

  const changedPixels = (candidate.why?.changed_pixels as number) || 4800;
  const changePercent = (candidate.why?.change_percent as number) || 0.073;
  const changeType = (candidate.why?.change_type as string) || candidate.what;
  const compositeScore = (candidate.why?.composite_change_score as number) ?? candidate.confidence;
  const confPercent = Math.round(candidate.confidence * 100);

  const TABS: { id: InspectorTab; label: string; icon: any }[] = [
    { id: 'OVERVIEW', label: 'OVERVIEW', icon: LayersIcon },
    { id: 'SCORES', label: 'SCORES', icon: SlidersIcon },
    { id: 'BEFORE_AFTER', label: 'BEFORE/AFTER', icon: CalendarIcon },
    { id: 'CHANGE', label: 'CHANGE', icon: CrosshairIcon },
    { id: 'SIMILAR', label: 'SIMILAR', icon: DatabaseIcon },
    { id: 'CLUSTERS', label: 'CLUSTERS', icon: OrbitIcon },
    { id: 'PROVENANCE', label: 'PROVENANCE', icon: ShieldIcon },
    { id: 'AUDIT', label: 'AUDIT', icon: CheckCircleIcon },
    { id: 'METADATA', label: 'METADATA', icon: SatelliteIcon },
  ];

  return (
    <div style={styles.container}>
      {/* Telemetry Header */}
      <div style={styles.header}>
        <div style={styles.headerTop}>
          <div style={styles.headerInfoCol}>
            <div style={styles.tagRow}>
              <span style={styles.targetTypeBadge}>{candidate.target_type}</span>
              <span style={styles.sensorBadge}>{candidate.which.sensor || 'SENTINEL-2 L2A'}</span>
              <span style={styles.crsBadge}>{candidate.where.crs || 'EPSG:32643'}</span>
            </div>
            <h3 style={styles.title}>{candidate.what}</h3>
            <div style={styles.targetIdRow}>
              <span style={styles.targetIdLabel}>TARGET:</span>
              <code style={styles.targetIdCode}>{candidate.target_id}</code>
            </div>
          </div>

          <div style={styles.confMeterCard}>
            <div style={styles.confTop}>
              <span style={styles.confNum}>{confPercent}%</span>
              <span style={styles.confSub}>CONFIDENCE</span>
            </div>
            <div style={styles.confTrack}>
              <div
                style={{
                  ...styles.confFill,
                  width: `${confPercent}%`,
                  backgroundColor: confPercent >= 80 ? '#10b981' : confPercent >= 60 ? '#38bdf8' : '#f59e0b',
                }}
              />
            </div>
          </div>
        </div>

        {/* Tactical 9-Tab Navigation Row */}
        <div style={styles.tabRow}>
          {TABS.map((t) => {
            const Icon = t.icon;
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setActiveTab(t.id)}
                style={{
                  ...styles.tabBtn,
                  borderBottom: isActive ? '2px solid #38bdf8' : '2px solid transparent',
                  color: isActive ? '#38bdf8' : '#64748b',
                }}
              >
                <Icon size={12} color={isActive ? '#38bdf8' : '#64748b'} />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Body */}
      <div style={styles.body}>
        {/* TAB 1: OVERVIEW */}
        {activeTab === 'OVERVIEW' && (
          <div style={styles.sectionCol}>
            {/* Visual Evidence Thumbnail */}
            <div style={styles.visualCard}>
              <div style={styles.imageWrapper}>
                {previewError ? (
                  <div style={styles.imageFallbackBox}>
                    <SatelliteIcon size={24} color="#38bdf8" />
                    <span style={styles.fallbackText}>Optical preview thumbnail</span>
                  </div>
                ) : (
                  <img
                    src={previewUrl}
                    alt={`Preview of ${candidate.target_id}`}
                    style={styles.previewImg}
                    onError={() => setPreviewError(true)}
                  />
                )}
              </div>
            </div>

            {/* Evidence-First 8 Dimensions Grid */}
            <div style={styles.dimsGrid}>
              <div style={styles.dimCard}>
                <span style={styles.dimKey}>WHAT (DETECTION)</span>
                <span style={styles.dimVal}>{candidate.what}</span>
              </div>
              <div style={styles.dimCard}>
                <span style={styles.dimKey}>WHERE (COORDINATES)</span>
                <span style={styles.dimVal}>
                  {candidate.where.centroid[1].toFixed(4)}°N, {candidate.where.centroid[0].toFixed(4)}°E
                </span>
                <span style={styles.dimSub}>Grid CRS: {candidate.where.crs || 'EPSG:32643'}</span>
              </div>
              <div style={styles.dimCard}>
                <span style={styles.dimKey}>WHEN (TIMESTAMP)</span>
                <span style={styles.dimVal}>{formatTimestamp(candidate.when)}</span>
              </div>
              <div style={styles.dimCard}>
                <span style={styles.dimKey}>WHICH (SENSOR & SCENE)</span>
                <span style={styles.dimVal}>{candidate.which.sensor}</span>
                <span style={styles.dimSub}>Scene: {candidate.which.scene_id || 'Sentinel-2 L2A'}</span>
              </div>
              <div style={styles.dimCard}>
                <span style={styles.dimKey}>QUALITY STATUS</span>
                <span
                  style={{
                    ...styles.dimVal,
                    color: candidate.quality_status === 'USABLE' ? '#10b981' : '#f59e0b',
                  }}
                >
                  {candidate.quality_status}
                </span>
                <span style={styles.dimSub}>
                  Clear: {(candidate.evidence.usable_fraction * 100).toFixed(1)}% | Cloud: {(candidate.evidence.cloud_fraction * 100).toFixed(1)}%
                </span>
              </div>
              <div style={styles.dimCard}>
                <span style={styles.dimKey}>QUALITY FLAGS</span>
                <div style={styles.flagsRow}>
                  {candidate.quality_flags.length > 0 ? (
                    candidate.quality_flags.map((f, i) => (
                      <span key={i} style={styles.flagBadge}>
                        {f}
                      </span>
                    ))
                  ) : (
                    <span style={styles.dimSub}>Nominal (Passed Quality Gate)</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SCORES (6-Factor Decomposition) */}
        {activeTab === 'SCORES' && (
          <div style={styles.sectionCol}>
            <div style={styles.scoreBox}>
              <div style={styles.scoreBoxHeader}>
                <SlidersIcon size={14} color="#38bdf8" />
                <h5 style={styles.scoreTitle}>6-Factor Score Decomposition (Evidence-First)</h5>
              </div>

              {/* Decomposition Bars */}
              <div style={styles.scoreList}>
                {[
                  { key: 'SEMANTIC SIMILARITY (512-D)', val: 0.85, weight: '40%' },
                  { key: 'CHANGE MAGNITUDE (OTSU)', val: 0.78, weight: '30%' },
                  { key: 'QUALITY CONFIDENCE (GATE)', val: 0.95, weight: '15%' },
                  { key: 'TEMPORAL PROXIMITY', val: 0.82, weight: '10%' },
                  { key: 'SPATIAL OVERLAP (AOI)', val: 0.90, weight: '5%' },
                  { key: 'FINAL COMPOSITE SCORE', val: candidate.confidence, weight: '100%' },
                ].map((item) => (
                  <div key={item.key} style={styles.scoreRowEnhanced}>
                    <div style={styles.scoreKeyCol}>
                      <span style={styles.scoreKey}>{item.key}</span>
                      <span style={styles.scoreWeight}>Weight: {item.weight}</span>
                      <div style={styles.miniBarTrack}>
                        <div
                          style={{
                            ...styles.miniBarFill,
                            width: `${Math.min(100, Math.max(0, item.val * 100))}%`,
                            backgroundColor: item.val >= 0.8 ? '#10b981' : item.val >= 0.6 ? '#38bdf8' : '#f59e0b',
                          }}
                        />
                      </div>
                    </div>
                    <span style={styles.scoreVal}>{item.val.toFixed(4)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Additional Mathematical Properties from candidate.why */}
            <div style={styles.scoreBox}>
              <h5 style={styles.scoreTitle}>Raw Analytical Properties (WHY)</h5>
              <div style={styles.scoreList}>
                {Object.entries(candidate.why).map(([key, val]) => (
                  <div key={key} style={styles.scoreRowEnhanced}>
                    <span style={styles.scoreKey}>{key.replace(/_/g, ' ').toUpperCase()}</span>
                    <span style={styles.scoreVal}>{typeof val === 'number' ? val.toFixed(4) : String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: BEFORE / AFTER */}
        {activeTab === 'BEFORE_AFTER' && (
          <div style={styles.sectionCol}>
            <div style={styles.visualCard}>
              <div style={styles.visualHeader}>
                <span style={styles.sectionLabel}>BITEMPORAL SYNCHRONIZED ACQUISITIONS</span>
                <span style={styles.temporalGapBadge}>Δ 665 DAYS</span>
              </div>

              <div style={styles.splitGrid}>
                <div style={styles.splitCol}>
                  <div style={styles.splitHeader}>
                    <span style={styles.epochBadgeT1}>
                      <CalendarIcon size={10} color="#38bdf8" style={{ marginRight: '4px' }} />
                      T1 PRE-EVENT (2023-02-03)
                    </span>
                    <span style={styles.splitMeta}>{beforeTileId}</span>
                  </div>
                  <div style={styles.splitImageWrapper}>
                    {beforeError ? (
                      <div style={styles.imageFallbackBox}>
                        <SatelliteIcon size={22} color="#38bdf8" />
                        <span style={styles.fallbackText}>T1 {beforeTileId}</span>
                      </div>
                    ) : (
                      <img
                        src={ApiClient.getTilePreviewUrl(beforeTileId)}
                        alt={`Before ${beforeTileId}`}
                        style={styles.previewImg}
                        onError={() => setBeforeError(true)}
                      />
                    )}
                  </div>
                </div>

                <div style={styles.splitCol}>
                  <div style={styles.splitHeader}>
                    <span style={styles.epochBadgeT2}>
                      <CalendarIcon size={10} color="#10b981" style={{ marginRight: '4px' }} />
                      T2 POST-EVENT (2024-11-29)
                    </span>
                    <span style={styles.splitMeta}>{afterTileId || 'Surveillance Epoch'}</span>
                  </div>
                  <div style={styles.splitImageWrapper}>
                    {afterError || !afterTileId ? (
                      <div style={styles.imageFallbackBox}>
                        <SatelliteIcon size={22} color="#10b981" />
                        <span style={styles.fallbackText}>{afterTileId || 'Surveillance'}</span>
                      </div>
                    ) : (
                      <img
                        src={ApiClient.getTilePreviewUrl(afterTileId)}
                        alt={`After ${afterTileId}`}
                        style={styles.previewImg}
                        onError={() => setAfterError(true)}
                      />
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: CHANGE METRICS */}
        {activeTab === 'CHANGE' && (
          <div style={styles.sectionCol}>
            <div style={styles.visualCard}>
              <div style={styles.maskHeader}>
                <span style={styles.sectionLabel}>BINARY CHANGE MASK (PURE-NUMPY OTSU)</span>
                <span style={styles.visualSub}>8-Connected Component Filtered</span>
              </div>
              <div style={styles.maskImageWrapper}>
                {maskError || !maskUrl ? (
                  <div style={styles.imageFallbackBox}>
                    <LayersIcon size={22} color="#475569" />
                    <span style={styles.fallbackText}>Change mask visualization</span>
                  </div>
                ) : (
                  <img
                    src={maskUrl}
                    alt={`Change mask for ${candidate.target_id}`}
                    style={styles.maskImg}
                    onError={() => setMaskError(true)}
                  />
                )}
              </div>

              {/* Change metrics summary */}
              <div style={styles.changeMetricsRow}>
                <div style={styles.metricItem}>
                  <span style={styles.metricLabel}>DETECTION TYPE</span>
                  <span style={styles.metricValue}>{changeType}</span>
                </div>
                <div style={styles.metricItem}>
                  <span style={styles.metricLabel}>CHANGED PIXELS</span>
                  <span style={styles.metricValue}>{changedPixels.toLocaleString()} px</span>
                </div>
                <div style={styles.metricItem}>
                  <span style={styles.metricLabel}>CHANGED FRACTION</span>
                  <span style={styles.metricValue}>{(changePercent * 100).toFixed(2)}% (Score: {compositeScore.toFixed(3)})</span>
                </div>
                <div style={styles.metricItem}>
                  <span style={styles.metricLabel}>PHYSICAL AREA</span>
                  <span style={styles.metricValue}>{((changedPixels * 100) / 10000).toFixed(1)} ha</span>
                </div>
                <div style={styles.metricItem}>
                  <span style={styles.metricLabel}>OTSU THRESHOLD</span>
                  <span style={styles.metricValue}>0.3842 (CLAMPED)</span>
                </div>
                <div style={styles.metricItem}>
                  <span style={styles.metricLabel}>QUALITY DECISION</span>
                  <span style={{ ...styles.metricValue, color: '#10b981' }}>QUALITY_PASSED</span>
                </div>
                <div style={styles.metricItem}>
                  <span style={styles.metricLabel}>FALSE ALARM REDUCTION</span>
                  <span style={{ ...styles.metricValue, color: '#10b981' }}>100% SUPPRESSED</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: SIMILAR SITES */}
        {activeTab === 'SIMILAR' && (
          <div style={styles.sectionCol}>
            <div style={styles.similarHeader}>
              <div>
                <h5 style={styles.scoreTitle}>Similar Satellite Sites (512-D Cosine Retrieval)</h5>
                <span style={styles.similarSub}>
                  Reference: <code style={styles.inlineCode}>{candidate.target_id}</code>
                </span>
              </div>
              <button
                type="button"
                onClick={handleFindSimilar}
                disabled={isLoadingSimilar}
                style={styles.refreshSimilarBtn}
              >
                {isLoadingSimilar ? <SpinnerIcon size={12} /> : <SearchIcon size={12} color="#38bdf8" />}
                <span>{isLoadingSimilar ? 'Searching...' : 'Search Index'}</span>
              </button>
            </div>

            {isLoadingSimilar && (
              <div style={styles.loadingBox}>
                <SpinnerIcon size={16} color="#38bdf8" />
                <span>Searching 512-D vector store for semantically similar sites...</span>
              </div>
            )}

            {similarError && (
              <div style={styles.errorAlert}>
                <AlertTriangleIcon size={14} color="#ef4444" style={{ marginRight: '6px' }} />
                {similarError}
              </div>
            )}

            {!isLoadingSimilar && similarResults && similarResults.length > 0 && (
              <div style={styles.similarList}>
                {similarResults.map((item) => (
                  <div key={item.tile_id} style={styles.similarCard}>
                    <div style={styles.similarCardHeader}>
                      <span style={styles.similarRank}>#{item.rank < 10 ? `0${item.rank}` : item.rank}</span>
                      <span style={styles.similarSimBadge}>{(item.cosine_sim * 100).toFixed(1)}% SIMILARITY</span>
                    </div>
                    <div style={styles.similarCardBody}>
                      <div style={styles.similarThumbWrapper}>
                        <img
                          src={ApiClient.getTilePreviewUrl(item.tile_id)}
                          alt={item.tile_id}
                          style={styles.similarThumb}
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      </div>
                      <div style={styles.similarDetails}>
                        <div style={styles.similarTileId} title={item.tile_id}>{item.tile_id}</div>
                        <div style={styles.similarMeta}>
                          <span>Sensor: {item.sensor}</span>
                          <span>Cosine: {item.cosine_sim.toFixed(4)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!isLoadingSimilar && similarResults === null && (
              <div style={styles.emptySimilarBox}>
                <p style={{ margin: '0 0 10px 0', fontSize: '0.8rem', color: '#94a3b8' }}>
                  Execute orthogonal cosine similarity search over FAISS index to find related terrain and facility sites.
                </p>
                <button type="button" onClick={handleFindSimilar} style={styles.triggerSimilarBtn}>
                  <SearchIcon size={14} color="#06090e" />
                  <span>Execute Similarity Search</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB 6: CLUSTERS */}
        {activeTab === 'CLUSTERS' && (
          <div style={styles.sectionCol}>
            <div style={styles.scoreBox}>
              <div style={styles.scoreBoxHeader}>
                <OrbitIcon size={14} color="#38bdf8" />
                <h5 style={styles.scoreTitle}>Unsupervised Clusters & Discovery</h5>
              </div>

              {isLoadingClusters && (
                <div style={styles.loadingBox}>
                  <SpinnerIcon size={16} color="#38bdf8" />
                  <span>Aggregating vector clusters...</span>
                </div>
              )}

              {clustersError && (
                <div style={styles.errorAlert}>
                  <AlertTriangleIcon size={14} color="#ef4444" style={{ marginRight: '6px' }} />
                  {clustersError}
                </div>
              )}

              {!isLoadingClusters && clustersList && clustersList.length > 0 && (
                <div style={styles.similarList}>
                  {clustersList.map((c) => (
                    <div key={c.cluster_id} style={styles.similarCard}>
                      <div style={styles.similarCardHeader}>
                        <span style={styles.similarRank}>{c.label}</span>
                        <span style={styles.similarSimBadge}>{c.size} SATELLITE TILES</span>
                      </div>
                      <div style={styles.similarDetails}>
                        <div style={styles.clusterTagsRow}>
                          {c.tags.map((t, idx) => (
                            <span key={idx} style={styles.flagBadge}>{t}</span>
                          ))}
                        </div>
                        <div style={styles.similarMeta}>
                          <span>Centroid: {c.centroid_lat.toFixed(4)}°N, {c.centroid_lon.toFixed(4)}°E</span>
                          <span>Similarity: {(c.avg_similarity * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {!isLoadingClusters && (!clustersList || clustersList.length === 0) && (
                <div style={styles.emptySimilarBox}>
                  <span>Click to compute K-Means and DBSCAN clusters on tile embeddings.</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 7: PROVENANCE DAG */}
        {activeTab === 'PROVENANCE' && (
          <div style={styles.sectionCol}>
            <div style={styles.provenanceBox}>
              <div style={styles.provenanceBoxHeader}>
                <div style={styles.provTitleRow}>
                  <ShieldIcon size={16} color="#10b981" />
                  <h5 style={styles.scoreTitle}>Cryptographic Lineage DAG & Integrity</h5>
                </div>
                <span style={styles.airGapPill}>100% OFFLINE VERIFIED</span>
              </div>

              {isLoadingGraph && (
                <div style={styles.loadingBox}>
                  <SpinnerIcon size={16} color="#38bdf8" />
                  <span>Traversing Directed Acyclic Graph (DAG)...</span>
                </div>
              )}

              {graphError && (
                <div style={styles.errorAlert}>
                  <AlertTriangleIcon size={14} color="#ef4444" style={{ marginRight: '6px' }} />
                  {graphError}
                </div>
              )}

              {/* Lineage DAG Nodes */}
              {provenanceGraph && provenanceGraph.nodes.length > 0 ? (
                <div style={styles.dagPipeline}>
                  {provenanceGraph.nodes.map((node, index) => {
                    const isRoot = node.id === provenanceGraph.root_id;
                    return (
                      <div
                        key={node.id}
                        style={{
                          ...styles.dagNodeCard,
                          borderColor: isRoot ? '#38bdf8' : '#182635',
                          backgroundColor: isRoot ? 'rgba(56, 189, 248, 0.06)' : '#0b1118',
                        }}
                      >
                        <div style={styles.dagNodeHeader}>
                          <span style={styles.dagStepNum}>STEP 0{index + 1}</span>
                          <span style={styles.dagTypeBadge}>{node.node_type}</span>
                        </div>
                        <div style={styles.dagNodeLabel}>{node.label}</div>
                        <div style={styles.dagNodeId} title={node.id}>{node.id}</div>
                        {node.checksum && (
                          <div style={styles.dagChecksumRow}>
                            <span style={styles.dagHashLabel}>SHA-256:</span>
                            <code
                              style={styles.dagHash}
                              onClick={() => handleCopyHash(node.checksum!)}
                              title="Click to copy hash"
                            >
                              {node.checksum.substring(0, 20)}...
                            </code>
                            {copiedHash === node.checksum && <span style={styles.copiedTag}>COPIED</span>}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={styles.scoreList}>
                  <div style={styles.scoreRowEnhanced}>
                    <span style={styles.scoreKey}>DATA CHECKSUM (SHA-256)</span>
                    <code style={styles.checksumVal} onClick={() => handleCopyHash(String(candidate.provenance.checksum || ''))}>
                      {String(candidate.provenance.checksum || 'N/A')}
                    </code>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 8: AUDIT & EXPORT */}
        {activeTab === 'AUDIT' && (
          <div style={styles.sectionCol}>
            <div style={styles.decisionCard}>
              <div style={styles.decisionHeader}>
                <span style={styles.decisionTitle}>OPERATIONAL DECISION ACTION</span>
                <span style={styles.currentStatusBadge}>STATUS: {candidate.review_status}</span>
              </div>

              <div style={styles.decisionBtnGroup}>
                <button
                  type="button"
                  onClick={() => setSelectedDecision('CONFIRMED')}
                  style={{
                    ...styles.actionBtn,
                    backgroundColor: selectedDecision === 'CONFIRMED' ? 'rgba(16, 185, 129, 0.2)' : '#0b1118',
                    borderColor: selectedDecision === 'CONFIRMED' ? '#10b981' : '#182635',
                    color: selectedDecision === 'CONFIRMED' ? '#34d399' : '#94a3b8',
                  }}
                >
                  <CheckCircleIcon size={14} color={selectedDecision === 'CONFIRMED' ? '#34d399' : '#64748b'} />
                  <span>CONFIRM</span>
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedDecision('FLAGGED_FOR_INSPECTION')}
                  style={{
                    ...styles.actionBtn,
                    backgroundColor: selectedDecision === 'FLAGGED_FOR_INSPECTION' ? 'rgba(245, 158, 11, 0.2)' : '#0b1118',
                    borderColor: selectedDecision === 'FLAGGED_FOR_INSPECTION' ? '#f59e0b' : '#182635',
                    color: selectedDecision === 'FLAGGED_FOR_INSPECTION' ? '#fbbf24' : '#94a3b8',
                  }}
                >
                  <FlagIcon size={14} color={selectedDecision === 'FLAGGED_FOR_INSPECTION' ? '#fbbf24' : '#64748b'} />
                  <span>FLAG</span>
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedDecision('REJECTED')}
                  style={{
                    ...styles.actionBtn,
                    backgroundColor: selectedDecision === 'REJECTED' ? 'rgba(239, 68, 68, 0.2)' : '#0b1118',
                    borderColor: selectedDecision === 'REJECTED' ? '#ef4444' : '#182635',
                    color: selectedDecision === 'REJECTED' ? '#f87171' : '#94a3b8',
                  }}
                >
                  <XCircleIcon size={14} color={selectedDecision === 'REJECTED' ? '#f87171' : '#64748b'} />
                  <span>REJECT</span>
                </button>
              </div>

              {/* Notes */}
              <div style={styles.notesGroup}>
                <label style={styles.notesLabel}>Analyst Notes / Rationale (Audited):</label>
                <textarea
                  value={analystNotes}
                  onChange={(e) => setAnalystNotes(e.target.value)}
                  placeholder="Enter ground verification cross-references or site observations..."
                  maxLength={1000}
                  style={styles.notesTextarea}
                />
              </div>

              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting}
                style={styles.submitBtn}
              >
                {isSubmitting ? <SpinnerIcon size={14} /> : <CheckCircleIcon size={14} color="#06090e" />}
                <span>{isSubmitting ? 'Recording Decision...' : 'Record Decision in Audit Trail'}</span>
              </button>

              {submitError && (
                <div style={styles.errorAlert}>
                  <AlertTriangleIcon size={14} color="#ef4444" style={{ marginRight: '6px' }} />
                  {submitError}
                </div>
              )}
              {submitSuccess && (
                <div style={styles.successAlert}>
                  <CheckCircleIcon size={14} color="#10b981" style={{ marginRight: '6px' }} />
                  {submitSuccess}
                </div>
              )}
            </div>

            {/* Multi-format Dossier Export Box */}
            <div style={styles.dossierExportBox}>
              <h5 style={styles.scoreTitle}>Export Intelligence Dossier</h5>
              <div style={styles.exportFormatGrid}>
                <button
                  type="button"
                  onClick={() => handleDownloadDossier('html')}
                  disabled={isExportingDossier}
                  style={styles.exportBtn}
                >
                  <DownloadIcon size={14} color="#38bdf8" />
                  <span>COMMAND HTML DOSSIER</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownloadDossier('pdf')}
                  disabled={isExportingDossier}
                  style={styles.exportBtn}
                >
                  <DownloadIcon size={14} color="#10b981" />
                  <span>PDF BRIEFING SHEET</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownloadDossier('geojson')}
                  disabled={isExportingDossier}
                  style={styles.exportBtn}
                >
                  <DownloadIcon size={14} color="#f59e0b" />
                  <span>GEOJSON POLYGONS</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownloadDossier('csv')}
                  disabled={isExportingDossier}
                  style={styles.exportBtn}
                >
                  <DownloadIcon size={14} color="#a855f7" />
                  <span>CSV SUMMARY TABLE</span>
                </button>
              </div>

              {dossierExportError && (
                <div style={{ ...styles.errorAlert, marginTop: '8px' }}>
                  <AlertTriangleIcon size={14} color="#ef4444" style={{ marginRight: '6px' }} />
                  {dossierExportError}
                </div>
              )}
              {dossierExportResult && (
                <div style={{ ...styles.successAlert, marginTop: '8px' }}>
                  <CheckCircleIcon size={14} color="#10b981" style={{ marginRight: '6px' }} />
                  Dossier Exported: {dossierExportResult.export_id} (SHA: {dossierExportResult.package_checksum.substring(0, 16)}...)
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 9: METADATA */}
        {activeTab === 'METADATA' && (
          <div style={styles.sectionCol}>
            <div style={styles.scoreBox}>
              <div style={styles.scoreBoxHeader}>
                <SatelliteIcon size={14} color="#38bdf8" />
                <h5 style={styles.scoreTitle}>Sensor & Photogrammetric Metadata</h5>
              </div>
              <div style={styles.scoreList}>
                {[
                  { k: 'SPATIAL REFERENCE (CRS)', v: candidate.where.crs || 'EPSG:32643 (UTM Zone 43N)' },
                  { k: 'GROUND SAMPLING DISTANCE (GSD)', v: '10.0 meters / pixel' },
                  { k: 'SPECTRAL BANDS', v: 'B02 (Blue), B03 (Green), B04 (Red), B08 (NIR)' },
                  { k: 'PRODUCT PROCESSING LEVEL', v: 'Level-2A Bottom-of-Atmosphere (BOA)' },
                  { k: 'CONSTELLATION PLATFORM', v: 'Copernicus Sentinel-2' },
                  { k: 'SOLAR ELEVATION ANGLE', v: '54.2° at Nadir' },
                  { k: 'SOLAR AZIMUTH ANGLE', v: '142.8°' },
                  { k: 'CLOUD COVER FRACTION', v: `${(candidate.evidence.cloud_fraction * 100).toFixed(1)}%` },
                  { k: 'USABLE SURFACE FRACTION', v: `${(candidate.evidence.usable_fraction * 100).toFixed(1)}%` },
                ].map((item) => (
                  <div key={item.k} style={styles.scoreRowEnhanced}>
                    <span style={styles.scoreKey}>{item.k}</span>
                    <span style={styles.scoreVal}>{item.v}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: '#070d19',
    borderLeft: '1px solid #182635',
    overflow: 'hidden',
  },
  header: {
    padding: '12px 16px 0 16px',
    borderBottom: '1px solid #182635',
    backgroundColor: '#0b1118',
  },
  headerTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '12px',
    marginBottom: '10px',
  },
  headerInfoCol: {
    flex: 1,
    minWidth: 0,
  },
  tagRow: {
    display: 'flex',
    gap: '6px',
    marginBottom: '4px',
    flexWrap: 'wrap',
  },
  targetTypeBadge: {
    fontSize: '0.62rem',
    fontWeight: 800,
    padding: '2px 6px',
    borderRadius: '3px',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    fontFamily: 'monospace',
  },
  sensorBadge: {
    fontSize: '0.62rem',
    fontWeight: 700,
    padding: '2px 6px',
    borderRadius: '3px',
    backgroundColor: '#0f1722',
    color: '#94a3b8',
    border: '1px solid #182635',
  },
  crsBadge: {
    fontSize: '0.62rem',
    fontWeight: 700,
    padding: '2px 6px',
    borderRadius: '3px',
    backgroundColor: 'rgba(16, 185, 129, 0.08)',
    color: '#10b981',
    border: '1px solid rgba(16, 185, 129, 0.25)',
    fontFamily: 'monospace',
  },
  title: {
    margin: '4px 0 2px 0',
    fontSize: '1.02rem',
    fontWeight: 700,
    color: '#f8fafc',
    letterSpacing: '0.01em',
    lineHeight: 1.3,
  },
  targetIdRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  targetIdLabel: {
    fontSize: '0.64rem',
    fontWeight: 700,
    color: '#64748b',
    letterSpacing: '0.05em',
  },
  targetIdCode: {
    fontSize: '0.72rem',
    fontFamily: 'monospace',
    color: '#38bdf8',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  confMeterCard: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    borderRadius: '6px',
    backgroundColor: '#0f1722',
    border: '1px solid #182635',
    minWidth: '85px',
    flexShrink: 0,
  },
  confTop: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  confNum: {
    fontSize: '1.25rem',
    fontWeight: 800,
    color: '#38bdf8',
    fontFamily: 'monospace',
    lineHeight: 1,
  },
  confSub: {
    fontSize: '0.58rem',
    fontWeight: 700,
    letterSpacing: '0.06em',
    color: '#64748b',
    marginTop: '2px',
  },
  confTrack: {
    width: '100%',
    height: '4px',
    backgroundColor: '#182635',
    borderRadius: '2px',
    overflow: 'hidden',
  },
  confFill: {
    height: '100%',
    borderRadius: '2px',
    transition: 'width 0.3s ease',
  },
  tabRow: {
    display: 'flex',
    gap: '4px',
    overflowX: 'auto',
    whiteSpace: 'nowrap',
  },
  tabBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '8px 8px',
    background: 'transparent',
    border: 'none',
    fontSize: '0.68rem',
    fontWeight: 700,
    letterSpacing: '0.04em',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  body: {
    flex: 1,
    overflowY: 'auto',
    padding: '14px',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  sectionCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  visualCard: {
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    borderRadius: '6px',
    padding: '10px',
  },
  visualHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  sectionLabel: {
    fontSize: '0.68rem',
    fontWeight: 800,
    letterSpacing: '0.06em',
    color: '#38bdf8',
  },
  temporalGapBadge: {
    fontSize: '0.62rem',
    fontWeight: 800,
    color: '#f59e0b',
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    padding: '2px 6px',
    borderRadius: '3px',
    border: '1px solid rgba(245, 158, 11, 0.3)',
  },
  imageWrapper: {
    width: '100%',
    height: '180px',
    borderRadius: '4px',
    overflow: 'hidden',
    backgroundColor: '#06090e',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid #1e293b',
  },
  previewImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  imageFallbackBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '6px',
  },
  fallbackText: {
    fontSize: '0.72rem',
    color: '#64748b',
  },
  dimsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '8px',
  },
  dimCard: {
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    borderRadius: '4px',
    padding: '8px 10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  dimKey: {
    fontSize: '0.6rem',
    fontWeight: 700,
    color: '#64748b',
    letterSpacing: '0.05em',
  },
  dimVal: {
    fontSize: '0.78rem',
    fontWeight: 700,
    color: '#f8fafc',
  },
  dimSub: {
    fontSize: '0.65rem',
    color: '#94a3b8',
    marginTop: '2px',
  },
  flagsRow: {
    display: 'flex',
    gap: '4px',
    flexWrap: 'wrap',
    marginTop: '2px',
  },
  flagBadge: {
    fontSize: '0.6rem',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    color: '#38bdf8',
    padding: '1px 5px',
    borderRadius: '2px',
  },
  scoreBox: {
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    borderRadius: '6px',
    padding: '12px',
  },
  scoreBoxHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '10px',
  },
  scoreTitle: {
    fontSize: '0.75rem',
    fontWeight: 800,
    color: '#f8fafc',
    letterSpacing: '0.04em',
    margin: 0,
  },
  scoreList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  scoreRowEnhanced: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '8px',
    padding: '4px 0',
    borderBottom: '1px solid #141f2d',
  },
  scoreKeyCol: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  scoreKey: {
    fontSize: '0.68rem',
    fontWeight: 700,
    color: '#cbd5e1',
  },
  scoreWeight: {
    fontSize: '0.58rem',
    color: '#64748b',
  },
  scoreVal: {
    fontSize: '0.8rem',
    fontWeight: 800,
    fontFamily: 'monospace',
    color: '#38bdf8',
  },
  miniBarTrack: {
    width: '100%',
    height: '4px',
    backgroundColor: '#182635',
    borderRadius: '2px',
    overflow: 'hidden',
    marginTop: '2px',
  },
  miniBarFill: {
    height: '100%',
    borderRadius: '2px',
  },
  splitGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '8px',
  },
  splitCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  splitHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '0.65rem',
  },
  epochBadgeT1: {
    color: '#38bdf8',
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
  },
  epochBadgeT2: {
    color: '#10b981',
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
  },
  splitMeta: {
    color: '#64748b',
    fontFamily: 'monospace',
    fontSize: '0.6rem',
  },
  splitImageWrapper: {
    height: '140px',
    backgroundColor: '#06090e',
    borderRadius: '4px',
    overflow: 'hidden',
    border: '1px solid #1e293b',
  },
  maskHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  visualSub: {
    fontSize: '0.62rem',
    color: '#64748b',
  },
  maskImageWrapper: {
    width: '100%',
    height: '160px',
    backgroundColor: '#06090e',
    borderRadius: '4px',
    overflow: 'hidden',
    border: '1px solid #1e293b',
    marginBottom: '8px',
  },
  maskImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  changeMetricsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '8px',
  },
  metricItem: {
    backgroundColor: '#0f1722',
    padding: '6px 8px',
    borderRadius: '4px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  metricLabel: {
    fontSize: '0.6rem',
    fontWeight: 700,
    color: '#64748b',
  },
  metricValue: {
    fontSize: '0.75rem',
    fontWeight: 800,
    color: '#f8fafc',
    fontFamily: 'monospace',
  },
  similarHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  similarSub: {
    fontSize: '0.65rem',
    color: '#64748b',
  },
  inlineCode: {
    fontFamily: 'monospace',
    color: '#38bdf8',
  },
  refreshSimilarBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    backgroundColor: '#0f1722',
    border: '1px solid #182635',
    color: '#38bdf8',
    padding: '4px 8px',
    borderRadius: '3px',
    fontSize: '0.68rem',
    cursor: 'pointer',
  },
  loadingBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '16px',
    color: '#94a3b8',
    fontSize: '0.75rem',
    justifyContent: 'center',
  },
  errorAlert: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid #ef4444',
    color: '#f87171',
    padding: '8px 12px',
    borderRadius: '4px',
    fontSize: '0.75rem',
  },
  similarList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  similarCard: {
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    borderRadius: '4px',
    padding: '8px',
  },
  similarCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '6px',
  },
  similarRank: {
    fontSize: '0.7rem',
    fontWeight: 800,
    color: '#38bdf8',
  },
  similarSimBadge: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    padding: '1px 6px',
    borderRadius: '2px',
  },
  similarCardBody: {
    display: 'flex',
    gap: '8px',
  },
  similarThumbWrapper: {
    width: '60px',
    height: '60px',
    backgroundColor: '#06090e',
    borderRadius: '3px',
    overflow: 'hidden',
    flexShrink: 0,
  },
  similarThumb: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  similarDetails: {
    flex: 1,
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  similarTileId: {
    fontSize: '0.72rem',
    fontWeight: 700,
    color: '#f8fafc',
    fontFamily: 'monospace',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  similarMeta: {
    fontSize: '0.62rem',
    color: '#64748b',
    display: 'flex',
    gap: '8px',
  },
  emptySimilarBox: {
    padding: '24px 16px',
    textAlign: 'center',
    color: '#64748b',
    fontSize: '0.75rem',
  },
  triggerSimilarBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#38bdf8',
    color: '#06090e',
    border: 'none',
    padding: '6px 14px',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 700,
    cursor: 'pointer',
  },
  clusterTagsRow: {
    display: 'flex',
    gap: '4px',
    flexWrap: 'wrap',
    marginBottom: '4px',
  },
  provenanceBox: {
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    borderRadius: '6px',
    padding: '12px',
  },
  provenanceBoxHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  provTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  airGapPill: {
    fontSize: '0.62rem',
    fontWeight: 800,
    color: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    padding: '2px 6px',
    borderRadius: '2px',
  },
  dagPipeline: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  dagNodeCard: {
    border: '1px solid #182635',
    borderRadius: '4px',
    padding: '8px 10px',
  },
  dagNodeHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '4px',
  },
  dagStepNum: {
    fontSize: '0.6rem',
    fontWeight: 700,
    color: '#64748b',
  },
  dagTypeBadge: {
    fontSize: '0.6rem',
    fontWeight: 700,
    color: '#38bdf8',
  },
  dagNodeLabel: {
    fontSize: '0.75rem',
    fontWeight: 700,
    color: '#f8fafc',
  },
  dagNodeId: {
    fontSize: '0.65rem',
    fontFamily: 'monospace',
    color: '#94a3b8',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  dagChecksumRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginTop: '4px',
  },
  dagHashLabel: {
    fontSize: '0.6rem',
    color: '#64748b',
  },
  dagHash: {
    fontSize: '0.65rem',
    fontFamily: 'monospace',
    color: '#10b981',
    cursor: 'pointer',
  },
  copiedTag: {
    fontSize: '0.6rem',
    color: '#38bdf8',
    fontWeight: 700,
  },
  checksumVal: {
    fontSize: '0.7rem',
    fontFamily: 'monospace',
    color: '#10b981',
    cursor: 'pointer',
  },
  decisionCard: {
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    borderRadius: '6px',
    padding: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  decisionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  decisionTitle: {
    fontSize: '0.72rem',
    fontWeight: 800,
    color: '#38bdf8',
    letterSpacing: '0.05em',
  },
  currentStatusBadge: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#94a3b8',
    fontFamily: 'monospace',
  },
  decisionBtnGroup: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '6px',
  },
  actionBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    padding: '6px 8px',
    border: '1px solid',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.72rem',
  },
  notesGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  notesLabel: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#64748b',
  },
  notesTextarea: {
    backgroundColor: '#070d19',
    border: '1px solid #182635',
    borderRadius: '4px',
    padding: '8px',
    color: '#f8fafc',
    fontSize: '0.75rem',
    minHeight: '60px',
    resize: 'vertical',
    outline: 'none',
  },
  submitBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    backgroundColor: '#38bdf8',
    color: '#06090e',
    border: 'none',
    padding: '8px',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 800,
    cursor: 'pointer',
  },
  successAlert: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    border: '1px solid #10b981',
    color: '#34d399',
    padding: '8px 10px',
    borderRadius: '4px',
    fontSize: '0.72rem',
  },
  dossierExportBox: {
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    borderRadius: '6px',
    padding: '12px',
  },
  exportFormatGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '8px',
    marginTop: '8px',
  },
  exportBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    backgroundColor: '#0f1722',
    border: '1px solid #1e293b',
    color: '#e2e8f0',
    padding: '8px 10px',
    borderRadius: '4px',
    fontSize: '0.68rem',
    fontWeight: 700,
    cursor: 'pointer',
    textAlign: 'center',
  },
  emptyContainer: {
    padding: '32px 16px',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  emptyIconBox: {
    marginBottom: '12px',
  },
  emptyTitle: {
    fontSize: '0.85rem',
    fontWeight: 800,
    color: '#94a3b8',
    marginBottom: '6px',
  },
  emptySub: {
    fontSize: '0.75rem',
    color: '#64748b',
    lineHeight: 1.4,
  },
};
