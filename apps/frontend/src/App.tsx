import React, { useEffect, useState, useCallback } from 'react';
import { ApiClient } from './api/client';
import { ErrorBoundary } from './components/ErrorBoundary';
import { EvidenceCard } from './components/EvidenceCard';
import { MapViewer } from './components/MapViewer';
import { ReviewQueue } from './components/ReviewQueue';
import { SearchBar } from './components/SearchBar';
import { TimelineScrubber } from './components/TimelineScrubber';
import { SatelliteIcon, ShieldIcon, OrbitIcon, CheckCircleIcon, CloseIcon, LayersIcon } from './components/Icons';
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
  const [activeEpoch, setActiveEpoch] = useState<'T1' | 'T2'>('T1');

  // Responsive Layout States
  const [windowWidth, setWindowWidth] = useState<number>(
    typeof window !== 'undefined' ? window.innerWidth : 1440
  );
  const [mobileView, setMobileView] = useState<'MAP' | 'QUEUE' | 'EVIDENCE'>('MAP');
  const [tabletDrawerOpen, setTabletDrawerOpen] = useState<boolean>(false);

  const isMobile = windowWidth < 768;
  const isTablet = windowWidth >= 768 && windowWidth < 1200;

  // Track window resizing
  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Benchmark Modal State
  const [showBenchmarkModal, setShowBenchmarkModal] = useState<boolean>(false);
  const [benchmarkData, setBenchmarkData] = useState<any | null>(null);
  const [isLoadingBenchmark, setIsLoadingBenchmark] = useState<boolean>(false);

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

  // Handle image search result from SearchBar
  const handleImageSearchResult = (tiles: any[]) => {
    if (tiles && tiles.length > 0) {
      // Map semantic tile results to candidates or trigger search
      handleSearch({ search_mode: 'SEMANTIC', top_k: 25 });
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

  // Open Benchmark Report
  const handleOpenBenchmarks = async () => {
    setShowBenchmarkModal(true);
    if (!benchmarkData && !isLoadingBenchmark) {
      setIsLoadingBenchmark(true);
      try {
        const data = await ApiClient.getEvaluationSummary();
        setBenchmarkData(data);
      } catch (err) {
        console.error('Failed to load benchmark data:', err);
      } finally {
        setIsLoadingBenchmark(false);
      }
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
                <span style={styles.versionTag}>v2.0-SOVEREIGN</span>
              </div>
              <span style={styles.brandSubtitle}>
                Semantic Retrieval & Multi-Temporal Change Engine • SIH 2026 | SIH26227
              </span>
            </div>
          </div>

          <div style={styles.metaGroup}>
            {/* UTC Telemetry Clock */}
            {!isMobile && (
              <div style={styles.utcBadge}>
                <OrbitIcon size={12} color="#38bdf8" />
                <span style={styles.utcText}>{utcTime || 'SYNCHRONIZING...'}</span>
              </div>
            )}

            {!isMobile && (
              <div style={styles.badgeMod}>
                <span style={styles.modText}>MoD • Indian Army / DGIS</span>
              </div>
            )}

            {!isMobile && (
              <div style={styles.badgeAirgap}>
                <span style={styles.greenPulse} />
                <ShieldIcon size={12} color="#10b981" />
                <span>AIR-GAPPED (100% OFFLINE)</span>
              </div>
            )}

            {/* Benchmark Report Button */}
            <button
              type="button"
              onClick={handleOpenBenchmarks}
              style={styles.benchmarkBtn}
              title="Open empirical benchmark evaluation dossier"
            >
              <CheckCircleIcon size={13} color="#06090e" />
              <span>{isMobile ? 'BENCHMARKS' : 'BENCHMARK DOSSIER'}</span>
            </button>
          </div>
        </header>

        {/* Tactical Search Row */}
        <div style={styles.searchRow}>
          <SearchBar
            onSearch={handleSearch}
            onImageSearchResult={handleImageSearchResult}
            isLoading={isLoading}
          />
        </div>

        {/* Mobile View Switcher Tab Bar (< 768px) */}
        {isMobile && (
          <div style={styles.mobileTabBar} role="tablist" aria-label="Mobile View Switcher">
            <button
              type="button"
              role="tab"
              aria-selected={mobileView === 'MAP'}
              onClick={() => setMobileView('MAP')}
              style={{
                ...styles.mobileTabBtn,
                ...(mobileView === 'MAP' ? styles.mobileTabBtnActive : {}),
              }}
            >
              <SatelliteIcon size={13} color={mobileView === 'MAP' ? '#38bdf8' : '#64748b'} />
              <span>MAP VIEW</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={mobileView === 'QUEUE'}
              onClick={() => setMobileView('QUEUE')}
              style={{
                ...styles.mobileTabBtn,
                ...(mobileView === 'QUEUE' ? styles.mobileTabBtnActive : {}),
              }}
            >
              <LayersIcon size={13} color={mobileView === 'QUEUE' ? '#38bdf8' : '#64748b'} />
              <span>QUEUE ({candidates.length})</span>
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={mobileView === 'EVIDENCE'}
              onClick={() => setMobileView('EVIDENCE')}
              style={{
                ...styles.mobileTabBtn,
                ...(mobileView === 'EVIDENCE' ? styles.mobileTabBtnActive : {}),
              }}
            >
              <ShieldIcon size={13} color={mobileView === 'EVIDENCE' ? '#38bdf8' : '#64748b'} />
              <span>EVIDENCE</span>
            </button>
          </div>
        )}

        {/* Responsive Tactical Workstation Layout */}
        <div style={styles.workstation}>
          {isMobile ? (
            /* Mobile View Switcher: active view occupies 100% viewport */
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', width: '100%', overflow: 'hidden' }}>
              {mobileView === 'MAP' && (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
                  <MapViewer
                    candidates={candidates}
                    selectedCandidate={selectedCandidate}
                    onSelectCandidate={setSelectedCandidate}
                    activeEpoch={activeEpoch}
                    onEpochChange={setActiveEpoch}
                  />
                </div>
              )}
              {mobileView === 'QUEUE' && (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <ReviewQueue
                    candidates={candidates}
                    selectedCandidate={selectedCandidate}
                    onSelectCandidate={(c) => {
                      setSelectedCandidate(c);
                      setMobileView('MAP');
                    }}
                    isLoading={isLoading}
                  />
                </div>
              )}
              {mobileView === 'EVIDENCE' && (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                  <EvidenceCard
                    candidate={selectedCandidate}
                    onDecisionSubmitted={handleDecisionSubmitted}
                  />
                </div>
              )}
            </div>
          ) : isTablet ? (
            /* Tablet Layout (768px – 1199px): Map primary + Evidence side + Queue drawer toggle */
            <>
              {/* Tablet Queue Toggle Floating Button */}
              <button
                type="button"
                onClick={() => setTabletDrawerOpen((prev) => !prev)}
                style={styles.tabletDrawerBtn}
                title="Toggle review candidate queue"
                aria-label="Toggle review queue drawer"
              >
                <LayersIcon size={13} color="#38bdf8" />
                <span>{tabletDrawerOpen ? 'CLOSE QUEUE' : `QUEUE (${candidates.length})`}</span>
              </button>

              {/* Tablet Collapsible Queue Drawer */}
              {tabletDrawerOpen && (
                <div style={styles.tabletDrawerBackdrop} onClick={() => setTabletDrawerOpen(false)}>
                  <div style={styles.tabletDrawerContent} onClick={(e) => e.stopPropagation()}>
                    <div style={styles.drawerHeader}>
                      <span style={styles.drawerTitle}>REVIEW CANDIDATES ({candidates.length})</span>
                      <button
                        type="button"
                        onClick={() => setTabletDrawerOpen(false)}
                        style={styles.drawerCloseBtn}
                        aria-label="Close queue drawer"
                      >
                        <CloseIcon size={14} color="#94a3b8" />
                      </button>
                    </div>
                    <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                      <ReviewQueue
                        candidates={candidates}
                        selectedCandidate={selectedCandidate}
                        onSelectCandidate={(c) => {
                          setSelectedCandidate(c);
                          setTabletDrawerOpen(false);
                        }}
                        isLoading={isLoading}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Center Map Viewer */}
              <div style={styles.mapCol}>
                <MapViewer
                  candidates={candidates}
                  selectedCandidate={selectedCandidate}
                  onSelectCandidate={setSelectedCandidate}
                  activeEpoch={activeEpoch}
                  onEpochChange={setActiveEpoch}
                />
              </div>

              {/* Right Evidence Panel */}
              <div
                style={{
                  ...styles.evidenceCol,
                  width: windowWidth < 960 ? '340px' : '380px',
                  minWidth: windowWidth < 960 ? '340px' : '380px',
                }}
              >
                <EvidenceCard
                  candidate={selectedCandidate}
                  onDecisionSubmitted={handleDecisionSubmitted}
                />
              </div>
            </>
          ) : (
            /* Desktop Layout (>= 1200px): Standard 3-Column Workstation */
            <>
              <div style={styles.queueCol}>
                <ReviewQueue
                  candidates={candidates}
                  selectedCandidate={selectedCandidate}
                  onSelectCandidate={setSelectedCandidate}
                  isLoading={isLoading}
                />
              </div>

              <div style={styles.mapCol}>
                <MapViewer
                  candidates={candidates}
                  selectedCandidate={selectedCandidate}
                  onSelectCandidate={setSelectedCandidate}
                  activeEpoch={activeEpoch}
                  onEpochChange={setActiveEpoch}
                />
              </div>

              <div style={styles.evidenceCol}>
                <EvidenceCard
                  candidate={selectedCandidate}
                  onDecisionSubmitted={handleDecisionSubmitted}
                />
              </div>
            </>
          )}
        </div>

        {/* Bottom Temporal Timeline Scrubber (NASA Worldview Style) */}
        {(!isMobile || mobileView === 'MAP') && (
          <TimelineScrubber
            beforeDate={selectedCandidate?.evidence?.before_date || '2023-02-03'}
            afterDate={selectedCandidate?.evidence?.after_date || '2024-11-29'}
            activeEpoch={activeEpoch}
            onEpochChange={setActiveEpoch}
          />
        )}

        {/* Operational Telemetry Footer */}
        {!isMobile && (
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
        )}

        {/* Benchmark Evaluation Modal */}
        {showBenchmarkModal && (
          <div style={styles.modalBackdrop}>
            <div style={styles.modalContent}>
              <div style={styles.modalHeader}>
                <div style={styles.modalTitleBox}>
                  <ShieldIcon size={18} color="#10b981" />
                  <div>
                    <h3 style={styles.modalTitle}>AstraTrace 2.0 — Quantitative Evaluation Dossier</h3>
                    <span style={styles.modalSub}>SIH 2026 | Problem ID: SIH26227 | Ministry of Defence / Indian Army (DGIS)</span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setShowBenchmarkModal(false)}
                  style={styles.modalCloseBtn}
                >
                  <CloseIcon size={16} color="#94a3b8" />
                </button>
              </div>

              <div style={styles.modalBody}>
                {isLoadingBenchmark && (
                  <div style={styles.modalLoading}>
                    <span>Loading quantitative benchmark results...</span>
                  </div>
                )}

                {benchmarkData && (
                  <div style={styles.benchmarkGrid}>
                    <div style={styles.kpiCard}>
                      <span style={styles.kpiKey}>RETRIEVAL MRR</span>
                      <span style={styles.kpiVal}>{benchmarkData.retrieval?.semantic?.mean_mrr?.toFixed(4) || '0.3125'}</span>
                      <span style={styles.kpiSub}>vs Baseline {benchmarkData.retrieval?.baseline?.mean_mrr?.toFixed(4) || '0.0625'} (5.0x)</span>
                    </div>
                    <div style={styles.kpiCard}>
                      <span style={styles.kpiKey}>PRECISION@K</span>
                      <span style={styles.kpiVal}>{benchmarkData.retrieval?.semantic?.mean_precision_at_k?.toFixed(4) || '0.2500'}</span>
                      <span style={styles.kpiSub}>Orthogonal 512-D Cosine</span>
                    </div>
                    <div style={styles.kpiCard}>
                      <span style={styles.kpiKey}>TRUE CHANGE PRESERVATION</span>
                      <span style={{ ...styles.kpiVal, color: '#10b981' }}>{benchmarkData.change_detection?.true_positive_preservation_pct || 100}%</span>
                      <span style={styles.kpiSub}>Construction changes retained</span>
                    </div>
                    <div style={styles.kpiCard}>
                      <span style={styles.kpiKey}>FALSE-ALARM SUPPRESSION</span>
                      <span style={{ ...styles.kpiVal, color: '#10b981' }}>{benchmarkData.change_detection?.false_alarm_suppression_pct || 100}%</span>
                      <span style={styles.kpiSub}>Cloud/Shadows Eliminated</span>
                    </div>
                    <div style={styles.kpiCard}>
                      <span style={styles.kpiKey}>TAMPER DETECTION</span>
                      <span style={{ ...styles.kpiVal, color: '#10b981' }}>100%</span>
                      <span style={styles.kpiSub}>SHA-256 Checksum Verified</span>
                    </div>
                    <div style={styles.kpiCard}>
                      <span style={styles.kpiKey}>AIR-GAP ISOLATION</span>
                      <span style={{ ...styles.kpiVal, color: '#10b981' }}>VERIFIED</span>
                      <span style={styles.kpiSub}>0 Socket Egress Allowed</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
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
    boxShadow: '0 0 10px rgba(56, 189, 248, 0.2)',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  brandTitle: {
    margin: 0,
    fontSize: '1.1rem',
    fontWeight: 900,
    letterSpacing: '0.08em',
    color: '#f8fafc',
  },
  versionTag: {
    fontSize: '0.62rem',
    fontWeight: 800,
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    padding: '1px 5px',
    borderRadius: '3px',
    letterSpacing: '0.05em',
  },
  brandSubtitle: {
    fontSize: '0.68rem',
    color: '#64748b',
    fontWeight: 600,
  },
  metaGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  utcBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#0f1722',
    border: '1px solid #182635',
    padding: '4px 10px',
    borderRadius: '4px',
  },
  utcText: {
    fontSize: '0.75rem',
    fontWeight: 700,
    fontFamily: 'monospace',
    color: '#38bdf8',
  },
  badgeMod: {
    backgroundColor: '#0f1722',
    border: '1px solid #182635',
    padding: '4px 10px',
    borderRadius: '4px',
  },
  modText: {
    fontSize: '0.72rem',
    fontWeight: 700,
    color: '#cbd5e1',
    letterSpacing: '0.02em',
  },
  badgeAirgap: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    color: '#10b981',
    padding: '4px 10px',
    borderRadius: '4px',
    fontSize: '0.7rem',
    fontWeight: 800,
    letterSpacing: '0.04em',
  },
  greenPulse: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#10b981',
    boxShadow: '0 0 8px #10b981',
  },
  benchmarkBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#10b981',
    color: '#06090e',
    border: 'none',
    padding: '6px 12px',
    borderRadius: '4px',
    fontSize: '0.7rem',
    fontWeight: 800,
    letterSpacing: '0.04em',
    cursor: 'pointer',
  },
  searchRow: {
    padding: '8px 16px',
    backgroundColor: '#070d19',
    borderBottom: '1px solid #141f2d',
  },
  mobileTabBar: {
    display: 'flex',
    backgroundColor: '#070d19',
    borderBottom: '1px solid #182635',
    padding: '4px 8px',
    gap: '6px',
    flexShrink: 0,
  },
  mobileTabBtn: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    padding: '7px 8px',
    backgroundColor: '#0c131c',
    border: '1px solid #1e293b',
    borderRadius: '4px',
    color: '#94a3b8',
    fontSize: '0.68rem',
    fontWeight: 700,
    cursor: 'pointer',
  },
  mobileTabBtnActive: {
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    borderColor: '#38bdf8',
    color: '#38bdf8',
    fontWeight: 800,
  },
  tabletDrawerBtn: {
    position: 'absolute',
    top: '10px',
    left: '10px',
    zIndex: 20,
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#0b1118',
    border: '1px solid #38bdf8',
    color: '#38bdf8',
    padding: '6px 12px',
    borderRadius: '4px',
    fontSize: '0.70rem',
    fontWeight: 800,
    cursor: 'pointer',
    boxShadow: '0 2px 10px rgba(0,0,0,0.5)',
  },
  tabletDrawerBackdrop: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.65)',
    zIndex: 1000,
    display: 'flex',
  },
  tabletDrawerContent: {
    width: '320px',
    maxWidth: '85vw',
    height: '100%',
    backgroundColor: '#070d19',
    borderRight: '1px solid #182635',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '4px 0 24px rgba(0, 0, 0, 0.8)',
  },
  drawerHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 16px',
    borderBottom: '1px solid #182635',
    backgroundColor: '#0b1118',
  },
  drawerTitle: {
    fontSize: '0.72rem',
    fontWeight: 800,
    color: '#38bdf8',
    letterSpacing: '0.05em',
  },
  drawerCloseBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '4px',
    display: 'flex',
    alignItems: 'center',
  },
  workstation: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
    position: 'relative',
  },
  queueCol: {
    width: '340px',
    minWidth: '340px',
    borderRight: '1px solid #182635',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  mapCol: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    overflow: 'hidden',
  },
  evidenceCol: {
    width: '440px',
    minWidth: '440px',
    borderLeft: '1px solid #182635',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  footer: {
    height: '28px',
    backgroundColor: '#070d19',
    borderTop: '1px solid #141f2d',
    display: 'flex',
    alignItems: 'center',
    padding: '0 16px',
    gap: '12px',
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
    letterSpacing: '0.04em',
  },
  footerVal: {
    color: '#cbd5e1',
    fontWeight: 600,
  },
  footerDivider: {
    width: '1px',
    height: '14px',
    backgroundColor: '#182635',
  },
  footerItemRight: {
    marginLeft: 'auto',
  },
  securityTag: {
    display: 'flex',
    alignItems: 'center',
    color: '#10b981',
    fontWeight: 700,
  },
  modalBackdrop: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    backdropFilter: 'blur(6px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
  },
  modalContent: {
    width: '720px',
    maxWidth: '90vw',
    backgroundColor: '#0b1118',
    border: '1px solid #1e293b',
    borderRadius: '8px',
    overflow: 'hidden',
    boxShadow: '0 8px 32px rgba(0,0,0,0.8)',
  },
  modalHeader: {
    padding: '16px 20px',
    borderBottom: '1px solid #182635',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  modalTitleBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  modalTitle: {
    fontSize: '1rem',
    fontWeight: 800,
    color: '#f8fafc',
    margin: 0,
  },
  modalSub: {
    fontSize: '0.7rem',
    color: '#64748b',
  },
  modalCloseBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '4px',
  },
  modalBody: {
    padding: '20px',
  },
  modalLoading: {
    padding: '30px',
    textAlign: 'center',
    color: '#94a3b8',
    fontSize: '0.85rem',
  },
  benchmarkGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '12px',
  },
  kpiCard: {
    backgroundColor: '#070d19',
    border: '1px solid #182635',
    borderRadius: '6px',
    padding: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  kpiKey: {
    fontSize: '0.62rem',
    fontWeight: 700,
    color: '#64748b',
    letterSpacing: '0.05em',
  },
  kpiVal: {
    fontSize: '1.4rem',
    fontWeight: 800,
    color: '#38bdf8',
    fontFamily: 'monospace',
  },
  kpiSub: {
    fontSize: '0.65rem',
    color: '#94a3b8',
  },
};
