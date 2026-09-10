import React, { useState } from 'react';
import { ApiClient } from '../api/client';
import { EvidenceFirstCandidate, ReviewDecision } from '../types/api';

interface EvidenceCardProps {
  candidate: EvidenceFirstCandidate | null;
  onDecisionSubmitted: (targetId: string, decision: ReviewDecision) => void;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  candidate,
  onDecisionSubmitted,
}) => {
  const [selectedDecision, setSelectedDecision] = useState<ReviewDecision>('CONFIRMED');
  const [analystNotes, setAnalystNotes] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'OVERVIEW' | 'SCORES' | 'PROVENANCE'>('OVERVIEW');

  if (!candidate) {
    return (
      <div style={styles.emptyContainer}>
        <span style={styles.emptyIcon}>🔍</span>
        <h4 style={styles.emptyTitle}>No Observation Selected</h4>
        <p style={styles.emptySub}>
          Select a candidate from the review queue or click on a footprint on the map to inspect evidence.
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

      setSubmitSuccess(`Decision '${selectedDecision}' recorded in audit log.`);
      onDecisionSubmitted(candidate.target_id, selectedDecision);
      setAnalystNotes('');
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to submit review');
    } finally {
      setIsSubmitting(false);
    }
  };

  const previewUrl = ApiClient.getTilePreviewUrl(candidate.target_id);

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerTop}>
          <div>
            <span style={styles.targetType}>{candidate.target_type} TARGET</span>
            <h3 style={styles.title}>{candidate.what}</h3>
            <span style={styles.targetId}>{candidate.target_id}</span>
          </div>
          <div style={styles.confBadgeLarge}>
            <span style={styles.confNum}>{(candidate.confidence * 100).toFixed(0)}%</span>
            <span style={styles.confSub}>CONFIDENCE</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div style={styles.tabRow}>
          <button
            onClick={() => setActiveTab('OVERVIEW')}
            style={{
              ...styles.tabBtn,
              borderBottom: activeTab === 'OVERVIEW' ? '2px solid #38bdf8' : 'none',
              color: activeTab === 'OVERVIEW' ? '#38bdf8' : '#94a3b8',
            }}
          >
            Evidence Overview
          </button>
          <button
            onClick={() => setActiveTab('SCORES')}
            style={{
              ...styles.tabBtn,
              borderBottom: activeTab === 'SCORES' ? '2px solid #38bdf8' : 'none',
              color: activeTab === 'SCORES' ? '#38bdf8' : '#94a3b8',
            }}
          >
            Score Decomposition
          </button>
          <button
            onClick={() => setActiveTab('PROVENANCE')}
            style={{
              ...styles.tabBtn,
              borderBottom: activeTab === 'PROVENANCE' ? '2px solid #38bdf8' : 'none',
              color: activeTab === 'PROVENANCE' ? '#38bdf8' : '#94a3b8',
            }}
          >
            Provenance & Audit
          </button>
        </div>
      </div>

      {/* Body Content */}
      <div style={styles.body}>
        {activeTab === 'OVERVIEW' && (
          <div style={styles.sectionCol}>
            {/* Visual Evidence Imagery Preview */}
            <div style={styles.visualCard}>
              <div style={styles.visualHeader}>
                <span style={styles.sectionLabel}>OPTICAL SATELLITE PREVIEW</span>
                <span style={styles.visualSub}>Sentinel-2 RGB (B4-B3-B2 2%-98% Stretch)</span>
              </div>
              <div style={styles.imageWrapper}>
                <img
                  src={previewUrl}
                  alt={`Preview of ${candidate.target_id}`}
                  style={styles.previewImg}
                  onError={(e) => {
                    // Fallback to placeholder if thumbnail is generating
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
              </div>
            </div>

            {/* Evidence-First 8 Dimensions Grid */}
            <div style={styles.dimsGrid}>
              <div style={styles.dimCard}>
                <span style={styles.dimKey}>WHAT (Detection)</span>
                <span style={styles.dimVal}>{candidate.what}</span>
              </div>
              <div style={styles.dimCard}>
                <span style={styles.dimKey}>WHERE (Location)</span>
                <span style={styles.dimVal}>
                  {candidate.where.centroid[1].toFixed(4)}°N, {candidate.where.centroid[0].toFixed(4)}°E
                </span>
                <span style={styles.dimSub}>CRS: {candidate.where.crs || 'EPSG:4326'}</span>
              </div>
              <div style={styles.dimCard}>
                <span style={styles.dimKey}>WHEN (Timestamp)</span>
                <span style={styles.dimVal}>
                  {candidate.when ? new Date(candidate.when).toUTCString() : 'Not Available'}
                </span>
              </div>
              <div style={styles.dimCard}>
                <span style={styles.dimKey}>WHICH (Sensor/Source)</span>
                <span style={styles.dimVal}>{candidate.which.sensor}</span>
                <span style={styles.dimSub}>Scene: {candidate.which.scene_id || 'N/A'}</span>
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
                  Clear-sky: {(candidate.evidence.usable_fraction * 100).toFixed(1)}% | Cloud: {(candidate.evidence.cloud_fraction * 100).toFixed(1)}%
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
                    <span style={styles.dimSub}>None (Nominal)</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'SCORES' && (
          <div style={styles.sectionCol}>
            <div style={styles.scoreBox}>
              <h5 style={styles.scoreTitle}>Mathematical Score Decomposition (WHY)</h5>
              <div style={styles.scoreList}>
                {Object.entries(candidate.why).map(([key, val]) => (
                  <div key={key} style={styles.scoreRow}>
                    <span style={styles.scoreKey}>{key.replace(/_/g, ' ').toUpperCase()}</span>
                    <span style={styles.scoreVal}>
                      {typeof val === 'number' ? val.toFixed(4) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'PROVENANCE' && (
          <div style={styles.sectionCol}>
            <div style={styles.provenanceBox}>
              <h5 style={styles.scoreTitle}>Cryptographic Lineage & Provenance</h5>
              <div style={styles.scoreList}>
                <div style={styles.scoreRow}>
                  <span style={styles.scoreKey}>DATA CHECKSUM (SHA-256)</span>
                  <span style={styles.checksumVal}>{String(candidate.provenance.checksum || 'N/A')}</span>
                </div>
                {Object.entries(candidate.provenance)
                  .filter(([k]) => k !== 'checksum')
                  .map(([k, v]) => (
                    <div key={k} style={styles.scoreRow}>
                      <span style={styles.scoreKey}>{k.replace(/_/g, ' ').toUpperCase()}</span>
                      <span style={styles.scoreVal}>{String(v)}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        )}

        {/* Analyst Decision Control Panel */}
        <div style={styles.decisionCard}>
          <div style={styles.decisionHeader}>
            <span style={styles.decisionTitle}>OPERATIONAL DECISION ACTION</span>
            <span style={styles.currentStatusBadge}>Status: {candidate.review_status}</span>
          </div>

          <div style={styles.decisionBtnGroup}>
            <button
              onClick={() => setSelectedDecision('CONFIRMED')}
              style={{
                ...styles.actionBtn,
                backgroundColor: selectedDecision === 'CONFIRMED' ? '#10b981' : '#1e293b',
                borderColor: selectedDecision === 'CONFIRMED' ? '#34d399' : '#334155',
                color: selectedDecision === 'CONFIRMED' ? '#064e3b' : '#f1f5f9',
                fontWeight: selectedDecision === 'CONFIRMED' ? 800 : 600,
              }}
            >
              ✓ Confirm Target
            </button>
            <button
              onClick={() => setSelectedDecision('FLAGGED_FOR_INSPECTION')}
              style={{
                ...styles.actionBtn,
                backgroundColor: selectedDecision === 'FLAGGED_FOR_INSPECTION' ? '#f59e0b' : '#1e293b',
                borderColor: selectedDecision === 'FLAGGED_FOR_INSPECTION' ? '#fbbf24' : '#334155',
                color: selectedDecision === 'FLAGGED_FOR_INSPECTION' ? '#451a03' : '#f1f5f9',
                fontWeight: selectedDecision === 'FLAGGED_FOR_INSPECTION' ? 800 : 600,
              }}
            >
              ⚠ Flag for Review
            </button>
            <button
              onClick={() => setSelectedDecision('REJECTED')}
              style={{
                ...styles.actionBtn,
                backgroundColor: selectedDecision === 'REJECTED' ? '#ef4444' : '#1e293b',
                borderColor: selectedDecision === 'REJECTED' ? '#f87171' : '#334155',
                color: selectedDecision === 'REJECTED' ? '#450a0a' : '#f1f5f9',
                fontWeight: selectedDecision === 'REJECTED' ? 800 : 600,
              }}
            >
              ✕ Reject (False Alarm)
            </button>
          </div>

          {/* Notes Textarea */}
          <div style={styles.notesGroup}>
            <label style={styles.notesLabel}>Analyst Notes / Tactical Rationale (Audited):</label>
            <textarea
              value={analystNotes}
              onChange={(e) => setAnalystNotes(e.target.value)}
              placeholder="Enter observations, ground verification cross-references, or artifact rationale..."
              maxLength={1000}
              style={styles.notesTextarea}
            />
          </div>

          {/* Feedback messages */}
          {submitError && <div style={styles.errorAlert}>{submitError}</div>}
          {submitSuccess && <div style={styles.successAlert}>{submitSuccess}</div>}

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            style={{
              ...styles.submitBtn,
              opacity: isSubmitting ? 0.7 : 1.0,
            }}
          >
            {isSubmitting ? 'Recording Decision...' : `Submit ${selectedDecision} Decision`}
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
    backgroundColor: '#0f172a',
    borderRadius: '8px',
    border: '1px solid #1e293b',
    overflow: 'hidden',
  },
  header: {
    padding: '14px 16px 0 16px',
    backgroundColor: '#111827',
    borderBottom: '1px solid #1f2937',
  },
  headerTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '10px',
  },
  targetType: {
    fontSize: '0.68rem',
    fontWeight: 800,
    letterSpacing: '0.08em',
    color: '#38bdf8',
  },
  title: {
    margin: '3px 0',
    fontSize: '1.1rem',
    fontWeight: 700,
    color: '#f8fafc',
  },
  targetId: {
    fontSize: '0.75rem',
    fontFamily: 'monospace',
    color: '#64748b',
  },
  confBadgeLarge: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '6px 12px',
    borderRadius: '6px',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    border: '1px solid #0284c7',
  },
  confNum: {
    fontSize: '1.25rem',
    fontWeight: 800,
    color: '#38bdf8',
  },
  confSub: {
    fontSize: '0.62rem',
    fontWeight: 700,
    letterSpacing: '0.06em',
    color: '#94a3b8',
  },
  tabRow: {
    display: 'flex',
    gap: '12px',
  },
  tabBtn: {
    padding: '8px 4px',
    background: 'transparent',
    border: 'none',
    fontSize: '0.8rem',
    fontWeight: 600,
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
    borderRadius: '6px',
    border: '1px solid #1e293b',
    backgroundColor: '#111827',
    padding: '10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  visualHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionLabel: {
    fontSize: '0.72rem',
    fontWeight: 800,
    letterSpacing: '0.06em',
    color: '#38bdf8',
  },
  visualSub: {
    fontSize: '0.7rem',
    color: '#64748b',
  },
  imageWrapper: {
    width: '100%',
    height: '180px',
    borderRadius: '4px',
    overflow: 'hidden',
    backgroundColor: '#0b1120',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  previewImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  dimsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '8px',
  },
  dimCard: {
    padding: '8px 10px',
    borderRadius: '6px',
    backgroundColor: '#111827',
    border: '1px solid #1e293b',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  dimKey: {
    fontSize: '0.68rem',
    fontWeight: 700,
    color: '#64748b',
    letterSpacing: '0.04em',
  },
  dimVal: {
    fontSize: '0.84rem',
    fontWeight: 600,
    color: '#f1f5f9',
  },
  dimSub: {
    fontSize: '0.7rem',
    color: '#94a3b8',
  },
  flagsRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
    marginTop: '2px',
  },
  flagBadge: {
    fontSize: '0.65rem',
    padding: '1px 5px',
    borderRadius: '3px',
    backgroundColor: '#1e293b',
    color: '#38bdf8',
    border: '1px solid #334155',
  },
  scoreBox: {
    padding: '12px',
    borderRadius: '6px',
    backgroundColor: '#111827',
    border: '1px solid #1e293b',
  },
  provenanceBox: {
    padding: '12px',
    borderRadius: '6px',
    backgroundColor: '#111827',
    border: '1px solid #1e293b',
  },
  scoreTitle: {
    margin: '0 0 10px 0',
    fontSize: '0.85rem',
    fontWeight: 700,
    color: '#f8fafc',
  },
  scoreList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  scoreRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.78rem',
    padding: '4px 0',
    borderBottom: '1px solid #1f2937',
  },
  scoreKey: {
    color: '#94a3b8',
    fontWeight: 600,
  },
  scoreVal: {
    color: '#f8fafc',
    fontFamily: 'monospace',
  },
  checksumVal: {
    color: '#38bdf8',
    fontFamily: 'monospace',
    fontSize: '0.7rem',
    maxWidth: '220px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  decisionCard: {
    padding: '12px',
    borderRadius: '6px',
    backgroundColor: '#111827',
    border: '1px solid #1e293b',
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
    fontSize: '0.75rem',
    fontWeight: 800,
    letterSpacing: '0.05em',
    color: '#f8fafc',
  },
  currentStatusBadge: {
    fontSize: '0.7rem',
    color: '#94a3b8',
    fontFamily: 'monospace',
  },
  decisionBtnGroup: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '8px',
  },
  actionBtn: {
    padding: '8px 6px',
    borderRadius: '6px',
    border: '1px solid',
    fontSize: '0.75rem',
    cursor: 'pointer',
    textAlign: 'center',
    transition: 'all 0.15s ease',
  },
  notesGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  notesLabel: {
    fontSize: '0.72rem',
    color: '#94a3b8',
    fontWeight: 600,
  },
  notesTextarea: {
    width: '100%',
    minHeight: '60px',
    padding: '8px',
    borderRadius: '4px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    color: '#f8fafc',
    fontSize: '0.78rem',
    resize: 'vertical',
  },
  submitBtn: {
    padding: '9px 12px',
    borderRadius: '6px',
    border: 'none',
    backgroundColor: '#0284c7',
    color: '#f8fafc',
    fontSize: '0.82rem',
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: '0.04em',
    transition: 'all 0.15s ease',
  },
  errorAlert: {
    padding: '6px 10px',
    borderRadius: '4px',
    backgroundColor: 'rgba(239, 68, 68, 0.2)',
    color: '#f87171',
    fontSize: '0.75rem',
    border: '1px solid #ef4444',
  },
  successAlert: {
    padding: '6px 10px',
    borderRadius: '4px',
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    color: '#34d399',
    fontSize: '0.75rem',
    border: '1px solid #10b981',
  },
  emptyContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    padding: '30px',
    textAlign: 'center',
    backgroundColor: '#0f172a',
    borderRadius: '8px',
    border: '1px solid #1e293b',
  },
  emptyIcon: {
    fontSize: '2.5rem',
    marginBottom: '12px',
  },
  emptyTitle: {
    margin: '0 0 6px 0',
    fontSize: '1rem',
    fontWeight: 700,
    color: '#f8fafc',
  },
  emptySub: {
    margin: 0,
    fontSize: '0.8rem',
    color: '#64748b',
    maxWidth: '280px',
    lineHeight: 1.4,
  },
};
