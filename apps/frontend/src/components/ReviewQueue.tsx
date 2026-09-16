import React, { useState } from 'react';
import { EvidenceFirstCandidate, ReviewDecision } from '../types/api';
import { ListIcon, SpinnerIcon, RadarIcon, ShieldIcon, CalendarIcon, TargetIcon } from './Icons';

interface ReviewQueueProps {
  candidates: EvidenceFirstCandidate[];
  selectedCandidate: EvidenceFirstCandidate | null;
  onSelectCandidate: (candidate: EvidenceFirstCandidate) => void;
  isLoading: boolean;
}

export const ReviewQueue: React.FC<ReviewQueueProps> = ({
  candidates,
  selectedCandidate,
  onSelectCandidate,
  isLoading,
}) => {
  const [filterTab, setFilterTab] = useState<string>('ALL');

  // Compute status counts
  const counts = {
    ALL: candidates.length,
    PENDING: candidates.filter((c) => c.review_status === 'PENDING_REVIEW').length,
    CONFIRMED: candidates.filter((c) => c.review_status === 'CONFIRMED').length,
    FLAGGED: candidates.filter((c) => c.review_status === 'FLAGGED_FOR_INSPECTION').length,
    REJECTED: candidates.filter((c) => c.review_status === 'REJECTED').length,
  };

  const filteredCandidates = candidates.filter((c) => {
    if (filterTab === 'ALL') return true;
    if (filterTab === 'PENDING') return c.review_status === 'PENDING_REVIEW';
    if (filterTab === 'CONFIRMED') return c.review_status === 'CONFIRMED';
    if (filterTab === 'FLAGGED') return c.review_status === 'FLAGGED_FOR_INSPECTION';
    if (filterTab === 'REJECTED') return c.review_status === 'REJECTED';
    return true;
  });

  const getStatusBadge = (status: ReviewDecision) => {
    switch (status) {
      case 'CONFIRMED':
        return { label: 'CONFIRMED', bg: 'rgba(16, 185, 129, 0.15)', border: '#10b981', color: '#10b981' };
      case 'REJECTED':
        return { label: 'REJECTED', bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', color: '#ef4444' };
      case 'FLAGGED_FOR_INSPECTION':
        return { label: 'FLAGGED', bg: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', color: '#f59e0b' };
      default:
        return { label: 'PENDING', bg: 'rgba(56, 189, 248, 0.12)', border: '#38bdf8', color: '#38bdf8' };
    }
  };

  const getQualityBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'USABLE':
        return { bg: 'rgba(16, 185, 129, 0.15)', border: '#10b981', color: '#34d399' };
      case 'DEGRADED':
        return { bg: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', color: '#fbbf24' };
      case 'UNRELIABLE':
      case 'INSUFFICIENT':
        return { bg: 'rgba(239, 68, 68, 0.15)', border: '#ef4444', color: '#f87171' };
      default:
        return { bg: '#182635', border: '#22374c', color: '#94a3b8' };
    }
  };

  return (
    <div style={styles.container}>
      {/* Tactical Queue Header */}
      <div style={styles.header}>
        <div style={styles.headerTop}>
          <div style={styles.titleGroup}>
            <ListIcon size={16} color="#38bdf8" />
            <h3 style={styles.title}>ANALYST REVIEW QUEUE</h3>
          </div>
          <span style={styles.totalBadge}>{candidates.length} CANDIDATES</span>
        </div>

        {/* Segmented Filter Tabs */}
        <div style={styles.tabsRow}>
          {(['ALL', 'PENDING', 'CONFIRMED', 'FLAGGED', 'REJECTED'] as const).map((tab) => {
            const isActive = filterTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setFilterTab(tab)}
                style={{
                  ...styles.tabBtn,
                  color: isActive ? '#38bdf8' : '#64748b',
                  borderBottom: isActive ? '2px solid #38bdf8' : '2px solid transparent',
                  backgroundColor: isActive ? 'rgba(56, 189, 248, 0.08)' : 'transparent',
                }}
              >
                <span>{tab}</span>
                <span style={{
                  ...styles.tabCount,
                  backgroundColor: isActive ? 'rgba(56, 189, 248, 0.25)' : '#182635',
                  color: isActive ? '#38bdf8' : '#94a3b8',
                }}>
                  {counts[tab]}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Queue Card List */}
      <div style={styles.listContainer}>
        {isLoading ? (
          <div style={styles.loadingState}>
            <SpinnerIcon size={24} color="#38bdf8" />
            <span style={styles.loadingText}>EVALUATING SENTINEL-2 TILES & QUALITY GATE...</span>
          </div>
        ) : filteredCandidates.length === 0 ? (
          <div style={styles.emptyState}>
            <RadarIcon size={32} color="#334155" />
            <span style={styles.emptyTitle}>NO TARGETS IN CURRENT FILTER</span>
            <span style={styles.emptySubtitle}>No candidate observations matching filter ({filterTab}).</span>
          </div>
        ) : (
          filteredCandidates.map((c) => {
            const isSelected = selectedCandidate?.target_id === c.target_id || selectedCandidate?.candidate_id === c.candidate_id;
            const statusInfo = getStatusBadge(c.review_status);
            const qualInfo = getQualityBadge(c.quality_status);

            return (
              <div
                key={c.target_id || c.candidate_id}
                onClick={() => onSelectCandidate(c)}
                style={{
                  ...styles.card,
                  borderColor: isSelected ? '#38bdf8' : '#182635',
                  backgroundColor: isSelected ? 'rgba(17, 28, 41, 0.95)' : 'rgba(11, 17, 24, 0.85)',
                  borderLeft: isSelected ? '3px solid #38bdf8' : '3px solid transparent',
                  boxShadow: isSelected ? '0 0 16px rgba(56, 189, 248, 0.12)' : 'none',
                }}
              >
                {/* Top Row: Rank & Badges */}
                <div style={styles.cardHeader}>
                  <div style={styles.rankGroup}>
                    <span style={styles.rankNum}>#{c.rank ? String(c.rank).padStart(2, '0') : '01'}</span>
                    <span style={styles.targetTypeBadge}>{c.target_type}</span>
                    <span style={styles.sensorBadge}>SENTINEL-2</span>
                  </div>
                  <div style={styles.badgeRow}>
                    <span style={{ ...styles.badge, backgroundColor: qualInfo.bg, borderColor: qualInfo.border, color: qualInfo.color }}>
                      <ShieldIcon size={10} color={qualInfo.color} style={{ marginRight: '3px' }} />
                      {c.quality_status}
                    </span>
                    <span style={{ ...styles.badge, backgroundColor: statusInfo.bg, borderColor: statusInfo.border, color: statusInfo.color }}>
                      {statusInfo.label}
                    </span>
                  </div>
                </div>

                {/* Primary Headline */}
                <div style={styles.cardWhat}>
                  <TargetIcon size={13} color="#38bdf8" style={{ marginRight: '6px', flexShrink: 0 }} />
                  <span>{c.what}</span>
                </div>

                {/* Tactical Target Identifier */}
                <div style={styles.targetId}>
                  <span style={{ color: '#475569' }}>REF:</span> {c.target_id}
                </div>

                {/* Metrics Row: Confidence Meter & Observation Epoch */}
                <div style={styles.metricsRow}>
                  <div style={styles.confMeter}>
                    <div style={styles.confLabel}>
                      <span>CONFIDENCE</span>
                      <span style={styles.confValue}>{(c.confidence * 100).toFixed(1)}%</span>
                    </div>
                    <div style={styles.meterTrack}>
                      <div
                        style={{
                          ...styles.meterFill,
                          width: `${Math.min(100, Math.round(c.confidence * 100))}%`,
                          backgroundColor: c.confidence >= 0.7 ? '#10b981' : c.confidence >= 0.5 ? '#f59e0b' : '#38bdf8',
                        }}
                      />
                    </div>
                  </div>

                  <div style={styles.dateLabel}>
                    <CalendarIcon size={11} color="#64748b" style={{ marginRight: '4px' }} />
                    <span>
                      {c.when ? (
                        c.when.includes(' to ')
                          ? c.when.split(' to ').map(d => new Date(d.trim()).toISOString().slice(0, 10)).join(' → ')
                          : new Date(c.when).toISOString().slice(0, 10)
                      ) : '2023-02-03'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
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
    backgroundColor: 'rgba(11, 17, 24, 0.94)',
    backdropFilter: 'blur(10px)',
    borderRadius: '8px',
    border: '1px solid #182635',
    overflow: 'hidden',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
  },
  header: {
    padding: '12px 14px 0 14px',
    backgroundColor: '#06090e',
    borderBottom: '1px solid #182635',
  },
  headerTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  titleGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  title: {
    margin: 0,
    fontSize: '0.78rem',
    fontWeight: 800,
    letterSpacing: '0.08em',
    color: '#f8fafc',
  },
  totalBadge: {
    fontSize: '0.66rem',
    fontWeight: 700,
    fontFamily: 'var(--font-mono, monospace)',
    padding: '2px 8px',
    borderRadius: '10px',
    backgroundColor: '#0f1722',
    color: '#38bdf8',
    border: '1px solid #182635',
  },
  tabsRow: {
    display: 'flex',
    gap: '2px',
    overflowX: 'auto',
  },
  tabBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    padding: '7px 9px',
    fontSize: '0.68rem',
    fontWeight: 700,
    border: 'none',
    cursor: 'pointer',
    borderRadius: '4px 4px 0 0',
    whiteSpace: 'nowrap',
    letterSpacing: '0.04em',
    transition: 'all 0.15s ease',
  },
  tabCount: {
    fontFamily: 'var(--font-mono, monospace)',
    fontSize: '0.62rem',
    padding: '1px 5px',
    borderRadius: '8px',
  },
  listContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  card: {
    padding: '10px 12px',
    borderRadius: '6px',
    border: '1px solid #182635',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  rankGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  rankNum: {
    fontSize: '0.75rem',
    fontWeight: 800,
    fontFamily: 'var(--font-mono, monospace)',
    color: '#38bdf8',
  },
  targetTypeBadge: {
    fontSize: '0.60rem',
    fontWeight: 700,
    fontFamily: 'var(--font-mono, monospace)',
    padding: '1px 5px',
    borderRadius: '3px',
    backgroundColor: '#06090e',
    color: '#94a3b8',
    border: '1px solid #182635',
  },
  sensorBadge: {
    fontSize: '0.58rem',
    fontWeight: 700,
    fontFamily: 'var(--font-mono, monospace)',
    padding: '1px 4px',
    borderRadius: '3px',
    backgroundColor: 'rgba(99, 102, 241, 0.15)',
    color: '#818cf8',
    border: '1px solid rgba(99, 102, 241, 0.3)',
  },
  badgeRow: {
    display: 'flex',
    gap: '5px',
  },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    fontSize: '0.62rem',
    fontWeight: 700,
    fontFamily: 'var(--font-mono, monospace)',
    padding: '2px 6px',
    borderRadius: '3px',
    border: '1px solid transparent',
    letterSpacing: '0.04em',
  },
  cardWhat: {
    display: 'flex',
    alignItems: 'flex-start',
    fontSize: '0.80rem',
    fontWeight: 700,
    color: '#f8fafc',
    lineHeight: 1.3,
  },
  targetId: {
    fontSize: '0.68rem',
    fontFamily: 'var(--font-mono, monospace)',
    color: '#64748b',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  metricsRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '2px',
    paddingTop: '6px',
    borderTop: '1px solid #182635',
  },
  confMeter: {
    display: 'flex',
    flexDirection: 'column',
    gap: '3px',
    width: '120px',
  },
  confLabel: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.64rem',
    fontWeight: 700,
    letterSpacing: '0.04em',
    color: '#94a3b8',
  },
  confValue: {
    fontFamily: 'var(--font-mono, monospace)',
    color: '#f8fafc',
  },
  meterTrack: {
    height: '4px',
    backgroundColor: '#06090e',
    borderRadius: '2px',
    overflow: 'hidden',
    border: '1px solid #182635',
  },
  meterFill: {
    height: '100%',
    borderRadius: '2px',
    transition: 'width 0.3s ease',
  },
  dateLabel: {
    display: 'inline-flex',
    alignItems: 'center',
    fontSize: '0.68rem',
    fontFamily: 'var(--font-mono, monospace)',
    color: '#94a3b8',
  },
  loadingState: {
    padding: '40px 20px',
    textAlign: 'center',
    color: '#64748b',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
  },
  loadingText: {
    fontSize: '0.70rem',
    fontWeight: 700,
    letterSpacing: '0.05em',
    color: '#94a3b8',
  },
  emptyState: {
    padding: '40px 20px',
    textAlign: 'center',
    color: '#64748b',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px',
  },
  emptyTitle: {
    fontSize: '0.75rem',
    fontWeight: 800,
    letterSpacing: '0.06em',
    color: '#cbd5e1',
  },
  emptySubtitle: {
    fontSize: '0.70rem',
    color: '#64748b',
  },
};

