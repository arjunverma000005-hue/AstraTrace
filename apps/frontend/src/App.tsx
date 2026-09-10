import React, { useEffect, useState, useCallback } from 'react';
import { ApiClient } from './api/client';
import { ErrorBoundary } from './components/ErrorBoundary';
import { EvidenceCard } from './components/EvidenceCard';
import { MapViewer } from './components/MapViewer';
import { ReviewQueue } from './components/ReviewQueue';
import { SearchBar } from './components/SearchBar';
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
        {/* Top Operational Navigation Bar */}
        <header style={styles.header}>
          <div style={styles.brand}>
            <span style={styles.logoIcon}>🛰️</span>
            <div>
              <h1 style={styles.brandTitle}>ASTRATRACE</h1>
              <span style={styles.brandSubtitle}>
                Geospatial Intelligence Platform • Tactical Analyst Console
              </span>
            </div>
          </div>

          <div style={styles.metaGroup}>
            <div style={styles.badgeSih}>SIH 2026 • SIH26227</div>
            <div style={styles.badgeMod}>Ministry of Defence • Indian Army, DGIS</div>
            <div style={styles.badgeAirgap}>
              <span style={styles.greenPulse} />
              <span>AIR-GAPPED (100% OFFLINE)</span>
            </div>
          </div>
        </header>

        {/* Search Bar Row */}
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

          {/* Right Column: Evidence-First Inspection & Decision Card (380px) */}
          <div style={styles.evidenceCol}>
            <EvidenceCard
              candidate={selectedCandidate}
              onDecisionSubmitted={handleDecisionSubmitted}
            />
          </div>
        </div>

        {/* Operational Status Footer */}
        <footer style={styles.footer}>
          <div style={styles.footerItem}>
            <span>Status:</span>
            <span style={{ color: systemOnline ? '#10b981' : '#f59e0b', fontWeight: 600 }}>
              {systemOnline ? 'OPERATIONAL' : 'DEGRADED'}
            </span>
          </div>
          <div style={styles.footerItem}>
            <span>Active Query:</span>
            <span style={{ color: '#f8fafc', fontFamily: 'monospace' }}>
              {activeQuery || '(All Catalog Observations)'}
            </span>
          </div>
          <div style={styles.footerItem}>
            <span>Active Targets:</span>
            <span style={{ color: '#38bdf8', fontWeight: 700 }}>{candidates.length}</span>
          </div>
          <div style={styles.footerItemRight}>
            <span>Milestone 8 • Offline MapLibre & Evidence-First Decision Persistence</span>
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
    backgroundColor: '#0b0f19',
    color: '#e2e8f0',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 20px',
    backgroundColor: '#0f172a',
    borderBottom: '1px solid #1e293b',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  logoIcon: {
    fontSize: '1.8rem',
  },
  brandTitle: {
    margin: 0,
    fontSize: '1.25rem',
    fontWeight: 800,
    letterSpacing: '0.08em',
    color: '#f8fafc',
  },
  brandSubtitle: {
    fontSize: '0.72rem',
    color: '#94a3b8',
    letterSpacing: '0.02em',
  },
  metaGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  badgeSih: {
    fontSize: '0.7rem',
    fontWeight: 700,
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: '#1e293b',
    color: '#f8fafc',
    border: '1px solid #334155',
  },
  badgeMod: {
    fontSize: '0.7rem',
    fontWeight: 700,
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: 'rgba(2, 132, 199, 0.15)',
    color: '#38bdf8',
    border: '1px solid #0284c7',
  },
  badgeAirgap: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '0.68rem',
    fontWeight: 800,
    letterSpacing: '0.06em',
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    color: '#34d399',
    border: '1px solid #10b981',
  },
  greenPulse: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#10b981',
    boxShadow: '0 0 6px #10b981',
  },
  searchRow: {
    padding: '8px 14px',
    backgroundColor: '#0b1120',
  },
  workstation: {
    flex: 1,
    display: 'flex',
    gap: '10px',
    padding: '0 14px 10px 14px',
    overflow: 'hidden',
  },
  queueCol: {
    width: '330px',
    minWidth: '300px',
    height: '100%',
  },
  mapCol: {
    flex: 1,
    height: '100%',
  },
  evidenceCol: {
    width: '380px',
    minWidth: '340px',
    height: '100%',
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
    padding: '6px 16px',
    backgroundColor: '#0f172a',
    borderTop: '1px solid #1e293b',
    fontSize: '0.73rem',
    color: '#94a3b8',
  },
  footerItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  footerItemRight: {
    marginLeft: 'auto',
    color: '#64748b',
    fontSize: '0.7rem',
  },
};
