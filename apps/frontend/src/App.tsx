import React from 'react';
import { HealthCard } from './components/HealthCard';
import { ErrorBoundary } from './components/ErrorBoundary';

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <div style={styles.container}>
        {/* Navigation Bar */}
        <header style={styles.header}>
          <div style={styles.brand}>
            <span style={styles.logoIcon}>🛰️</span>
            <div>
              <h1 style={styles.brandTitle}>ASTRATRACE</h1>
              <span style={styles.brandSubtitle}>Offline Geospatial Intelligence Platform</span>
            </div>
          </div>
          <div style={styles.badges}>
            <span style={styles.sihBadge}>SIH 2026 • SIH26227</span>
            <span style={styles.statusBadge}>Milestone 1: Foundation</span>
          </div>
        </header>

        {/* Main Content Shell */}
        <main style={styles.main}>
          <div style={styles.banner}>
            <div style={styles.sponsorTag}>Ministry of Defence • Indian Army, DGIS</div>
            <h2 style={styles.bannerTitle}>Semantic Retrieval & Multi-Temporal Change Analysis</h2>
            <p style={styles.bannerText}>
              AstraTrace delivers an offline, provenance-preserving satellite imagery exploitation engine.
              Currently establishing the core software foundation, typed communication contracts, and air-gapped test harnesses.
            </p>
          </div>

          {/* System Health Check Widget */}
          <HealthCard />

          {/* Architectural Road Ahead */}
          <div style={styles.roadmapCard}>
            <h4 style={styles.roadmapTitle}>Architecture Roadmap Status</h4>
            <div style={styles.roadmapList}>
              <div style={styles.roadmapItem}>
                <span style={styles.checkDone}>✓</span>
                <span><strong>Milestone 1:</strong> Foundation & Repository Setup (ACTIVE)</span>
              </div>
              <div style={styles.roadmapItem}>
                <span style={styles.checkPlanned}>○</span>
                <span><strong>Milestone 2:</strong> Data Ingestion & GeoTIFF/COG Preprocessing (PLANNED)</span>
              </div>
              <div style={styles.roadmapItem}>
                <span style={styles.checkPlanned}>○</span>
                <span><strong>Milestone 3:</strong> PostGIS STAC Catalog & Spatial Indexing (PLANNED)</span>
              </div>
              <div style={styles.roadmapItem}>
                <span style={styles.checkPlanned}>○</span>
                <span><strong>Milestones 4-6:</strong> Semantic Retrieval & Change Detection Engine (PLANNED)</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </ErrorBoundary>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#0b0f19',
    color: '#e2e8f0',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1rem 2rem',
    backgroundColor: '#111827',
    borderBottom: '1px solid #1f2937',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  logoIcon: {
    fontSize: '2rem',
  },
  brandTitle: {
    margin: 0,
    fontSize: '1.4rem',
    letterSpacing: '0.08em',
    color: '#f8fafc',
  },
  brandSubtitle: {
    fontSize: '0.8rem',
    color: '#94a3b8',
  },
  badges: {
    display: 'flex',
    gap: '0.5rem',
  },
  sihBadge: {
    backgroundColor: '#1e3a8a',
    color: '#bfdbfe',
    padding: '0.3rem 0.6rem',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 600,
  },
  statusBadge: {
    backgroundColor: '#065f46',
    color: '#a7f3d0',
    padding: '0.3rem 0.6rem',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 600,
  },
  main: {
    flex: 1,
    padding: '2rem',
    maxWidth: '1000px',
    margin: '0 auto',
    width: '100%',
  },
  banner: {
    backgroundColor: '#131b2e',
    border: '1px solid #1e293b',
    borderRadius: '8px',
    padding: '1.5rem',
    marginBottom: '1rem',
  },
  sponsorTag: {
    fontSize: '0.75rem',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: '#60a5fa',
    marginBottom: '0.5rem',
    fontWeight: 600,
  },
  bannerTitle: {
    margin: '0 0 0.5rem 0',
    fontSize: '1.35rem',
    color: '#f1f5f9',
  },
  bannerText: {
    margin: 0,
    fontSize: '0.9rem',
    color: '#94a3b8',
    lineHeight: 1.6,
  },
  roadmapCard: {
    backgroundColor: '#111827',
    border: '1px solid #1f2937',
    borderRadius: '8px',
    padding: '1.25rem',
    marginTop: '1.5rem',
    maxWidth: '680px',
  },
  roadmapTitle: {
    margin: '0 0 0.75rem 0',
    fontSize: '0.95rem',
    color: '#cbd5e1',
  },
  roadmapList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
    fontSize: '0.85rem',
    color: '#94a3b8',
  },
  roadmapItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  checkDone: {
    color: '#10b981',
    fontWeight: 'bold',
  },
  checkPlanned: {
    color: '#64748b',
  },
};
