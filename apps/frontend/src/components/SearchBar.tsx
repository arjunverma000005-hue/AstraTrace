import React, { useState } from 'react';
import { SearchMode, UnifiedSearchRequest } from '../types/api';
import { SearchIcon, CloseIcon, SpinnerIcon } from './Icons';

interface SearchBarProps {
  onSearch: (req: UnifiedSearchRequest) => void;
  isLoading: boolean;
}

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

  return (
    <form onSubmit={handleSearchSubmit} style={styles.container}>
      {/* Query Input */}
      <div style={styles.inputGroup}>
        <span style={styles.searchIcon}>
          <SearchIcon size={18} color="#94a3b8" />
        </span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search satellite imagery by concepts, EuroSAT vocabulary, or natural language..."
          style={styles.searchInput}
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery('')}
            style={styles.clearBtn}
            title="Clear search"
          >
            <CloseIcon size={14} color="#94a3b8" />
          </button>
        )}
      </div>

      {/* Controls Row */}
      <div style={styles.controlsRow}>
        {/* Modality Selector */}
        <div style={styles.controlItem}>
          <label style={styles.label}>Mode:</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as SearchMode)}
            style={styles.select}
          >
            <option value="AUTO">AUTO (Hybrid 65/35)</option>
            <option value="SEMANTIC">SEMANTIC (512-D Vectors)</option>
            <option value="KEYWORD">KEYWORD (EuroSAT)</option>
          </select>
        </div>

        {/* Quality Filter */}
        <div style={styles.controlItem}>
          <label style={styles.label}>Quality Gate:</label>
          <select
            value={qualityFilter}
            onChange={(e) => setQualityFilter(e.target.value)}
            style={styles.select}
          >
            <option value="ALL">All Observations</option>
            <option value="USABLE">USABLE Only (Clear Sky)</option>
            <option value="USABLE_DEGRADED">USABLE + DEGRADED</option>
          </select>
        </div>

        {/* Confidence Threshold */}
        <div style={styles.controlItem}>
          <label style={styles.label}>Min Conf: {(minConfidence * 100).toFixed(0)}%</label>
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

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          style={{
            ...styles.searchBtn,
            opacity: isLoading ? 0.7 : 1.0,
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            {isLoading ? <SpinnerIcon size={14} color="#ffffff" /> : <SearchIcon size={14} color="#ffffff" />}
            <span>{isLoading ? 'Searching...' : 'Search Intelligence'}</span>
          </span>
        </button>
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
    backgroundColor: '#111827',
    borderRadius: '8px',
    border: '1px solid #1f2937',
  },
  inputGroup: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#0f172a',
    borderRadius: '6px',
    border: '1px solid #334155',
    padding: '0 12px',
  },
  searchIcon: {
    fontSize: '1rem',
    color: '#64748b',
    marginRight: '8px',
  },
  searchInput: {
    flex: 1,
    height: '38px',
    backgroundColor: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#f8fafc',
    fontSize: '0.88rem',
  },
  clearBtn: {
    background: 'transparent',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    fontSize: '0.85rem',
    padding: '4px',
  },
  controlsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
    flexWrap: 'wrap',
  },
  controlItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  label: {
    fontSize: '0.75rem',
    fontWeight: 600,
    color: '#94a3b8',
    whiteSpace: 'nowrap',
  },
  select: {
    height: '30px',
    padding: '0 8px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '4px',
    color: '#f1f5f9',
    fontSize: '0.78rem',
    outline: 'none',
    cursor: 'pointer',
  },
  rangeInput: {
    width: '90px',
    cursor: 'pointer',
  },
  searchBtn: {
    marginLeft: 'auto',
    height: '32px',
    padding: '0 16px',
    backgroundColor: '#0284c7',
    color: '#f8fafc',
    border: 'none',
    borderRadius: '4px',
    fontSize: '0.82rem',
    fontWeight: 700,
    cursor: 'pointer',
    letterSpacing: '0.03em',
    transition: 'all 0.15s ease',
  },
};
