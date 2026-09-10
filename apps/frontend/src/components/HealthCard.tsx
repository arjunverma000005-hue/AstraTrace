import React, { useEffect, useState } from 'react';
import { ApiClient } from '../api/client';
import { HealthResponse } from '../types/api';

export const HealthCard: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ApiClient.getHealth();
      setHealth(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to connect to AstraTrace backend.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h3 style={styles.title}>System Health & Operational Status</h3>
        <button onClick={fetchHealth} disabled={loading} style={styles.button}>
          {loading ? 'Checking...' : 'Refresh Status'}
        </button>
      </div>

      {loading && <p style={styles.muted}>Querying local backend service...</p>}

      {error && (
        <div style={styles.errorBox}>
          <strong>Connection Disconnected:</strong> {error}
          <div style={styles.hint}>Ensure backend is running locally on port 8000.</div>
        </div>
      )}

      {health && (
        <div style={styles.grid}>
          <div style={styles.metric}>
            <span style={styles.label}>Application:</span>
            <span style={styles.value}>{health.app}</span>
          </div>
          <div style={styles.metric}>
            <span style={styles.label}>Version:</span>
            <span style={styles.value}>v{health.version}</span>
          </div>
          <div style={styles.metric}>
            <span style={styles.label}>Core Service:</span>
            <span style={{ ...styles.value, color: '#10b981' }}>{health.status.toUpperCase()}</span>
          </div>
          <div style={styles.metric}>
            <span style={styles.label}>Network Profile:</span>
            <span style={{ ...styles.value, color: health.offline_mode ? '#3b82f6' : '#f59e0b' }}>
              {health.offline_mode ? 'AIR-GAPPED (OFFLINE)' : 'ONLINE'}
            </span>
          </div>
          <div style={styles.metric}>
            <span style={styles.label}>Last Check:</span>
            <span style={styles.timestamp}>{new Date(health.timestamp).toLocaleTimeString()}</span>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  card: {
    backgroundColor: '#161e2e',
    border: '1px solid #2d3748',
    borderRadius: '8px',
    padding: '1.5rem',
    marginTop: '1.5rem',
    maxWidth: '680px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
  },
  title: {
    margin: 0,
    fontSize: '1.15rem',
    fontWeight: 600,
    color: '#f8fafc',
  },
  button: {
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    padding: '0.4rem 0.8rem',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.85rem',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '0.75rem',
  },
  metric: {
    display: 'flex',
    flexDirection: 'column',
  },
  label: {
    fontSize: '0.75rem',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  value: {
    fontSize: '0.95rem',
    fontWeight: 500,
    color: '#f1f5f9',
  },
  timestamp: {
    fontSize: '0.85rem',
    color: '#cbd5e1',
  },
  muted: {
    color: '#94a3b8',
    fontSize: '0.9rem',
  },
  errorBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid #ef4444',
    padding: '0.75rem',
    borderRadius: '4px',
    color: '#fca5a5',
    fontSize: '0.9rem',
  },
  hint: {
    fontSize: '0.8rem',
    color: '#cbd5e1',
    marginTop: '0.25rem',
  },
};
