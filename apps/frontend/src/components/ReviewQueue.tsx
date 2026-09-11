import React, { useState } from 'react';
import { EvidenceFirstCandidate, ReviewDecision } from '../types/api';
import { ListIcon } from './Icons';

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
        return { label: 'CONFIRMED', bg: 'rgba(16, 185, 129, 0.2)', color: '#10b981' };
      case 'REJECTED':
        return { label: 'REJECTED', bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444' };
      case 'FLAGGED_FOR_INSPECTION':
        return { label: 'FLAGGED', bg: 'rgba(245, 158, 11, 0.2)', color: '#f59e0b' };
      default:
        return { label: 'PENDING', bg: 'rgba(59, 130, 246, 0.15)', color: '#38bdf8' };
    }
  };

  const getQualityBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case 'USABLE':
        return { bg: '#064e3b', color: '#34d399' };
      case 'DEGRADED':
        return { bg: '#451a03', color: '#fbbf24' };
      case 'UNRELIABLE':
      case 'INSUFFICIENT':
        return { bg: '#450a0a', color: '#f87171' };
      default:
        return { bg: '#1e293b', color: '#94a3b8' };
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerTop}>
          <div style={styles.titleGroup}>
            <span style={styles.queueIcon}><ListIcon size={18} color="#38bdf8" /></span>
            <h3 style={styles.title}>Analyst Review Queue</h3>
          </div>
          <span style={styles.totalBadge}>{candidates.length} Targets</span>
        </div>

        {/* Filter Tabs */}
        <div style={styles.tabsRow}>
          {(['ALL', 'PENDING', 'CONFIRMED', 'FLAGGED', 'REJECTED'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setFilterTab(tab)}
              style={{
                ...styles.tabBtn,
                borderBottom: filterTab === tab ? '2px solid #38bdf8' : '2px solid transparent',
                color: filterTab === tab ? '#f8fafc' : '#94a3b8',
                backgroundColor: filterTab === tab ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
              }}
            >
              {tab} ({counts[tab]})
            </button>
          ))}
        </div>
      </div>

      {/* Queue Item List */}
      <div style={styles.listContainer}>
        {isLoading ? (
          <div style={styles.emptyState}>
            <span style={styles.spinner}>⏳</span>
            <span>Querying catalog and evaluating quality gate...</span>
          </div>
        ) : filteredCandidates.length === 0 ? (
          <div style={styles.emptyState}>
            <span>No targets matching current filter ({filterTab}).</span>
          </div>
        ) : (
          filteredCandidates.map((c) => {
            const isSelected = selectedCandidate?.candidate_id === c.candidate_id;
            const statusInfo = getStatusBadge(c.review_status);
            const qualInfo = getQualityBadge(c.quality_status);

            return (
              <div
                key={c.candidate_id}
                onClick={() => onSelectCandidate(c)}
                style={{
                  ...styles.card,
                  borderColor: isSelected ? '#facc15' : '#1e293b',
                  backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.12)' : '#111827',
                }}
              >
                {/* Top Row: Rank & Badges */}
                <div style={styles.cardHeader}>
                  <div style={styles.rankGroup}>
                    <span style={styles.rankNum}>#{c.rank}</span>
                    <span style={styles.targetTypeBadge}>{c.target_type}</span>
                  </div>
                  <div style={styles.badgeRow}>
                    <span style={{ ...styles.badge, backgroundColor: qualInfo.bg, color: qualInfo.color }}>
                      {c.quality_status}
                    </span>
                    <span style={{ ...styles.badge, backgroundColor: statusInfo.bg, color: statusInfo.color }}>
                      {statusInfo.label}
                    </span>
                  </div>
                </div>

                {/* Main Content */}
                <div style={styles.cardWhat}>{c.what}</div>
                <div style={styles.targetId}>{c.target_id}</div>

                {/* Metrics Row */}
                <div style={styles.metricsRow}>
                  <div style={styles.confMeter}>
                    <div style={styles.confLabel}>
                      <span>Confidence</span>
                      <span style={styles.confValue}>{(c.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div style={styles.meterTrack}>
                      <div
                        style={{
                          ...styles.meterFill,
                          width: `${Math.round(c.confidence * 100)}%`,
                          backgroundColor: c.confidence >= 0.7 ? '#10b981' : c.confidence >= 0.4 ? '#f59e0b' : '#ef4444',
                        }}
                      />
                    </div>
                  </div>
                  <div style={styles.dateLabel}>
                    {c.when ? (
                      c.when.includes(' to ')
                        ? c.when.split(' to ').map(d => new Date(d.trim()).toLocaleDateString('en-GB')).join(' → ')
                        : new Date(c.when).toLocaleDateString('en-GB')
                    ) : 'Unknown Date'}
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
    backgroundColor: '#0f172a',
    borderRadius: '8px',
    border: '1px solid #1e293b',
    overflow: 'hidden',
  },
  header: {
    padding: '12px 14px 0 14px',
    backgroundColor: '#111827',
    borderBottom: '1px solid #1f2937',
  },
  headerTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  titleGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  queueIcon: {
    fontSize: '1.2rem',
  },
  title: {
    margin: 0,
    fontSize: '0.95rem',
    fontWeight: 700,
    letterSpacing: '0.04em',
    color: '#f8fafc',
  },
  totalBadge: {
    fontSize: '0.72rem',
    fontWeight: 600,
    padding: '2px 8px',
    borderRadius: '12px',
    backgroundColor: '#1e293b',
    color: '#38bdf8',
    border: '1px solid #334155',
  },
  tabsRow: {
    display: 'flex',
    gap: '4px',
    overflowX: 'auto',
  },
  tabBtn: {
    padding: '6px 10px',
    fontSize: '0.75rem',
    fontWeight: 600,
    border: 'none',
    cursor: 'pointer',
    borderRadius: '4px 4px 0 0',
    whiteSpace: 'nowrap',
    transition: 'all 0.15s ease',
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
    border: '1px solid #1e293b',
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
    fontSize: '0.8rem',
    fontWeight: 800,
    color: '#38bdf8',
  },
  targetTypeBadge: {
    fontSize: '0.65rem',
    fontWeight: 700,
    padding: '1px 5px',
    borderRadius: '3px',
    backgroundColor: '#1e293b',
    color: '#94a3b8',
  },
  badgeRow: {
    display: 'flex',
    gap: '6px',
  },
  badge: {
    fontSize: '0.68rem',
    fontWeight: 700,
    padding: '2px 6px',
    borderRadius: '4px',
    letterSpacing: '0.03em',
  },
  cardWhat: {
    fontSize: '0.86rem',
    fontWeight: 600,
    color: '#f1f5f9',
    lineHeight: 1.3,
  },
  targetId: {
    fontSize: '0.72rem',
    fontFamily: 'monospace',
    color: '#64748b',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  metricsRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '4px',
    paddingTop: '6px',
    borderTop: '1px solid #1f2937',
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
    fontSize: '0.68rem',
    color: '#94a3b8',
    fontWeight: 600,
  },
  confValue: {
    color: '#f8fafc',
  },
  meterTrack: {
    height: '4px',
    backgroundColor: '#1e293b',
    borderRadius: '2px',
    overflow: 'hidden',
  },
  meterFill: {
    height: '100%',
    borderRadius: '2px',
  },
  dateLabel: {
    fontSize: '0.7rem',
    color: '#64748b',
  },
  emptyState: {
    padding: '30px',
    textAlign: 'center',
    color: '#64748b',
    fontSize: '0.85rem',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '10px',
  },
  spinner: {
    fontSize: '1.5rem',
  },
};
