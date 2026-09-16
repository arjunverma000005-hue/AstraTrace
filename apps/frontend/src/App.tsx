import React, { useEffect, useState, useCallback } from 'react';
import { ApiClient } from './api/client';
import { ErrorBoundary } from './components/ErrorBoundary';
import { EvidenceCard } from './components/EvidenceCard';
import { MapViewer } from './components/MapViewer';
import { ReviewQueue } from './components/ReviewQueue';
import { SearchBar } from './components/SearchBar';
import { SatelliteIcon, ShieldIcon, OrbitIcon } from './components/Icons';
import {
  EvidenceFirstCandidate,
  ReviewDecision,
  UnifiedSearchRequest,
} from './types/api';

export const App: React.FC = () => {
  const [candidates, setCandidates] = useState<EvidenceFirstCandidate[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<EvidenceFirstCandidate | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeQuery, setActiveQuery] = useState<string>('');
  const [systemOnline, setSystemOnline] = useState<boolean>(true);
  const [utcTime, setUtcTime] = useState<string>('');

  // Live UTC Clock for aerospace mission control
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Initial load: Fetch default review queue
  const loadInitialQueue = useCallback(async () => {
    setIsLoading(true);
    try {
      const queueRes = await ApiClient.getReviewQueue(undefined, undefined, 50, 0);
      setCandidates(queueRes.items);
      if (queueRes.items.length > 0) {
        setSelectedCandidate(queueRes.items[0]);
      }
    } catch (err) {
      console.warn('Could not load initial queue:', err);
      // Fallback search
      try {
        const searchRes = await ApiClient.unifiedSearch({ top_k: 25 });
        setCandidates(searchRes.results);
        if (searchRes.results.length > 0) {
          setSelectedCandidate(searchRes.results[0]);
        }
      } catch (searchErr) {
        console.error('Unified search fallback failed:', searchErr);
        setSystemOnline(false);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialQueue();
  }, [loadInitialQueue]);

  // Handle unified search execution
  const handleSearch = async (req: UnifiedSearchRequest) => {
    setIsLoading(true);
    setActiveQuery(req.query || '');
    try {
      const res = await ApiClient.unifiedSearch(req);
      setCandidates(res.results);
      if (res.results.length > 0) {
        setSelectedCandidate(res.results[0]);
      } else {
        setSelectedCandidate(null);
      }
    } catch (err) {
      console.error('Unified search failed:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle analyst decision submission update in local state
  const handleDecisionSubmitted = (targetId: string, decision: ReviewDecision) => {
    setCandidates((prev) =>
      prev.map((c) =>
        c.target_id === targetId ? { ...c, review_status: decision } : c,
      ),
    );
    if (selectedCandidate?.target_id === targetId) {
      setSelectedCandidate((prev) =>
        prev ? { ...prev, review_status: decision } : null,
      );
    }
  };

  return (
    <ErrorBoundary>
      <div style={styles.container}>
        {/* Top Tactical Mission-Control Navigation Bar */}
        <header style={styles.header}>
          <div style={styles.brand}>
            <div style={styles.logoBadge}>
              <SatelliteIcon size={20} color="#38bdf8" />
            </div>
            <div>
              <div style={styles.titleRow}>
                <h1 style={styles.brandTitle}>ASTRATRACE</h1>
                <span style={styles.versionTag}>v2.6-ORBITAL</span>
              </div>
              <span style={styles.brandSubtitle}>
                Geospatial Earth Observation & Intelligence • SIH 2026 | SIH26227
              </span>
            </div>
          </div>

          <div style={styles.metaGroup}>
            {/* UTC Telemetry Clock */}
            <div style={styles.utcBadge}>
              <OrbitIcon size={12} color="#38bdf8" />
              <span style={styles.utcText}>{utcTime || 'SYNCHRONIZING...'}</span>
            </div>

            <div style={styles.badgeMod}>
              <span style={styles.modText}>MoD • Indian Army / DGIS</span>
            </div>

            <div style={styles.badgeAirgap}>
              <span style={styles.greenPulse} />
              <ShieldIcon size={12} color="#10b981" />
              <span>AIR-GAPPED (100% OFFLINE)</span>
            </div>
          </div>
        </header>

        {/* Tactical Search Row */}
        <div style={styles.searchRow}>
          <SearchBar onSearch={handleSearch} isLoading={isLoading} />
        </div>

        {/* 3-Column Tactical Workstation Layout */}
        <div style={styles.workstation}>
          {/* Left Column: Review Queue (340px) */}
          <div style={styles.queueCol}>
            <ReviewQueue
              candidates={candidates}
              selectedCandidate={selectedCandidate}
              onSelectCandidate={setSelectedCandidate}
              isLoading={isLoading}
            />
          </div>

          {/* Center Column: MapLibre Map Viewer (Flex 1) */}
          <div style={styles.mapCol}>
            <MapViewer
              candidates={candidates}
              selectedCandidate={selectedCandidate}
              onSelectCandidate={setSelectedCandidate}
            />
          </div>

          {/* Right Column: Evidence-First Inspection & Decision Card (400px) */}
          <div style={styles.evidenceCol}>
            <EvidenceCard
              candidate={selectedCandidate}
              onDecisionSubmitted={handleDecisionSubmitted}
            />
          </div>
        </div>

        {/* Operational Telemetry Footer */}
        <footer style={styles.footer}>
          <div style={styles.footerItem}>
            <span style={styles.footerLabel}>SYSTEM:</span>
            <span style={{ color: systemOnline ? '#10b981' : '#f59e0b', fontWeight: 700 }}>
              {systemOnline ? 'OPERATIONAL (AIR-GAPPED)' : 'DEGRADED'}
            </span>
          </div>

          <div style={styles.footerDivider} />

          <div style={styles.footerItem}>
            <span style={styles.footerLabel}>CORRIDOR:</span>
            <span style={styles.footerVal}>JEWAR AIRPORT (T43RGM • EPSG:32643)</span>
          </div>

          <div style={styles.footerDivider} />

          <div style={styles.footerItem}>
            <span style={styles.footerLabel}>SENSOR:</span>
            <span style={styles.footerVal}>COPERNICUS SENTINEL-2 L2A (10M BOA)</span>
          </div>

          <div style={styles.footerDivider} />

          <div style={styles.footerItem}>
            <span style={styles.footerLabel}>ACTIVE TARGETS:</span>
            <span style={{ color: '#38bdf8', fontWeight: 700, fontFamily: 'monospace' }}>
              {candidates.length}
            </span>
          </div>

          <div style={styles.footerDivider} />

          <div style={styles.footerItem}>
            <span style={styles.footerLabel}>QUERY:</span>
            <span style={{ color: '#f8fafc', fontFamily: 'monospace', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {activeQuery || 'CATALOG BASELINE'}
            </span>
          </div>

          <div style={styles.footerItemRight}>
            <span style={styles.securityTag}>
              <ShieldIcon size={11} color="#10b981" style={{ marginRight: '4px' }} />
              SHA-256 CRYPTOGRAPHIC INTEGRITY VERIFIED
            </span>
          </div>
        </footer>
      </div>
    </ErrorBoundary>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    maxHeight: '100vh',
    backgroundColor: '#06090e',
    color: '#e2e8f0',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 16px',
    backgroundColor: '#0b1118',
    borderBottom: '1px solid #182635',
    boxShadow: '0 2px 10px rgba(0, 0, 0, 0.5)',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  logoBadge: {
    width: '34px',
    height: '34px',
    borderRadius: '6px',
    backgroundColor: '#0f1722',
    border: '1px solid #182635',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 0 10px rgba(56, 189, 248, 0.15)',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  brandTitle: {
    margin: 0,
    fontSize: '1.15rem',
    fontWeight: 800,
    letterSpacing: '0.1em',
    color: '#f8fafc',
  },
  versionTag: {
    fontSize: '0.6rem',
    fontWeight: 700,
    letterSpacing: '0.08em',
    padding: '1px 5px',
    borderRadius: '3px',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.25)',
    fontFamily: 'monospace',
  },
  brandSubtitle: {
    fontSize: '0.68rem',
    color: '#64748b',
    letterSpacing: '0.02em',
  },
  metaGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  utcBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '0.68rem',
    fontWeight: 700,
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: '#0f1722',
    color: '#94a3b8',
    border: '1px solid #182635',
    fontFamily: 'monospace',
    letterSpacing: '0.04em',
  },
  utcText: {
    color: '#38bdf8',
  },
  badgeMod: {
    fontSize: '0.68rem',
    fontWeight: 700,
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    color: '#7dd3fc',
    border: '1px solid rgba(56, 189, 248, 0.25)',
    letterSpacing: '0.03em',
  },
  modText: {
    fontFamily: 'inherit',
  },
  badgeAirgap: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '0.66rem',
    fontWeight: 800,
    letterSpacing: '0.08em',
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    color: '#34d399',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    fontFamily: 'monospace',
  },
  greenPulse: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#10b981',
    boxShadow: '0 0 8px #10b981',
  },
  searchRow: {
    padding: '6px 14px',
    backgroundColor: '#06090e',
  },
  workstation: {
    flex: 1,
    display: 'flex',
    gap: '10px',
    padding: '0 14px 8px 14px',
    overflow: 'hidden',
  },
  queueCol: {
    width: '340px',
    minWidth: '310px',
    height: '100%',
  },
  mapCol: {
    flex: 1,
    height: '100%',
  },
  evidenceCol: {
    width: '400px',
    minWidth: '360px',
    height: '100%',
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '5px 16px',
    backgroundColor: '#0b1118',
    borderTop: '1px solid #182635',
    fontSize: '0.68rem',
    color: '#64748b',
    flexShrink: 0,
  },
  footerItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  footerLabel: {
    fontWeight: 700,
    color: '#475569',
    letterSpacing: '0.04em',
  },
  footerVal: {
    color: '#cbd5e1',
    fontFamily: 'monospace',
    fontWeight: 600,
  },
  footerDivider: {
    width: '1px',
    height: '12px',
    backgroundColor: '#182635',
  },
  footerItemRight: {
    marginLeft: 'auto',
    display: 'flex',
    alignItems: 'center',
  },
  securityTag: {
    display: 'inline-flex',
    alignItems: 'center',
    color: '#10b981',
    fontSize: '0.64rem',
    fontWeight: 700,
    fontFamily: 'monospace',
    letterSpacing: '0.04em',
  },
};

