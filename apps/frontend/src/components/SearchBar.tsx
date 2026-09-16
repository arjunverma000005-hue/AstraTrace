import React, { useState } from 'react';
import { SearchMode, UnifiedSearchRequest } from '../types/api';
import { SearchIcon, CloseIcon, SpinnerIcon, SlidersIcon, CrosshairIcon, SparklesIcon } from './Icons';

interface SearchBarProps {
  onSearch: (req: UnifiedSearchRequest) => void;
  isLoading: boolean;
}

const DEMO_QUERIES = [
  'Find newly built structures near roads between January 2023 and January 2025',
  'Jewar Airport Corridor T43RGM industrial expansion',
  'Highway infrastructure alterations',
];

export const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState<string>('');
  const [mode, setMode] = useState<SearchMode>('AUTO');
  const [minConfidence, setMinConfidence] = useState<number>(0.0);
  const [qualityFilter, setQualityFilter] = useState<string>('ALL');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const req: UnifiedSearchRequest = {
      query: query.trim() || undefined,
      search_mode: mode,
      min_confidence: minConfidence,
      allowed_quality_statuses:
        qualityFilter === 'USABLE'
          ? ['USABLE']
          : qualityFilter === 'USABLE_DEGRADED'
          ? ['USABLE', 'DEGRADED']
          : undefined,
      top_k: 25,
      page: 1,
      page_size: 25,
    };

    onSearch(req);
  };

  const handleApplyQuickQuery = (q: string) => {
    setQuery(q);
    const req: UnifiedSearchRequest = {
      query: q,
      search_mode: mode,
      min_confidence: minConfidence,
      allowed_quality_statuses:
        qualityFilter === 'USABLE'
          ? ['USABLE']
          : qualityFilter === 'USABLE_DEGRADED'
          ? ['USABLE', 'DEGRADED']
          : undefined,
      top_k: 25,
      page: 1,
      page_size: 25,
    };
    onSearch(req);
  };

  return (
    <form onSubmit={handleSearchSubmit} style={styles.container}>
      {/* Top Command Input Bar */}
      <div style={styles.inputGroup}>
        <span style={styles.searchIcon}>
          <SearchIcon size={18} color="#38bdf8" />
        </span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="ENTER GEOSPATIAL QUERY • e.g. 'Find newly built structures near roads between January 2023 and January 2025'..."
          style={styles.searchInput}
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery('')}
            style={styles.clearBtn}
            title="Clear search query"
          >
            <CloseIcon size={14} color="#94a3b8" />
          </button>
        )}
        <button
          type="submit"
          disabled={isLoading}
          style={{
            ...styles.searchBtn,
            opacity: isLoading ? 0.75 : 1.0,
          }}
        >
          {isLoading ? (
            <>
              <SpinnerIcon size={14} color="#06090e" />
              <span>SEARCHING...</span>
            </>
          ) : (
            <>
              <CrosshairIcon size={14} color="#06090e" />
              <span>EXECUTE QUERY</span>
            </>
          )}
        </button>
      </div>

      {/* Controls & Modality Row */}
      <div style={styles.controlsRow}>
        {/* Modality Mode Selector */}
        <div style={styles.controlItem}>
          <span style={styles.label}>
            <SlidersIcon size={13} color="#94a3b8" style={{ marginRight: '4px' }} />
            MODE:
          </span>
          <div style={styles.pillGroup}>
            {(['AUTO', 'SEMANTIC', 'KEYWORD'] as SearchMode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                style={{
                  ...styles.pillBtn,
                  ...(mode === m ? styles.pillBtnActive : {}),
                }}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Quality Gate Selector */}
        <div style={styles.controlItem}>
          <span style={styles.label}>QUALITY GATE:</span>
          <select
            value={qualityFilter}
            onChange={(e) => setQualityFilter(e.target.value)}
            style={styles.select}
          >
            <option value="ALL">ALL OBSERVATIONS</option>
            <option value="USABLE">USABLE ONLY (CLEAR SKY)</option>
            <option value="USABLE_DEGRADED">USABLE + DEGRADED</option>
          </select>
        </div>

        {/* Confidence Threshold */}
        <div style={styles.controlItem}>
          <span style={styles.label}>
            MIN CONF:
            <span style={styles.monoValue}>{(minConfidence * 100).toFixed(0)}%</span>
          </span>
          <input
            type="range"
            min="0"
            max="0.8"
            step="0.05"
            value={minConfidence}
            onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
            style={styles.rangeInput}
          />
        </div>

        {/* Tactical Quick Query Chips */}
        <div style={styles.quickChipsGroup}>
          <span style={styles.chipsLabel}>
            <SparklesIcon size={12} color="#38bdf8" style={{ marginRight: '3px' }} />
            SUGGESTED:
          </span>
          {DEMO_QUERIES.map((q, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplyQuickQuery(q)}
              style={styles.chipBtn}
              title={q}
            >
              {q.length > 34 ? q.substring(0, 34) + '…' : q}
            </button>
          ))}
        </div>
      </div>
    </form>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    padding: '12px 16px',
    backgroundColor: 'rgba(11, 17, 24, 0.94)',
    backdropFilter: 'blur(10px)',
    borderRadius: '8px',
    border: '1px solid #182635',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.45)',
  },
  inputGroup: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#06090e',
    borderRadius: '6px',
    border: '1px solid #22374c',
    padding: '3px 6px 3px 12px',
    transition: 'border-color 0.2s ease',
  },
  searchIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: '10px',
  },
  searchInput: {
    flex: 1,
    height: '38px',
    backgroundColor: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#f8fafc',
    fontSize: '0.85rem',
    fontFamily: 'var(--font-mono, monospace)',
    letterSpacing: '0.02em',
  },
  clearBtn: {
    background: 'transparent',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    padding: '6px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  searchBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    height: '34px',
    padding: '0 16px',
    backgroundColor: '#38bdf8',
    color: '#06090e',
    border: 'none',
    borderRadius: '4px',
    fontSize: '0.78rem',
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: '0.05em',
    transition: 'all 0.15s ease',
    boxShadow: '0 0 12px rgba(56, 189, 248, 0.25)',
  },
  controlsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    flexWrap: 'wrap',
    paddingTop: '2px',
  },
  controlItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  label: {
    display: 'inline-flex',
    alignItems: 'center',
    fontSize: '0.72rem',
    fontWeight: 700,
    color: '#94a3b8',
    letterSpacing: '0.04em',
    whiteSpace: 'nowrap',
  },
  monoValue: {
    fontFamily: 'var(--font-mono, monospace)',
    color: '#38bdf8',
    marginLeft: '5px',
  },
  pillGroup: {
    display: 'inline-flex',
    backgroundColor: '#06090e',
    borderRadius: '4px',
    padding: '2px',
    border: '1px solid #182635',
  },
  pillBtn: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#64748b',
    fontSize: '0.70rem',
    fontWeight: 700,
    padding: '3px 8px',
    borderRadius: '3px',
    cursor: 'pointer',
    letterSpacing: '0.04em',
    transition: 'all 0.15s ease',
  },
  pillBtnActive: {
    backgroundColor: '#182635',
    color: '#38bdf8',
    boxShadow: '0 0 8px rgba(56, 189, 248, 0.15)',
  },
  select: {
    height: '28px',
    padding: '0 8px',
    backgroundColor: '#06090e',
    border: '1px solid #22374c',
    borderRadius: '4px',
    color: '#f8fafc',
    fontSize: '0.72rem',
    fontWeight: 600,
    fontFamily: 'var(--font-mono, monospace)',
    outline: 'none',
    cursor: 'pointer',
  },
  rangeInput: {
    width: '80px',
    accentColor: '#38bdf8',
    cursor: 'pointer',
  },
  quickChipsGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginLeft: 'auto',
    flexWrap: 'wrap',
  },
  chipsLabel: {
    display: 'inline-flex',
    alignItems: 'center',
    fontSize: '0.68rem',
    fontWeight: 700,
    color: '#64748b',
    letterSpacing: '0.05em',
  },
  chipBtn: {
    backgroundColor: '#0f1722',
    border: '1px solid #182635',
    color: '#94a3b8',
    borderRadius: '12px',
    padding: '2px 10px',
    fontSize: '0.68rem',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    whiteSpace: 'nowrap',
    maxWidth: '220px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
};

