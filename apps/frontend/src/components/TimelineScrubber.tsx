import React, { useState, useEffect } from 'react';
import { CalendarIcon, OrbitIcon } from './Icons';

interface TimelineScrubberProps {
  beforeDate?: string | null;
  afterDate?: string | null;
  activeEpoch: 'T1' | 'T2';
  onEpochChange: (epoch: 'T1' | 'T2') => void;
  onDateChange?: (date: string) => void;
}

export const TimelineScrubber: React.FC<TimelineScrubberProps> = ({
  beforeDate = '2023-02-03',
  afterDate = '2024-11-29',
  activeEpoch,
  onEpochChange,
}) => {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1000); // ms per frame
  const t1 = beforeDate || '2023-02-03';
  const t2 = afterDate || '2024-11-29';

  // Earliest change estimated midpoint
  const earliestChangeDate = '2024-04-12';

  // Autoplay effect
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      onEpochChange(activeEpoch === 'T1' ? 'T2' : 'T1');
    }, playbackSpeed);
    return () => clearInterval(interval);
  }, [isPlaying, activeEpoch, playbackSpeed, onEpochChange]);

  return (
    <div style={styles.container}>
      {/* Left playback controls */}
      <div style={styles.controlsGroup}>
        <button
          type="button"
          onClick={() => setIsPlaying(!isPlaying)}
          style={{
            ...styles.controlBtn,
            backgroundColor: isPlaying ? 'rgba(239, 68, 68, 0.2)' : 'rgba(56, 189, 248, 0.15)',
            borderColor: isPlaying ? '#ef4444' : '#38bdf8',
            color: isPlaying ? '#ef4444' : '#38bdf8',
          }}
          title={isPlaying ? 'Pause timeline cycling' : 'Auto-cycle T1 / T2'}
        >
          {isPlaying ? '⏸ PAUSE' : '▶ CYCLE'}
        </button>

        <button
          type="button"
          onClick={() => onEpochChange('T1')}
          style={{
            ...styles.stepBtn,
            color: activeEpoch === 'T1' ? '#38bdf8' : '#94a3b8',
          }}
          title="Step to T1"
        >
          ⏮ T1
        </button>

        <button
          type="button"
          onClick={() => onEpochChange('T2')}
          style={{
            ...styles.stepBtn,
            color: activeEpoch === 'T2' ? '#38bdf8' : '#94a3b8',
          }}
          title="Step to T2"
        >
          T2 ⏭
        </button>

        <select
          value={playbackSpeed}
          onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
          style={styles.speedSelect}
        >
          <option value={1500}>0.7x (1.5s)</option>
          <option value={1000}>1.0x (1.0s)</option>
          <option value={500}>2.0x (0.5s)</option>
          <option value={250}>4.0x (0.25s)</option>
        </select>
      </div>

      {/* Central Interactive Timeline Track */}
      <div style={styles.trackContainer}>
        <div style={styles.trackLine}>
          {/* Progress fill */}
          <div
            style={{
              ...styles.trackFill,
              width: activeEpoch === 'T1' ? '12%' : '88%',
            }}
          />

          {/* T1 Marker */}
          <div
            onClick={() => onEpochChange('T1')}
            style={{
              ...styles.marker,
              left: '12%',
              borderColor: activeEpoch === 'T1' ? '#38bdf8' : '#64748b',
              backgroundColor: activeEpoch === 'T1' ? '#38bdf8' : '#1e293b',
              boxShadow: activeEpoch === 'T1' ? '0 0 10px #38bdf8' : 'none',
            }}
            title={`T1 Baseline: ${t1}`}
          >
            <div style={styles.markerLabel}>
              <span style={styles.markerBadge}>T1 BEFORE</span>
              <span style={styles.markerDate}>{t1}</span>
            </div>
          </div>

          {/* Earliest Change Detected Marker */}
          <div
            style={{
              ...styles.changeMarker,
              left: '52%',
            }}
            title={`Earliest Change Detected: ${earliestChangeDate}`}
          >
            <div style={styles.changeMarkerPin} />
            <div style={styles.changeMarkerLabel}>
              <span style={styles.changeBadge}>EARLIEST CHANGE</span>
              <span style={styles.changeDate}>{earliestChangeDate}</span>
            </div>
          </div>

          {/* T2 Marker */}
          <div
            onClick={() => onEpochChange('T2')}
            style={{
              ...styles.marker,
              left: '88%',
              borderColor: activeEpoch === 'T2' ? '#10b981' : '#64748b',
              backgroundColor: activeEpoch === 'T2' ? '#10b981' : '#1e293b',
              boxShadow: activeEpoch === 'T2' ? '0 0 10px #10b981' : 'none',
            }}
            title={`T2 Observation: ${t2}`}
          >
            <div style={styles.markerLabel}>
              <span style={{ ...styles.markerBadge, color: '#10b981' }}>T2 AFTER</span>
              <span style={styles.markerDate}>{t2}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right: Active Mission Context */}
      <div style={styles.metaGroup}>
        <div style={styles.metaItem}>
          <CalendarIcon size={12} color="#38bdf8" />
          <span style={styles.metaLabel}>ACTIVE EPOCH:</span>
          <span style={{ ...styles.metaVal, color: activeEpoch === 'T1' ? '#38bdf8' : '#10b981' }}>
            {activeEpoch === 'T1' ? `T1 (${t1})` : `T2 (${t2})`}
          </span>
        </div>
        <div style={styles.metaItem}>
          <OrbitIcon size={12} color="#94a3b8" />
          <span style={styles.metaLabel}>ORBIT:</span>
          <span style={styles.metaVal}>Sentinel-2 L2A</span>
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    height: '60px',
    backgroundColor: '#070d19',
    borderTop: '1px solid #1e293b',
    display: 'flex',
    alignItems: 'center',
    padding: '0 16px',
    gap: '20px',
    userSelect: 'none',
    zIndex: 10,
    boxShadow: '0 -4px 16px rgba(0,0,0,0.5)',
  },
  controlsGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexShrink: 0,
  },
  controlBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    fontSize: '0.75rem',
    fontWeight: 700,
    letterSpacing: '0.05em',
    borderRadius: '4px',
    border: '1px solid',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  stepBtn: {
    background: '#0f172a',
    border: '1px solid #334155',
    padding: '6px 10px',
    fontSize: '0.75rem',
    fontWeight: 600,
    borderRadius: '4px',
    cursor: 'pointer',
  },
  speedSelect: {
    background: '#0f172a',
    border: '1px solid #334155',
    color: '#94a3b8',
    padding: '5px 8px',
    fontSize: '0.7rem',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  trackContainer: {
    flex: 1,
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    position: 'relative',
    padding: '0 40px',
  },
  trackLine: {
    width: '100%',
    height: '4px',
    backgroundColor: '#1e293b',
    borderRadius: '2px',
    position: 'relative',
  },
  trackFill: {
    height: '100%',
    backgroundColor: 'rgba(56, 189, 248, 0.4)',
    borderRadius: '2px',
    transition: 'width 0.25s ease',
  },
  marker: {
    position: 'absolute',
    top: '50%',
    transform: 'translate(-50%, -50%)',
    width: '14px',
    height: '14px',
    borderRadius: '50%',
    border: '2px solid',
    cursor: 'pointer',
    zIndex: 5,
    transition: 'all 0.15s ease',
  },
  markerLabel: {
    position: 'absolute',
    bottom: '18px',
    left: '50%',
    transform: 'translateX(-50%)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    whiteSpace: 'nowrap',
  },
  markerBadge: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#38bdf8',
    letterSpacing: '0.05em',
  },
  markerDate: {
    fontSize: '0.7rem',
    color: '#cbd5e1',
    fontFamily: 'ui-monospace, monospace',
  },
  changeMarker: {
    position: 'absolute',
    top: '50%',
    transform: 'translate(-50%, -50%)',
    zIndex: 4,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  changeMarkerPin: {
    width: '2px',
    height: '18px',
    backgroundColor: '#f59e0b',
  },
  changeMarkerLabel: {
    position: 'absolute',
    top: '14px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    whiteSpace: 'nowrap',
  },
  changeBadge: {
    fontSize: '0.6rem',
    fontWeight: 700,
    color: '#f59e0b',
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    padding: '1px 4px',
    borderRadius: '2px',
    border: '1px solid rgba(245, 158, 11, 0.4)',
  },
  changeDate: {
    fontSize: '0.65rem',
    color: '#fbbf24',
    fontFamily: 'ui-monospace, monospace',
  },
  metaGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    flexShrink: 0,
    borderLeft: '1px solid #1e293b',
    paddingLeft: '16px',
  },
  metaItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '0.75rem',
  },
  metaLabel: {
    color: '#64748b',
    fontWeight: 600,
    fontSize: '0.65rem',
    letterSpacing: '0.05em',
  },
  metaVal: {
    color: '#e2e8f0',
    fontWeight: 700,
    fontFamily: 'ui-monospace, monospace',
  },
};
