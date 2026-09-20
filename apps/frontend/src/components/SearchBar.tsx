import React, { useState, useRef } from 'react';
import { SearchMode, UnifiedSearchRequest, ParsedQuerySlots } from '../types/api';
import { ApiClient } from '../api/client';
import {
  SearchIcon,
  CloseIcon,
  SpinnerIcon,
  SlidersIcon,
  CrosshairIcon,
  SparklesIcon,
  SatelliteIcon,
} from './Icons';

interface SearchBarProps {
  onSearch: (req: UnifiedSearchRequest) => void;
  onImageSearchResult?: (tiles: any[]) => void;
  isLoading: boolean;
}

const DEMO_QUERIES = [
  'Find newly built structures near roads between January 2023 and January 2025',
  'Jewar Airport Corridor T43RGM industrial expansion',
  'Highway infrastructure alterations',
  'Runway expansion and pavement development',
];

// Helper to simulate semantic query parsing client-side for immediate slot feedback
function parseQueryClientSide(text: string): ParsedQuerySlots {
  const lower = text.toLowerCase();
  const slots: ParsedQuerySlots = {};

  if (lower.includes('structure') || lower.includes('building') || lower.includes('industrial') || lower.includes('hangar')) {
    slots.target = 'Built Structures / Facilities';
  } else if (lower.includes('road') || lower.includes('highway') || lower.includes('runway') || lower.includes('taxiway')) {
    slots.target = 'Transportation / Pavement';
  } else if (lower.includes('vegetation') || lower.includes('clearing') || lower.includes('forest')) {
    slots.target = 'Vegetation / Land Cover';
  } else {
    slots.target = 'General Anthropogenic Site';
  }

  if (lower.includes('newly built') || lower.includes('new') || lower.includes('construction')) {
    slots.change = 'New Construction (+Δ)';
  } else if (lower.includes('expansion') || lower.includes('extended')) {
    slots.change = 'Spatial Expansion';
  } else if (lower.includes('alteration') || lower.includes('change')) {
    slots.change = 'Surface Alteration';
  } else if (lower.includes('demolition') || lower.includes('clearance')) {
    slots.change = 'Clearance / Removal (-Δ)';
  }

  if (lower.includes('near roads') || lower.includes('near highway')) {
    slots.context = 'Proximity to Road Network (< 150m)';
  } else if (lower.includes('corridor') || lower.includes('airport')) {
    slots.context = 'Aviation / Transport Corridor';
  }

  if (lower.includes('2023') || lower.includes('2025') || lower.includes('january')) {
    slots.time = '2023-01-01 → 2025-01-31';
  }

  if (lower.includes('jewar') || lower.includes('t43rgm')) {
    slots.location = 'Jewar Airport Corridor [77.53°E, 28.15°N]';
  } else if (lower.includes('western ghats')) {
    slots.location = 'Western Ghats, MH';
  }

  slots.sensor = 'Copernicus Sentinel-2 (B2,B3,B4,B8)';
  slots.quality = 'Usable (Cloud < 15%)';

  return slots;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onSearch, onImageSearchResult, isLoading }) => {
  const [query, setQuery] = useState<string>('');
  const [mode, setMode] = useState<SearchMode>('AUTO');
  const [minConfidence, setMinConfidence] = useState<number>(0.0);
  const [qualityFilter, setQualityFilter] = useState<string>('ALL');
  const [showSlotBreakdown, setShowSlotBreakdown] = useState<boolean>(true);
  const [isUploadingImage, setIsUploadingImage] = useState<boolean>(false);
  const [uploadedImageName, setUploadedImageName] = useState<string | null>(null);
  const [searchWarning, setSearchWarning] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const parsedSlots = query.trim() ? parseQueryClientSide(query) : null;

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (mode === 'CHANGE' && !query.trim()) {
      setSearchWarning('Enter a change description, location, or date range.');
      return;
    }
    setSearchWarning(null);

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
    setSearchWarning(null);
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

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadedImageName(file.name);
    setIsUploadingImage(true);

    try {
      const res = await ApiClient.searchByImage(file, 25);
      if (onImageSearchResult && res.results) {
        onImageSearchResult(res.results);
      } else {
        // Also trigger fallback search to refresh list
        onSearch({ search_mode: 'SEMANTIC', top_k: 25 });
      }
    } catch (err) {
      console.error('Image search failed:', err);
    } finally {
      setIsUploadingImage(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div style={styles.container}>
      <form onSubmit={handleSearchSubmit}>
        {/* Top Command Input Bar */}
        <div style={styles.inputGroup}>
          <span style={styles.searchIcon}>
            <SearchIcon size={18} color="#38bdf8" />
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (searchWarning) setSearchWarning(null);
            }}
            placeholder="ENTER NATURAL LANGUAGE QUERY • e.g. 'Find newly built structures near roads between January 2023 and January 2025'..."
            aria-label="Natural language search query"
            style={styles.searchInput}
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery('');
                setSearchWarning(null);
              }}
              aria-label="Clear search query"
              style={styles.clearBtn}
              title="Clear search query"
            >
              <CloseIcon size={14} color="#94a3b8" />
            </button>
          )}

          {/* Image-to-Image Similarity Upload Trigger */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleImageUpload}
            accept="image/*"
            aria-label="Upload reference raster file"
            style={{ display: 'none' }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploadingImage}
            aria-label="Upload reference raster to search visually similar sites"
            style={styles.imageUploadBtn}
            title="Upload reference raster/crop to search visually similar sites"
          >
            {isUploadingImage ? <SpinnerIcon size={14} /> : <SatelliteIcon size={14} color="#38bdf8" />}
            <span>{isUploadingImage ? 'ANALYZING...' : uploadedImageName ? `IMG: ${uploadedImageName}` : 'IMAGE SEARCH'}</span>
          </button>

          <button
            type="submit"
            disabled={isLoading}
            aria-label="Execute search query"
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

        {/* Tactical Search Warning / Guidance Banner */}
        {searchWarning && (
          <div style={styles.warningAlert} role="alert">
            <span style={styles.warningIcon}>⚠️</span>
            <span style={styles.warningText}>{searchWarning}</span>
            <button
              type="button"
              onClick={() => setSearchWarning(null)}
              aria-label="Dismiss warning"
              style={styles.warningDismissBtn}
            >
              DISMISS
            </button>
          </div>
        )}

        {/* Natural Language Slot Breakdown Card */}
        {parsedSlots && showSlotBreakdown && (
          <div style={styles.slotCard}>
            <div style={styles.slotHeader}>
              <div style={styles.slotTitle}>
                <SparklesIcon size={12} color="#38bdf8" />
                <span>PARSED SEMANTIC SLOTS (DISCOVERY ENGINE)</span>
              </div>
              <button
                type="button"
                onClick={() => setShowSlotBreakdown(false)}
                style={styles.slotCloseBtn}
              >
                DISMISS
              </button>
            </div>
            <div style={styles.slotGrid}>
              {parsedSlots.target && (
                <div style={styles.slotPill}>
                  <span style={styles.slotKey}>TARGET:</span>
                  <span style={styles.slotVal}>{parsedSlots.target}</span>
                </div>
              )}
              {parsedSlots.change && (
                <div style={styles.slotPill}>
                  <span style={styles.slotKey}>CHANGE:</span>
                  <span style={{ ...styles.slotVal, color: '#f59e0b' }}>{parsedSlots.change}</span>
                </div>
              )}
              {parsedSlots.context && (
                <div style={styles.slotPill}>
                  <span style={styles.slotKey}>CONTEXT:</span>
                  <span style={styles.slotVal}>{parsedSlots.context}</span>
                </div>
              )}
              {parsedSlots.time && (
                <div style={styles.slotPill}>
                  <span style={styles.slotKey}>TIME:</span>
                  <span style={styles.slotVal}>{parsedSlots.time}</span>
                </div>
              )}
              {parsedSlots.location && (
                <div style={styles.slotPill}>
                  <span style={styles.slotKey}>LOCATION:</span>
                  <span style={styles.slotVal}>{parsedSlots.location}</span>
                </div>
              )}
              {parsedSlots.sensor && (
                <div style={styles.slotPill}>
                  <span style={styles.slotKey}>SENSOR:</span>
                  <span style={styles.slotVal}>{parsedSlots.sensor}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Controls & Modality Row */}
        <div style={styles.controlsRow}>
          {/* Modality Mode Selector */}
          <div style={styles.controlItem}>
            <span style={styles.label}>
              <SlidersIcon size={13} color="#94a3b8" style={{ marginRight: '4px' }} />
              MODE:
            </span>
            <div style={styles.pillGroup} role="group" aria-label="Search mode selector">
              {(['AUTO', 'SEMANTIC', 'KEYWORD', 'HYBRID', 'CHANGE'] as SearchMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => {
                    setMode(m);
                    if (searchWarning) setSearchWarning(null);
                  }}
                  aria-label={`Search mode ${m}`}
                  aria-pressed={mode === m}
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
              aria-label="Quality gate filter"
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
              MIN CONF: <span style={styles.valBadge}>{Math.round(minConfidence * 100)}%</span>
            </span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              aria-label="Minimum confidence threshold"
              style={styles.slider}
            />
          </div>
        </div>

        {/* Quick Query Shortcuts */}
        <div style={styles.quickQueryRow}>
          <span style={styles.quickLabel}>TACTICAL PRESETS:</span>
          <div style={styles.quickTags}>
            {DEMO_QUERIES.map((dq, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleApplyQuickQuery(dq)}
                style={styles.quickTagBtn}
                title={dq}
              >
                {dq.length > 50 ? `${dq.substring(0, 48)}...` : dq}
              </button>
            ))}
          </div>
        </div>
      </form>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    width: '100%',
  },
  inputGroup: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#0c131c',
    border: '1px solid #1e293b',
    borderRadius: '6px',
    padding: '4px 6px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
  },
  searchIcon: {
    display: 'flex',
    alignItems: 'center',
    padding: '0 8px',
  },
  searchInput: {
    flex: 1,
    backgroundColor: 'transparent',
    border: 'none',
    color: '#f8fafc',
    fontSize: '0.875rem',
    outline: 'none',
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    letterSpacing: '0.02em',
  },
  clearBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '4px',
    display: 'flex',
    alignItems: 'center',
  },
  imageUploadBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    color: '#38bdf8',
    padding: '6px 12px',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 700,
    letterSpacing: '0.05em',
    cursor: 'pointer',
    marginRight: '6px',
  },
  searchBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#38bdf8',
    color: '#06090e',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: 800,
    letterSpacing: '0.05em',
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  },
  slotCard: {
    backgroundColor: '#0f172a',
    border: '1px solid #1e293b',
    borderRadius: '6px',
    padding: '8px 12px',
  },
  slotHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '6px',
  },
  slotTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#38bdf8',
    letterSpacing: '0.05em',
  },
  slotCloseBtn: {
    background: 'none',
    border: 'none',
    color: '#64748b',
    fontSize: '0.65rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  slotGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
  },
  slotPill: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
    border: '1px solid rgba(56, 189, 248, 0.2)',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '0.7rem',
  },
  slotKey: {
    color: '#94a3b8',
    fontWeight: 600,
  },
  slotVal: {
    color: '#f1f5f9',
    fontWeight: 700,
  },
  controlsRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: '12px',
    padding: '0 4px',
  },
  controlItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  label: {
    fontSize: '0.7rem',
    fontWeight: 700,
    color: '#64748b',
    letterSpacing: '0.05em',
    display: 'flex',
    alignItems: 'center',
  },
  valBadge: {
    color: '#38bdf8',
    fontFamily: 'monospace',
  },
  pillGroup: {
    display: 'flex',
    gap: '2px',
    backgroundColor: '#0c131c',
    border: '1px solid #1e293b',
    borderRadius: '4px',
    padding: '2px',
  },
  pillBtn: {
    background: 'transparent',
    border: 'none',
    color: '#94a3b8',
    padding: '3px 8px',
    fontSize: '0.68rem',
    fontWeight: 600,
    borderRadius: '3px',
    cursor: 'pointer',
    letterSpacing: '0.04em',
  },
  pillBtnActive: {
    backgroundColor: '#38bdf8',
    color: '#06090e',
    fontWeight: 800,
  },
  select: {
    backgroundColor: '#0c131c',
    border: '1px solid #1e293b',
    color: '#f8fafc',
    padding: '4px 8px',
    fontSize: '0.7rem',
    borderRadius: '4px',
    outline: 'none',
    cursor: 'pointer',
  },
  slider: {
    width: '90px',
    cursor: 'pointer',
  },
  quickQueryRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '0 4px',
  },
  quickLabel: {
    fontSize: '0.65rem',
    fontWeight: 700,
    color: '#475569',
    letterSpacing: '0.05em',
    flexShrink: 0,
  },
  quickTags: {
    display: 'flex',
    gap: '6px',
    overflowX: 'auto',
    whiteSpace: 'nowrap',
  },
  quickTagBtn: {
    backgroundColor: '#0c131c',
    border: '1px solid #1e293b',
    color: '#94a3b8',
    fontSize: '0.68rem',
    padding: '2px 8px',
    borderRadius: '3px',
    cursor: 'pointer',
  },
  warningAlert: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    borderRadius: '4px',
    padding: '6px 12px',
    marginTop: '6px',
  },
  warningIcon: {
    fontSize: '0.85rem',
    lineHeight: 1,
  },
  warningText: {
    fontSize: '0.72rem',
    fontWeight: 700,
    color: '#f59e0b',
    letterSpacing: '0.02em',
    flex: 1,
  },
  warningDismissBtn: {
    backgroundColor: 'transparent',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    color: '#f59e0b',
    fontSize: '0.60rem',
    fontWeight: 800,
    padding: '2px 6px',
    borderRadius: '3px',
    cursor: 'pointer',
  },
};
