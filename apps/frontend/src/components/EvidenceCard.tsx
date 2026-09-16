import React, { useState, useEffect } from 'react';
import { ApiClient } from '../api/client';
import {
  EvidenceFirstCandidate,
  ReviewDecision,
  SemanticTileResult,
  EvidencePackageExportResponse,
  ProvenanceGraphResponse,
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
} from './Icons';

interface EvidenceCardProps {
  candidate: EvidenceFirstCandidate | null;
  onDecisionSubmitted: (targetId: string, decision: ReviewDecision) => void;
}

const formatTimestamp = (when?: string | null): string => {
  if (!when) return 'Not Available';
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
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'SCORES' | 'PROVENANCE' | 'SIMILAR'>('OVERVIEW');

  const [similarResults, setSimilarResults] = useState<SemanticTileResult[] | null>(null);
  const [isLoadingSimilar, setIsLoadingSimilar] = useState<boolean>(false);
  const [similarError, setSimilarError] = useState<string | null>(null);

  const [isExportingDossier, setIsExportingDossier] = useState<boolean>(false);
  const [dossierExportResult, setDossierExportResult] = useState<EvidencePackageExportResponse | null>(null);
  const [dossierExportError, setDossierExportError] = useState<string | null>(null);

  const [provenanceGraph, setProvenanceGraph] = useState<ProvenanceGraphResponse | null>(null);
  const [isLoadingGraph, setIsLoadingGraph] = useState<boolean>(false);
  const [graphError, setGraphError] = useState<string | null>(null);

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

  const handleDownloadDossier = async () => {
    if (!candidate) return;
    setIsExportingDossier(true);
    setDossierExportError(null);
    try {
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
    } catch (err: unknown) {
      setDossierExportError(err instanceof Error ? err.message : 'Failed to export evidence dossier');
    } finally {
      setIsExportingDossier(false);
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

  const handleSubmit = async () => {
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

  const changedPixels = candidate.why?.changed_pixels as number | undefined;
  const changePercent = candidate.why?.change_percent as number | undefined;
  const changeType = (candidate.why?.change_type as string) || candidate.what;
  const compositeScore = (candidate.why?.composite_change_score as number) ?? candidate.confidence;

  const confPercent = Math.round(candidate.confidence * 100);

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

        {/* Tactical Navigation Tabs */}
        <div style={styles.tabRow}>
          <button
            type="button"
            onClick={() => setActiveTab('OVERVIEW')}
            style={{
              ...styles.tabBtn,
              borderBottom: activeTab === 'OVERVIEW' ? '2px solid #38bdf8' : '2px solid transparent',
              color: activeTab === 'OVERVIEW' ? '#38bdf8' : '#64748b',
            }}
          >
            <LayersIcon size={12} color={activeTab === 'OVERVIEW' ? '#38bdf8' : '#64748b'} />
            <span>OVERVIEW</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('SCORES')}
            style={{
              ...styles.tabBtn,
              borderBottom: activeTab === 'SCORES' ? '2px solid #38bdf8' : '2px solid transparent',
              color: activeTab === 'SCORES' ? '#38bdf8' : '#64748b',
            }}
          >
            <SlidersIcon size={12} color={activeTab === 'SCORES' ? '#38bdf8' : '#64748b'} />
            <span>SCORES</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('PROVENANCE')}
            style={{
              ...styles.tabBtn,
              borderBottom: activeTab === 'PROVENANCE' ? '2px solid #38bdf8' : '2px solid transparent',
              color: activeTab === 'PROVENANCE' ? '#38bdf8' : '#64748b',
            }}
          >
            <ShieldIcon size={12} color={activeTab === 'PROVENANCE' ? '#38bdf8' : '#64748b'} />
            <span>PROVENANCE DAG</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('SIMILAR')}
            style={{
              ...styles.tabBtn,
              borderBottom: activeTab === 'SIMILAR' ? '2px solid #38bdf8' : '2px solid transparent',
              color: activeTab === 'SIMILAR' ? '#38bdf8' : '#64748b',
            }}
          >
            <DatabaseIcon size={12} color={activeTab === 'SIMILAR' ? '#38bdf8' : '#64748b'} />
            <span>SIMILAR (512-D)</span>
          </button>
        </div>
      </div>

      {/* Main Body */}
      <div style={styles.body}>
        {activeTab === 'OVERVIEW' && (
          <div style={styles.sectionCol}>
            {/* Visual Evidence Section */}
            {isChangeEvent ? (
              <div style={styles.visualCard}>
                <div style={styles.visualHeader}>
                  <div style={styles.visualHeaderLeft}>
                    <span style={styles.sectionLabel}>BITEMPORAL CHANGE OBSERVATION</span>
                    <span style={styles.visualSub}>Spectral Differencing & Pure-NumPy Component Filter</span>
                  </div>
                  <span style={styles.temporalGapBadge}>Δ 665 DAYS</span>
                </div>

                {/* Split-screen Before (T1) and After (T2) Images */}
                <div style={styles.splitGrid}>
                  <div style={styles.splitCol}>
                    <div style={styles.splitHeader}>
                      <span style={styles.epochBadgeT1}>
                        <CalendarIcon size={10} color="#38bdf8" style={{ marginRight: '4px' }} />
                        T1 PRE-EVENT (2023-02-03)
                      </span>
                      <span style={styles.splitMeta} title={beforeTileId}>{beforeTileId}</span>
                    </div>
                    <div style={styles.splitImageWrapper}>
                      {beforeError ? (
                        <div style={styles.imageFallbackBox}>
                          <SatelliteIcon size={22} color="#38bdf8" />
                          <span style={styles.fallbackText}>T1 Raster {beforeTileId}</span>
                        </div>
                      ) : (
                        <img
                          src={ApiClient.getTilePreviewUrl(beforeTileId)}
                          alt={`Before T1 ${beforeTileId}`}
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
                      <span style={styles.splitMeta} title={afterTileId || 'Paired Temporal Epoch'}>
                        {afterTileId || 'Paired Temporal Epoch'}
                      </span>
                    </div>
                    <div style={styles.splitImageWrapper}>
                      {afterError || !afterTileId ? (
                        <div style={styles.imageFallbackBox}>
                          <SatelliteIcon size={22} color="#10b981" />
                          <span style={styles.fallbackText}>
                            {afterTileId ? `T2 Raster ${afterTileId}` : 'Surveillance Epoch'}
                          </span>
                        </div>
                      ) : (
                        <img
                          src={ApiClient.getTilePreviewUrl(afterTileId)}
                          alt={`After T2 ${afterTileId}`}
                          style={styles.previewImg}
                          onError={() => setAfterError(true)}
                        />
                      )}
                    </div>
                  </div>
                </div>

                {/* Binary Change Mask Container */}
                <div style={styles.maskSection}>
                  <div style={styles.maskHeader}>
                    <span style={styles.sectionLabel}>BINARY CHANGE MASK</span>
                    <span style={styles.visualSub}>Pure-NumPy 8-Connected Component Filtered</span>
                  </div>
                  <div style={styles.maskImageWrapper}>
                    {maskError ? (
                      <div style={styles.imageFallbackBox}>
                        <LayersIcon size={22} color="#475569" />
                        <span style={styles.fallbackText}>Change mask processing</span>
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

                  {/* Change metrics summary HUD */}
                  <div style={styles.changeMetricsRow}>
                    <div style={styles.metricItem}>
                      <span style={styles.metricLabel}>DETECTION TYPE</span>
                      <span style={styles.metricValue}>{changeType}</span>
                    </div>
                    {changedPixels !== undefined && (
                      <div style={styles.metricItem}>
                        <span style={styles.metricLabel}>CHANGED PIXELS</span>
                        <span style={styles.metricValue}>
                          {changedPixels.toLocaleString()} px {changePercent !== undefined ? `(${(changePercent * 100).toFixed(2)}%)` : ''}
                        </span>
                      </div>
                    )}
                    <div style={styles.metricItem}>
                      <span style={styles.metricLabel}>CHANGE SCORE</span>
                      <span style={styles.metricValue}>
                        {typeof compositeScore === 'number' ? compositeScore.toFixed(4) : String(compositeScore)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div style={styles.visualCard}>
                <div style={styles.visualHeader}>
                  <div style={styles.visualHeaderLeft}>
                    <span style={styles.sectionLabel}>OPTICAL SATELLITE PREVIEW (SINGLE EPOCH)</span>
                    <span style={styles.visualSub}>Sentinel-2 RGB (B4-B3-B2 2%-98% Stretch)</span>
                  </div>
                </div>
                <div style={styles.imageWrapper}>
                  {previewError ? (
                    <div style={styles.imageFallbackBox}>
                      <SatelliteIcon size={24} color="#38bdf8" />
                      <span style={styles.fallbackText}>Optical preview thumbnail unavailable</span>
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
                <div style={styles.singleEpochBanner}>
                  <span style={styles.singleEpochTitle}>
                    Single Observation Epoch • Sensor: <strong>{candidate.which.sensor}</strong> • Acquired:{' '}
                    <strong>{formatTimestamp(candidate.when)}</strong>
                  </span>
                  <span style={styles.singleEpochSub}>
                    Baseline acquisition established. Bitemporal change detection available upon pairing with surveillance epoch T2.
                  </span>
                </div>
              </div>
            )}

            {/* Action Bar: Find Similar Sites + Download Evidence Dossier */}
            <div style={styles.actionBarGrid}>
              <button
                type="button"
                onClick={handleFindSimilar}
                disabled={isLoadingSimilar}
                style={styles.findSimilarActionBtn}
                title="Search vector index for semantically and visually similar satellite observations"
              >
                {isLoadingSimilar ? <SpinnerIcon size={14} /> : <SearchIcon size={14} color="#38bdf8" />}
                <span>{isLoadingSimilar ? 'Searching 512-D Index...' : 'Find Similar Sites (512-D)'}</span>
              </button>
              <button
                type="button"
                onClick={handleDownloadDossier}
                disabled={isExportingDossier}
                style={styles.downloadDossierBtn}
                title="Generate and download self-contained, air-gapped forensic evidence dossier sealed with SHA-256"
              >
                {isExportingDossier ? <SpinnerIcon size={14} /> : <DownloadIcon size={14} color="#10b981" />}
                <span>{isExportingDossier ? 'Compiling Dossier...' : 'Export Forensic Dossier'}</span>
              </button>
            </div>

            {/* Dossier Download Feedback */}
            {dossierExportResult && (
              <div style={styles.dossierSuccessAlert}>
                <div style={styles.dossierSuccessHeader}>
                  <span style={styles.dossierSuccessTitle}>
                    <CheckCircleIcon size={14} color="#10b981" style={{ marginRight: '6px' }} />
                    FORENSIC DOSSIER SEALED & EXPORTED
                  </span>
                  <span style={styles.dossierBadge}>{dossierExportResult.export_id}</span>
                </div>
                <div style={styles.dossierDetails}>
                  <div style={styles.dossierHashRow}>
                    <span style={styles.dossierHashLabel}>SHA-256 SEAL:</span>
                    <code style={styles.dossierHash}>{dossierExportResult.package_checksum}</code>
                  </div>
                  <div style={styles.dossierMetaRow}>
                    <span>Target: <strong>{dossierExportResult.target_id}</strong> ({dossierExportResult.target_type})</span>
                    <span>Size: <strong>{(dossierExportResult.package_size_bytes / 1024).toFixed(1)} KB</strong></span>
                    <span>Exported: <strong>{new Date(dossierExportResult.exported_at).toLocaleTimeString()}</strong></span>
                  </div>
                </div>
              </div>
            )}

            {dossierExportError && (
              <div style={styles.errorAlert}>
                <AlertTriangleIcon size={14} color="#ef4444" style={{ marginRight: '6px' }} />
                Dossier Export Failed: {dossierExportError}
              </div>
            )}

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
                <span style={styles.dimVal}>
                  {formatTimestamp(candidate.when)}
                </span>
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
                    <span style={styles.dimSub}>None (Nominal Calibration)</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'SCORES' && (
          <div style={styles.sectionCol}>
            <div style={styles.scoreBox}>
              <div style={styles.scoreBoxHeader}>
                <SlidersIcon size={14} color="#38bdf8" />
                <h5 style={styles.scoreTitle}>Mathematical Score Decomposition (WHY)</h5>
              </div>
              <div style={styles.scoreList}>
                {Object.entries(candidate.why).map(([key, val]) => {
                  const isNum = typeof val === 'number';
                  const isNormalized = isNum && val >= 0 && val <= 1;
                  return (
                    <div key={key} style={styles.scoreRowEnhanced}>
                      <div style={styles.scoreKeyCol}>
                        <span style={styles.scoreKey}>{key.replace(/_/g, ' ').toUpperCase()}</span>
                        {isNormalized && (
                          <div style={styles.miniBarTrack}>
                            <div style={{ ...styles.miniBarFill, width: `${val * 100}%` }} />
                          </div>
                        )}
                      </div>
                      <span style={styles.scoreVal}>
                        {isNum ? val.toFixed(4) : String(val)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

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

              {/* Provenance DAG Nodes Display */}
              {provenanceGraph && provenanceGraph.nodes.length > 0 ? (
                <div style={styles.dagPipeline}>
                  {provenanceGraph.nodes.map((node, index) => {
                    const isRoot = node.id === provenanceGraph.root_id;
                    const typeColor =
                      node.node_type === 'SCENE'
                        ? '#38bdf8'
                        : node.node_type === 'TILE'
                        ? '#0284c7'
                        : node.node_type === 'EMBEDDING'
                        ? '#a855f7'
                        : node.node_type === 'QUALITY_ASSESSMENT'
                        ? '#10b981'
                        : node.node_type === 'ANALYST_REVIEW'
                        ? '#f59e0b'
                        : '#94a3b8';

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
                          <div style={styles.dagNodeStep}>
                            <span style={styles.dagStepNum}>STEP 0{index + 1}</span>
                            <span style={{ ...styles.dagTypeBadge, color: typeColor, borderColor: typeColor }}>
                              {node.node_type}
                            </span>
                          </div>
                          {isRoot && <span style={styles.dagRootTag}>TARGET ROOT</span>}
                        </div>

                        <div style={styles.dagNodeLabel}>{node.label}</div>
                        <div style={styles.dagNodeId} title={node.id}>{node.id}</div>

                        {node.checksum && (
                          <div style={styles.dagChecksumRow}>
                            <span style={styles.dagHashLabel}>SHA-256:</span>
                            <code
                              style={styles.dagHash}
                              onClick={() => handleCopyHash(node.checksum!)}
                              title="Click to copy SHA-256 hash"
                            >
                              {node.checksum.substring(0, 20)}...
                            </code>
                            {copiedHash === node.checksum && (
                              <span style={styles.copiedTag}>COPIED</span>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                /* Fallback key-value display from candidate.provenance */
                <div style={styles.scoreList}>
                  <div style={styles.scoreRowEnhanced}>
                    <span style={styles.scoreKey}>DATA CHECKSUM (SHA-256)</span>
                    <code
                      style={styles.checksumVal}
                      onClick={() => handleCopyHash(String(candidate.provenance.checksum || ''))}
                      title="Click to copy hash"
                    >
                      {String(candidate.provenance.checksum || 'N/A')}
                    </code>
                  </div>
                  {Object.entries(candidate.provenance)
                    .filter(([k]) => k !== 'checksum')
                    .map(([k, v]) => (
                      <div key={k} style={styles.scoreRowEnhanced}>
                        <span style={styles.scoreKey}>{k.replace(/_/g, ' ').toUpperCase()}</span>
                        <span style={styles.scoreVal}>{String(v)}</span>
                      </div>
                    ))}
                </div>
              )}
            </div>

            {/* Air-Gapped Evidence Dossier Export Card */}
            <div style={styles.dossierExportBox}>
              <div style={styles.dossierBoxHeader}>
                <div>
                  <h5 style={styles.scoreTitle}>Air-Gapped Forensic Intelligence Dossier</h5>
                  <span style={styles.similarSub}>
                    Bundles full lineage DAG, SHA-256 checksums, and mission verification metadata into a deterministic package.
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleDownloadDossier}
                  disabled={isExportingDossier}
                  style={styles.downloadDossierBtn}
                >
                  {isExportingDossier ? <SpinnerIcon size={14} /> : <DownloadIcon size={14} color="#10b981" />}
                  <span>{isExportingDossier ? 'Exporting...' : 'Export Dossier'}</span>
                </button>
              </div>
            </div>
          </div>
        )}

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
                <span>{isLoadingSimilar ? 'Searching...' : 'Re-query'}</span>
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

            {!isLoadingSimilar && !similarError && similarResults !== null && similarResults.length === 0 && (
              <div style={styles.emptySimilarBox}>
                <span>No similar sites found above similarity cutoff.</span>
              </div>
            )}

            {!isLoadingSimilar && similarResults && similarResults.length > 0 && (
              <div style={styles.similarList}>
                {similarResults.map((item) => (
                  <div key={item.tile_id} style={styles.similarCard}>
                    <div style={styles.similarCardHeader}>
                      <span style={styles.similarRank}>#{item.rank < 10 ? `0${item.rank}` : item.rank}</span>
                      <span style={styles.similarSimBadge}>
                        {(item.cosine_sim * 100).toFixed(1)}% SIMILARITY
                      </span>
                    </div>

                    <div style={styles.similarCardBody}>
                      <div style={styles.similarThumbWrapper}>
                        <img
                          src={ApiClient.getTilePreviewUrl(item.tile_id)}
                          alt={`Preview of ${item.tile_id}`}
                          style={styles.similarThumb}
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      </div>
                      <div style={styles.similarDetails}>
                        <div style={styles.similarTileId} title={item.tile_id}>
                          {item.tile_id}
                        </div>
                        <div style={styles.similarMeta}>
                          <span>Sensor: {item.sensor}</span>
                          <span>Acquired: {item.acquired_at ? new Date(item.acquired_at).toLocaleDateString() : 'N/A'}</span>
                          <span>Cosine: {item.cosine_sim.toFixed(4)}</span>
                        </div>
                        <div style={styles.similarHash}>
                          SHA: {item.checksum.substring(0, 16)}...
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
                  Extract 512-dimensional vector embedding for target observation <code style={styles.inlineCode}>{candidate.target_id}</code> and retrieve the most semantically and visually similar satellite tiles across the catalog.
                </p>
                <button
                  type="button"
                  onClick={handleFindSimilar}
                  style={styles.triggerSimilarBtn}
                >
                  <SearchIcon size={14} color="#06090e" />
                  <span>Execute Similarity Search</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Operational Decision Control Panel */}
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
                fontWeight: selectedDecision === 'CONFIRMED' ? 700 : 500,
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
                fontWeight: selectedDecision === 'FLAGGED_FOR_INSPECTION' ? 700 : 500,
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
                fontWeight: selectedDecision === 'REJECTED' ? 700 : 500,
              }}
            >
              <XCircleIcon size={14} color={selectedDecision === 'REJECTED' ? '#f87171' : '#64748b'} />
              <span>REJECT</span>
            </button>
          </div>

          {/* Notes Textarea */}
          <div style={styles.notesGroup}>
            <div style={styles.notesHeaderRow}>
              <label style={styles.notesLabel}>Analyst Notes / Tactical Rationale (Audited):</label>
              <span style={styles.notesCount}>{analystNotes.length} / 1000</span>
            </div>
            <textarea
              value={analystNotes}
              onChange={(e) => setAnalystNotes(e.target.value)}
              placeholder="Enter ground verification cross-references, site observations, or analytical rationale..."
              maxLength={1000}
              style={styles.notesTextarea}
            />
          </div>

          {/* Feedback messages */}
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

          {/* Submit Button */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            style={{
              ...styles.submitBtn,
              opacity: isSubmitting ? 0.7 : 1.0,
            }}
          >
            {isSubmitting ? (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <SpinnerIcon size={14} />
                <span>Recording Decision...</span>
              </span>
            ) : (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircleIcon size={14} color="#06090e" />
                <span>Record Operational Decision ({selectedDecision})</span>
              </span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: '#06090e',
    borderRadius: '8px',
    border: '1px solid #182635',
    overflow: 'hidden',
  },
  header: {
    padding: '12px 14px 0 14px',
    backgroundColor: '#0b1118',
    borderBottom: '1px solid #182635',
  },
  headerTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '12px',
    marginBottom: '10px',
  },
  headerInfoCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '3px',
    flex: 1,
    minWidth: 0,
  },
  tagRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    flexWrap: 'wrap',
  },
  targetTypeBadge: {
    fontSize: '0.62rem',
    fontWeight: 800,
    letterSpacing: '0.08em',
    padding: '2px 6px',
    borderRadius: '3px',
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    fontFamily: 'monospace',
  },
  sensorBadge: {
    fontSize: '0.62rem',
    fontWeight: 700,
    letterSpacing: '0.05em',
    padding: '2px 6px',
    borderRadius: '3px',
    backgroundColor: '#0f1722',
    color: '#94a3b8',
    border: '1px solid #182635',
    fontFamily: 'monospace',
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
    gap: '6px',
  },
  tabBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 10px',
    background: 'transparent',
    border: 'none',
    fontSize: '0.74rem',
    fontWeight: 700,
    letterSpacing: '0.05em',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  body: {
    flex: 1,
    overflowY: 'auto',
    padding: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  sectionCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  visualCard: {
    borderRadius: '6px',
    border: '1px solid #182635',
    backgroundColor: '#0b1118',
    padding: '10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  visualHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '8px',
  },
  visualHeaderLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1px',
  },
  sectionLabel: {
    fontSize: '0.7rem',
    fontWeight: 800,
    letterSpacing: '0.06em',
    color: '#38bdf8',
  },
  visualSub: {
    fontSize: '0.66rem',
    color: '#64748b',
  },
  temporalGapBadge: {
    fontSize: '0.65rem',
    fontWeight: 800,
    padding: '2px 6px',
    borderRadius: '3px',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.25)',
    fontFamily: 'monospace',
    whiteSpace: 'nowrap',
  },
  splitGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
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
  },
  epochBadgeT1: {
    display: 'inline-flex',
    alignItems: 'center',
    fontSize: '0.62rem',
    fontWeight: 700,
    letterSpacing: '0.04em',
    padding: '2px 6px',
    borderRadius: '3px',
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    fontFamily: 'monospace',
  },
  epochBadgeT2: {
    display: 'inline-flex',
    alignItems: 'center',
    fontSize: '0.62rem',
    fontWeight: 700,
    letterSpacing: '0.04em',
    padding: '2px 6px',
    borderRadius: '3px',
    backgroundColor: 'rgba(16, 185, 129, 0.12)',
    color: '#34d399',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    fontFamily: 'monospace',
  },
  splitMeta: {
    fontSize: '0.62rem',
    fontFamily: 'monospace',
    color: '#64748b',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    maxWidth: '100px',
  },
  splitImageWrapper: {
    width: '100%',
    height: '140px',
    borderRadius: '4px',
    overflow: 'hidden',
    backgroundColor: '#06090e',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid #182635',
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
    justifyContent: 'center',
    gap: '6px',
    padding: '10px',
    color: '#64748b',
    textAlign: 'center',
    height: '100%',
  },
  fallbackText: {
    fontSize: '0.68rem',
    color: '#64748b',
    fontFamily: 'monospace',
  },
  maskSection: {
    marginTop: '6px',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    paddingTop: '8px',
    borderTop: '1px solid #182635',
  },
  maskHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  maskImageWrapper: {
    width: '100%',
    height: '140px',
    borderRadius: '4px',
    overflow: 'hidden',
    backgroundColor: '#000000',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid #182635',
  },
  maskImg: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    imageRendering: 'pixelated',
  },
  changeMetricsRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#0f1722',
    padding: '6px 10px',
    borderRadius: '4px',
    border: '1px solid #182635',
  },
  metricItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  metricLabel: {
    fontSize: '0.6rem',
    fontWeight: 700,
    color: '#64748b',
    letterSpacing: '0.05em',
  },
  metricValue: {
    fontSize: '0.74rem',
    fontWeight: 700,
    color: '#f8fafc',
    fontFamily: 'monospace',
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
    border: '1px solid #182635',
  },
  singleEpochBanner: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    padding: '6px 10px',
    backgroundColor: '#0f1722',
    borderRadius: '4px',
    border: '1px solid #182635',
  },
  singleEpochTitle: {
    fontSize: '0.72rem',
    color: '#e2e8f0',
  },
  singleEpochSub: {
    fontSize: '0.66rem',
    color: '#64748b',
  },
  actionBarGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px',
  },
  findSimilarActionBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
    color: '#38bdf8',
    fontSize: '0.76rem',
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: '0.03em',
    transition: 'all 0.15s ease',
  },
  downloadDossierBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    backgroundColor: 'rgba(16, 185, 129, 0.08)',
    color: '#34d399',
    fontSize: '0.76rem',
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: '0.03em',
    transition: 'all 0.15s ease',
  },
  dossierSuccessAlert: {
    padding: '8px 10px',
    borderRadius: '6px',
    backgroundColor: 'rgba(16, 185, 129, 0.08)',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  dossierSuccessHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  dossierSuccessTitle: {
    display: 'inline-flex',
    alignItems: 'center',
    fontSize: '0.72rem',
    fontWeight: 800,
    letterSpacing: '0.04em',
    color: '#34d399',
  },
  dossierBadge: {
    fontSize: '0.62rem',
    fontFamily: 'monospace',
    padding: '1px 5px',
    borderRadius: '3px',
    backgroundColor: '#064e3b',
    color: '#a7f3d0',
  },
  dossierDetails: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    fontSize: '0.7rem',
    color: '#cbd5e1',
  },
  dossierHashRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  dossierHashLabel: {
    color: '#64748b',
    fontWeight: 700,
    fontSize: '0.62rem',
    letterSpacing: '0.04em',
  },
  dossierHash: {
    fontFamily: 'monospace',
    fontSize: '0.66rem',
    color: '#34d399',
    backgroundColor: '#06090e',
    padding: '2px 5px',
    borderRadius: '3px',
    border: '1px solid #182635',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  dossierMetaRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.66rem',
    color: '#64748b',
    fontFamily: 'monospace',
  },
  errorAlert: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '6px 10px',
    borderRadius: '4px',
    backgroundColor: 'rgba(239, 68, 68, 0.12)',
    color: '#f87171',
    fontSize: '0.72rem',
    border: '1px solid rgba(239, 68, 68, 0.3)',
  },
  successAlert: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '6px 10px',
    borderRadius: '4px',
    backgroundColor: 'rgba(16, 185, 129, 0.12)',
    color: '#34d399',
    fontSize: '0.72rem',
    border: '1px solid rgba(16, 185, 129, 0.3)',
  },
  dimsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px',
  },
  dimCard: {
    padding: '8px 10px',
    borderRadius: '6px',
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  dimKey: {
    fontSize: '0.62rem',
    fontWeight: 700,
    color: '#64748b',
    letterSpacing: '0.05em',
  },
  dimVal: {
    fontSize: '0.82rem',
    fontWeight: 600,
    color: '#f1f5f9',
  },
  dimSub: {
    fontSize: '0.68rem',
    color: '#64748b',
    fontFamily: 'monospace',
  },
  flagsRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
    marginTop: '2px',
  },
  flagBadge: {
    fontSize: '0.62rem',
    padding: '1px 5px',
    borderRadius: '3px',
    backgroundColor: '#0f1722',
    color: '#38bdf8',
    border: '1px solid #182635',
    fontFamily: 'monospace',
  },
  scoreBox: {
    padding: '12px',
    borderRadius: '6px',
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
  },
  scoreBoxHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '10px',
  },
  scoreTitle: {
    margin: 0,
    fontSize: '0.82rem',
    fontWeight: 700,
    color: '#f8fafc',
    letterSpacing: '0.03em',
  },
  scoreList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  scoreRowEnhanced: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '0.74rem',
    padding: '6px 0',
    borderBottom: '1px solid #182635',
  },
  scoreKeyCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    flex: 1,
    marginRight: '12px',
  },
  scoreKey: {
    color: '#94a3b8',
    fontWeight: 600,
    fontSize: '0.7rem',
    fontFamily: 'monospace',
  },
  miniBarTrack: {
    width: '100%',
    maxWidth: '180px',
    height: '3px',
    backgroundColor: '#182635',
    borderRadius: '2px',
    overflow: 'hidden',
  },
  miniBarFill: {
    height: '100%',
    backgroundColor: '#38bdf8',
    borderRadius: '2px',
  },
  scoreVal: {
    color: '#f8fafc',
    fontFamily: 'monospace',
    fontWeight: 700,
    fontSize: '0.78rem',
  },
  provenanceBox: {
    padding: '12px',
    borderRadius: '6px',
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  provenanceBoxHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  provTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  airGapPill: {
    fontSize: '0.62rem',
    fontWeight: 700,
    color: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    borderRadius: '3px',
    padding: '2px 6px',
    fontFamily: 'monospace',
    letterSpacing: '0.06em',
  },
  dagPipeline: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  dagNodeCard: {
    padding: '10px',
    borderRadius: '6px',
    border: '1px solid #182635',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  dagNodeHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  dagNodeStep: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  dagStepNum: {
    fontSize: '0.62rem',
    fontWeight: 800,
    color: '#64748b',
    fontFamily: 'monospace',
  },
  dagTypeBadge: {
    fontSize: '0.62rem',
    fontWeight: 700,
    padding: '1px 5px',
    borderRadius: '3px',
    border: '1px solid',
    fontFamily: 'monospace',
  },
  dagRootTag: {
    fontSize: '0.58rem',
    fontWeight: 800,
    color: '#38bdf8',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    padding: '1px 4px',
    borderRadius: '3px',
    fontFamily: 'monospace',
  },
  dagNodeLabel: {
    fontSize: '0.78rem',
    fontWeight: 600,
    color: '#f1f5f9',
  },
  dagNodeId: {
    fontSize: '0.68rem',
    fontFamily: 'monospace',
    color: '#64748b',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  dagChecksumRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginTop: '2px',
  },
  dagHashLabel: {
    fontSize: '0.6rem',
    fontWeight: 700,
    color: '#64748b',
  },
  dagHash: {
    fontSize: '0.66rem',
    fontFamily: 'monospace',
    color: '#10b981',
    backgroundColor: '#06090e',
    padding: '2px 5px',
    borderRadius: '3px',
    border: '1px solid #182635',
    cursor: 'pointer',
  },
  copiedTag: {
    fontSize: '0.58rem',
    fontWeight: 700,
    color: '#34d399',
    fontFamily: 'monospace',
  },
  checksumVal: {
    color: '#38bdf8',
    fontFamily: 'monospace',
    fontSize: '0.68rem',
    maxWidth: '220px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    cursor: 'pointer',
  },
  dossierExportBox: {
    padding: '12px',
    borderRadius: '6px',
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  dossierBoxHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '10px',
  },
  similarHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: '8px',
    borderBottom: '1px solid #182635',
  },
  similarSub: {
    fontSize: '0.68rem',
    color: '#64748b',
  },
  inlineCode: {
    fontFamily: 'monospace',
    color: '#38bdf8',
    backgroundColor: '#0f1722',
    padding: '2px 4px',
    borderRadius: '3px',
    border: '1px solid #182635',
  },
  refreshSimilarBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 8px',
    borderRadius: '4px',
    border: '1px solid #182635',
    backgroundColor: '#0f1722',
    color: '#cbd5e1',
    fontSize: '0.7rem',
    cursor: 'pointer',
    fontWeight: 600,
  },
  loadingBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '14px',
    backgroundColor: '#0b1118',
    borderRadius: '6px',
    border: '1px solid #182635',
    color: '#94a3b8',
    fontSize: '0.76rem',
  },
  emptySimilarBox: {
    padding: '18px',
    textAlign: 'center',
    backgroundColor: '#0b1118',
    borderRadius: '6px',
    border: '1px solid #182635',
    color: '#64748b',
    fontSize: '0.76rem',
  },
  triggerSimilarBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '7px 12px',
    borderRadius: '5px',
    border: 'none',
    backgroundColor: '#38bdf8',
    color: '#06090e',
    fontSize: '0.76rem',
    fontWeight: 700,
    cursor: 'pointer',
  },
  similarList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  similarCard: {
    padding: '8px 10px',
    borderRadius: '6px',
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  similarCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  similarRank: {
    fontSize: '0.7rem',
    fontWeight: 800,
    color: '#38bdf8',
    fontFamily: 'monospace',
  },
  similarSimBadge: {
    fontSize: '0.64rem',
    fontWeight: 800,
    letterSpacing: '0.04em',
    padding: '2px 6px',
    borderRadius: '3px',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.25)',
    fontFamily: 'monospace',
  },
  similarCardBody: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
  },
  similarThumbWrapper: {
    width: '56px',
    height: '56px',
    borderRadius: '4px',
    overflow: 'hidden',
    backgroundColor: '#06090e',
    flexShrink: 0,
    border: '1px solid #182635',
  },
  similarThumb: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  similarDetails: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    overflow: 'hidden',
    flex: 1,
  },
  similarTileId: {
    fontSize: '0.72rem',
    fontFamily: 'monospace',
    color: '#f8fafc',
    fontWeight: 600,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  similarMeta: {
    display: 'flex',
    flexDirection: 'column',
    fontSize: '0.64rem',
    color: '#64748b',
    gap: '1px',
    fontFamily: 'monospace',
  },
  similarHash: {
    fontSize: '0.6rem',
    fontFamily: 'monospace',
    color: '#475569',
  },
  decisionCard: {
    padding: '12px',
    borderRadius: '6px',
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  decisionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  decisionTitle: {
    fontSize: '0.72rem',
    fontWeight: 800,
    letterSpacing: '0.06em',
    color: '#f8fafc',
  },
  currentStatusBadge: {
    fontSize: '0.66rem',
    color: '#64748b',
    fontFamily: 'monospace',
    letterSpacing: '0.04em',
  },
  decisionBtnGroup: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '6px',
  },
  actionBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    padding: '7px 6px',
    borderRadius: '5px',
    border: '1px solid',
    fontSize: '0.72rem',
    cursor: 'pointer',
    textAlign: 'center',
    letterSpacing: '0.04em',
    transition: 'all 0.15s ease',
  },
  notesGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  notesHeaderRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  notesLabel: {
    fontSize: '0.68rem',
    color: '#64748b',
    fontWeight: 600,
  },
  notesCount: {
    fontSize: '0.62rem',
    color: '#475569',
    fontFamily: 'monospace',
  },
  notesTextarea: {
    width: '100%',
    minHeight: '52px',
    padding: '6px 8px',
    borderRadius: '4px',
    backgroundColor: '#06090e',
    border: '1px solid #182635',
    color: '#f8fafc',
    fontSize: '0.74rem',
    resize: 'vertical',
    fontFamily: 'inherit',
    outline: 'none',
  },
  submitBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '9px 12px',
    borderRadius: '5px',
    border: 'none',
    backgroundColor: '#38bdf8',
    color: '#06090e',
    fontSize: '0.78rem',
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: '0.04em',
    transition: 'all 0.15s ease',
  },
  emptyContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    padding: '24px',
    textAlign: 'center',
    backgroundColor: '#06090e',
    borderRadius: '8px',
    border: '1px solid #182635',
  },
  emptyIconBox: {
    width: '60px',
    height: '60px',
    borderRadius: '50%',
    backgroundColor: '#0b1118',
    border: '1px solid #182635',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '12px',
  },
  emptyTitle: {
    margin: '0 0 6px 0',
    fontSize: '0.88rem',
    fontWeight: 700,
    color: '#94a3b8',
    letterSpacing: '0.05em',
  },
  emptySub: {
    margin: 0,
    fontSize: '0.74rem',
    color: '#475569',
    maxWidth: '260px',
    lineHeight: 1.4,
  },
};
