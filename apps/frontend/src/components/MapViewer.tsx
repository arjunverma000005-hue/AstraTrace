import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { ApiClient } from '../api/client';
import { EvidenceFirstCandidate } from '../types/api';
import {
  SatelliteIcon,
  LayersIcon,
  EyeIcon,
  EyeOffIcon,
  CalendarIcon,
  TargetIcon,
  CrosshairIcon,
  ShieldIcon,
} from './Icons';

interface MapViewerProps {
  candidates: EvidenceFirstCandidate[];
  selectedCandidate: EvidenceFirstCandidate | null;
  onSelectCandidate: (candidate: EvidenceFirstCandidate) => void;
}

export const MapViewer: React.FC<MapViewerProps> = ({
  candidates,
  selectedCandidate,
  onSelectCandidate,
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [showAllFootprints, setShowAllFootprints] = useState<boolean>(true);
  const [activeEpoch, setActiveEpoch] = useState<'T1' | 'T2'>('T1');

  // Initialize MapLibre GL instance with 100% offline self-contained style
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    try {
      const offlineStyle: maplibregl.StyleSpecification = {
        version: 8,
        name: 'AstraTrace-Offline-Tactical-Dark',
        sources: {},
        layers: [
          {
            id: 'tactical-background',
            type: 'background',
            paint: {
              'background-color': '#070d19',
            },
          },
        ],
      };

      const map = new maplibregl.Map({
        container: mapContainer.current,
        style: offlineStyle,
        center: [77.58, 28.18], // Jewar Airport Corridor default center
        zoom: 12,
        attributionControl: false,
      });

      map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
      map.addControl(
        new maplibregl.ScaleControl({ maxWidth: 120, unit: 'metric' }),
        'bottom-left',
      );

      map.on('load', () => {
        setMapLoaded(true);
      });

      map.on('error', (e: any) => {
        console.warn('MapLibre internal event:', e);
      });

      mapRef.current = map;
    } catch (err: unknown) {
      console.warn('MapLibre WebGL initialization notice:', err);
      setMapError(err instanceof Error ? err.message : 'WebGL acceleration unavailable');
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Update candidate vector layers and raster underlay when candidates or selection changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const sourceId = 'candidates-source';
    const fillLayerId = 'candidates-fill';
    const lineAllLayerId = 'candidates-line-all';
    const lineSelectedLayerId = 'candidates-line-selected';
    const rasterSourceId = 'selected-candidate-raster-source';
    const rasterLayerId = 'selected-candidate-raster-layer';

    // Spatial deduplication: if multiple temporal observations share the same bbox, retain one feature
    const seenBoxes = new Set<string>();
    const deduped: EvidenceFirstCandidate[] = [];
    for (const c of candidates) {
      const boxKey = c.where?.bbox
        ? c.where.bbox.map((v) => v.toFixed(5)).join(':')
        : (c.target_id || c.candidate_id);
      if (!seenBoxes.has(boxKey)) {
        seenBoxes.add(boxKey);
        deduped.push(c);
      } else if (
        selectedCandidate &&
        (selectedCandidate.target_id === c.target_id || selectedCandidate.candidate_id === c.candidate_id)
      ) {
        const existingIdx = deduped.findIndex(
          (d) => d.where?.bbox && d.where.bbox.map((v) => v.toFixed(5)).join(':') === boxKey,
        );
        if (existingIdx !== -1) {
          deduped[existingIdx] = c;
        }
      }
    }

    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: deduped.map((c) => {
        const isSelected =
          selectedCandidate &&
          ((c.candidate_id && selectedCandidate.candidate_id === c.candidate_id) ||
            (c.target_id && selectedCandidate.target_id === c.target_id) ||
            (c.where?.bbox &&
              selectedCandidate.where?.bbox &&
              c.where.bbox.every((v, i) => Math.abs(v - selectedCandidate.where.bbox[i]) < 1e-5)))
            ? 1
            : 0;

        return {
          type: 'Feature',
          properties: {
            candidate_id: c.candidate_id || c.target_id,
            target_id: c.target_id,
            what: c.what,
            confidence: c.confidence,
            review_status: c.review_status,
            isSelected,
          },
          geometry: c.where.geometry as GeoJSON.Geometry,
        };
      }),
    };

    const source = map.getSource(sourceId) as maplibregl.GeoJSONSource | undefined;
    if (source) {
      source.setData(geojson);
    } else {
      map.addSource(sourceId, {
        type: 'geojson',
        data: geojson,
      });

      // 1. Semi-transparent footprint fill (layer visibility controlled by showAllFootprints)
      map.addLayer({
        id: fillLayerId,
        type: 'fill',
        source: sourceId,
        layout: {
          visibility: showAllFootprints ? 'visible' : 'none',
        },
        paint: {
          'fill-color': [
            'case',
            ['==', ['get', 'review_status'], 'CONFIRMED'],
            '#10b981',
            ['==', ['get', 'review_status'], 'REJECTED'],
            '#ef4444',
            ['==', ['get', 'review_status'], 'FLAGGED_FOR_INSPECTION'],
            '#f59e0b',
            '#38bdf8',
          ],
          'fill-opacity': [
            'case',
            ['==', ['get', 'isSelected'], 1],
            0.08,
            0.15,
          ],
        },
      });

      // 2. Footprint borders for general candidates (hidden when showAllFootprints is OFF)
      map.addLayer({
        id: lineAllLayerId,
        type: 'line',
        source: sourceId,
        filter: ['!=', ['get', 'isSelected'], 1],
        layout: {
          visibility: showAllFootprints ? 'visible' : 'none',
        },
        paint: {
          'line-color': '#38bdf8',
          'line-width': 1.5,
          'line-opacity': 0.7,
        },
      });

      // 3. Highlight border for SELECTED candidate (ALWAYS visible for orientation)
      map.addLayer({
        id: lineSelectedLayerId,
        type: 'line',
        source: sourceId,
        filter: ['==', ['get', 'isSelected'], 1],
        layout: {
          visibility: 'visible',
        },
        paint: {
          'line-color': '#facc15', // High-visibility yellow
          'line-width': 2.5,
          'line-opacity': 0.95,
        },
      });

      // Interactive selection
      map.on('click', fillLayerId, (e: any) => {
        if (e.features && e.features[0]) {
          const cid = e.features[0].properties?.candidate_id;
          const tid = e.features[0].properties?.target_id;
          const match = candidates.find(
            (c) =>
              (cid && (c.candidate_id === cid || c.target_id === cid)) ||
              (tid && (c.target_id === tid || c.candidate_id === tid)),
          );
          if (match) onSelectCandidate(match);
        }
      });

      map.on('mouseenter', fillLayerId, () => {
        map.getCanvas().style.cursor = 'pointer';
      });

      map.on('mouseleave', fillLayerId, () => {
        map.getCanvas().style.cursor = '';
      });
    }

    // Dynamic Full Georeferenced Optical Sentinel-2 Raster Underlay
    let rasterUrl: string | null = null;
    let rasterCoords:
      | [[number, number], [number, number], [number, number], [number, number]]
      | null = null;

    if (selectedCandidate) {
      const isChange =
        selectedCandidate.target_type === 'CHANGE' ||
        Boolean(selectedCandidate.evidence?.before_scene_preview_url);

      if (isChange) {
        if (activeEpoch === 'T1') {
          rasterUrl =
            selectedCandidate.evidence?.before_scene_preview_url ||
            selectedCandidate.evidence?.scene_preview_url ||
            selectedCandidate.evidence?.preview_url ||
            null;
        } else {
          rasterUrl =
            selectedCandidate.evidence?.after_scene_preview_url ||
            selectedCandidate.evidence?.scene_preview_url ||
            selectedCandidate.evidence?.preview_url ||
            null;
        }
      } else {
        rasterUrl =
          selectedCandidate.evidence?.scene_preview_url ||
          selectedCandidate.evidence?.preview_url ||
          (selectedCandidate.which?.tile_id
            ? ApiClient.getTilePreviewUrl(selectedCandidate.which.tile_id)
            : null);
      }

      // True georeferenced raster extent in WGS84
      rasterCoords =
        selectedCandidate.evidence?.scene_coordinates ||
        selectedCandidate.where?.coordinates ||
        (selectedCandidate.where?.bbox
          ? [
              [selectedCandidate.where.bbox[0], selectedCandidate.where.bbox[3]], // TL: minLon, maxLat
              [selectedCandidate.where.bbox[2], selectedCandidate.where.bbox[3]], // TR: maxLon, maxLat
              [selectedCandidate.where.bbox[2], selectedCandidate.where.bbox[1]], // BR: maxLon, minLat
              [selectedCandidate.where.bbox[0], selectedCandidate.where.bbox[1]], // BL: minLon, minLat
            ]
          : null);
    }

    if (selectedCandidate && rasterUrl && rasterCoords) {
      const existingRasterSource = map.getSource(rasterSourceId) as maplibregl.ImageSource | undefined;
      if (existingRasterSource && typeof existingRasterSource.updateImage === 'function') {
        try {
          existingRasterSource.updateImage({
            url: rasterUrl,
            coordinates: rasterCoords,
          });
          if (!map.getLayer(rasterLayerId)) {
            const beforeLayer = map.getLayer(fillLayerId) ? fillLayerId : undefined;
            map.addLayer(
              {
                id: rasterLayerId,
                type: 'raster',
                source: rasterSourceId,
                paint: {
                  'raster-opacity': 0.96,
                  'raster-fade-duration': 250,
                },
              },
              beforeLayer,
            );
          }
        } catch (err) {
          console.warn('MapLibre raster update notice:', err);
        }
      } else {
        try {
          if (map.getLayer(rasterLayerId)) {
            map.removeLayer(rasterLayerId);
          }
          if (map.getSource(rasterSourceId)) {
            map.removeSource(rasterSourceId);
          }
          map.addSource(rasterSourceId, {
            type: 'image',
            url: rasterUrl,
            coordinates: rasterCoords,
          });
          const beforeLayer = map.getLayer(fillLayerId) ? fillLayerId : undefined;
          map.addLayer(
            {
              id: rasterLayerId,
              type: 'raster',
              source: rasterSourceId,
              paint: {
                'raster-opacity': 0.96,
                'raster-fade-duration': 250,
              },
            },
            beforeLayer,
          );
        } catch (err) {
          console.warn('MapLibre raster layer add notice:', err);
        }
      }
    } else {
      if (map.getLayer(rasterLayerId)) {
        map.removeLayer(rasterLayerId);
      }
      if (map.getSource(rasterSourceId)) {
        map.removeSource(rasterSourceId);
      }
    }

    // Auto-fit camera: Prioritize full georeferenced scene extent for the selected candidate
    if (selectedCandidate) {
      const targetBbox =
        selectedCandidate.evidence?.scene_bbox || selectedCandidate.where.bbox;
      const [minLon, minLat, maxLon, maxLat] = targetBbox;
      map.fitBounds(
        [
          [minLon, minLat],
          [maxLon, maxLat],
        ],
        { padding: 40, maxZoom: 15, duration: 800 },
      );
    } else if (candidates.length > 0) {
      const primaryCluster = candidates.filter(
        (c) =>
          candidates[0].where.centroid[1] > 25
            ? c.where.centroid[1] > 25
            : c.where.centroid[1] <= 25,
      );
      const targetCandidates = primaryCluster.length > 0 ? primaryCluster : candidates;
      const allLons = targetCandidates.flatMap((c) => [c.where.bbox[0], c.where.bbox[2]]);
      const allLats = targetCandidates.flatMap((c) => [c.where.bbox[1], c.where.bbox[3]]);
      const bounds: [number, number, number, number] = [
        Math.min(...allLons),
        Math.min(...allLats),
        Math.max(...allLons),
        Math.max(...allLats),
      ];
      map.fitBounds(
        [
          [bounds[0], bounds[1]],
          [bounds[2], bounds[3]],
        ],
        { padding: 50, maxZoom: 13.5, duration: 800 },
      );
    }
  }, [candidates, selectedCandidate, mapLoaded, onSelectCandidate, activeEpoch]);

  // Deterministic MapLibre layer visibility effect (Phase 2)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;
    const visibility = showAllFootprints ? 'visible' : 'none';
    if (map.getLayer('candidates-fill')) {
      map.setLayoutProperty('candidates-fill', 'visibility', visibility);
    }
    if (map.getLayer('candidates-line-all')) {
      map.setLayoutProperty('candidates-line-all', 'visibility', visibility);
    }
  }, [showAllFootprints, mapLoaded]);

  const currentCandidate = selectedCandidate || (candidates.length > 0 ? candidates[0] : null);
  const aoiLabel =
    currentCandidate && currentCandidate.where.centroid[1] > 25
      ? 'Jewar Airport Corridor (T43RGM • EPSG:32643)'
      : 'Western Ghats, MH (EPSG:32643 / EPSG:4326)';

  const isBitemporal =
    selectedCandidate?.target_type === 'CHANGE' ||
    Boolean(selectedCandidate?.evidence?.before_date || selectedCandidate?.evidence?.before_scene_preview_url);

  const beforeDateStr = selectedCandidate?.evidence?.before_date || '2023-02-03';
  const afterDateStr = selectedCandidate?.evidence?.after_date || '2024-11-29';

  const handleFitAOI = () => {
    const map = mapRef.current;
    if (!map) return;
    if (selectedCandidate?.where?.bbox) {
      const b = selectedCandidate.where.bbox;
      map.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 60, maxZoom: 14, duration: 600 });
    } else {
      map.fitBounds([[77.526735, 28.132871], [77.633167, 28.227179]], { padding: 40, maxZoom: 13, duration: 600 });
    }
  };

  return (
    <div style={styles.container}>
      {/* Map Header Overlay Bar */}
      <div style={styles.overlayBar}>
        {/* Left: AOI & Satellite Sensor Context */}
        <div style={styles.aoiBadge}>
          <SatelliteIcon size={16} color="#38bdf8" />
          <span style={styles.dot} />
          <span style={styles.aoiText}>{aoiLabel}</span>
          <span style={styles.airGapTag}>
            <ShieldIcon size={10} color="#10b981" style={{ marginRight: '3px' }} />
            AIR-GAPPED
          </span>
        </div>

        {/* Center: Bitemporal Switcher (T1 / T2) */}
        {isBitemporal && (
          <div style={styles.temporalControlGroup}>
            <button
              type="button"
              onClick={() => setActiveEpoch('T1')}
              style={{
                ...styles.epochBtn,
                backgroundColor: activeEpoch === 'T1' ? '#38bdf8' : '#0f1722',
                color: activeEpoch === 'T1' ? '#06090e' : '#94a3b8',
                borderColor: activeEpoch === 'T1' ? '#38bdf8' : '#182635',
              }}
              title="Switch main map optical raster to T1 (Before) observation"
            >
              <CalendarIcon size={13} color={activeEpoch === 'T1' ? '#06090e' : '#38bdf8'} />
              <span>T1 BEFORE</span>
              <span style={{
                ...styles.epochDateBadge,
                backgroundColor: activeEpoch === 'T1' ? 'rgba(6, 9, 14, 0.4)' : '#06090e',
                color: activeEpoch === 'T1' ? '#06090e' : '#f8fafc',
              }}>
                {beforeDateStr}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setActiveEpoch('T2')}
              style={{
                ...styles.epochBtn,
                backgroundColor: activeEpoch === 'T2' ? '#38bdf8' : '#0f1722',
                color: activeEpoch === 'T2' ? '#06090e' : '#94a3b8',
                borderColor: activeEpoch === 'T2' ? '#38bdf8' : '#182635',
              }}
              title="Switch main map optical raster to T2 (After) observation"
            >
              <CalendarIcon size={13} color={activeEpoch === 'T2' ? '#06090e' : '#38bdf8'} />
              <span>T2 AFTER</span>
              <span style={{
                ...styles.epochDateBadge,
                backgroundColor: activeEpoch === 'T2' ? 'rgba(6, 9, 14, 0.4)' : '#06090e',
                color: activeEpoch === 'T2' ? '#06090e' : '#f8fafc',
              }}>
                {afterDateStr}
              </span>
            </button>
          </div>
        )}

        {/* Right: Layer Visibility & Legend Controls */}
        <div style={styles.headerControls}>
          <button
            type="button"
            onClick={handleFitAOI}
            style={styles.fitBtn}
            title="Fit view to target boundary"
          >
            <TargetIcon size={13} color="#38bdf8" />
            <span>FIT TARGET</span>
          </button>

          <button
            type="button"
            onClick={() => setShowAllFootprints((prev) => !prev)}
            style={{
              ...styles.toggleBtn,
              backgroundColor: showAllFootprints
                ? 'rgba(56, 189, 248, 0.12)'
                : '#0f1722',
              color: showAllFootprints ? '#38bdf8' : '#64748b',
              borderColor: showAllFootprints ? '#38bdf8' : '#182635',
            }}
            title={
              showAllFootprints
                ? 'Hide all candidate footprints (keep selected outline)'
                : 'Show all candidate footprint outlines'
            }
          >
            <LayersIcon size={13} color={showAllFootprints ? '#38bdf8' : '#64748b'} />
            <span>FOOTPRINTS {showAllFootprints ? 'ON' : 'OFF'}</span>
            {showAllFootprints ? (
              <EyeIcon size={12} color="#38bdf8" />
            ) : (
              <EyeOffIcon size={12} color="#64748b" />
            )}
          </button>

          <div style={styles.legend}>
            <span style={{ ...styles.legendItem, color: '#38bdf8' }}>■ Pending</span>
            <span style={{ ...styles.legendItem, color: '#10b981' }}>■ Confirmed</span>
            <span style={{ ...styles.legendItem, color: '#f59e0b' }}>■ Flagged</span>
            <span style={{ ...styles.legendItem, color: '#ef4444' }}>■ Rejected</span>
          </div>
        </div>
      </div>

      {/* Central Tactical Reticle Overlay */}
      <div style={styles.reticleOverlay}>
        <CrosshairIcon size={36} color="rgba(56, 189, 248, 0.25)" />
      </div>

      {/* MapLibre Canvas Container */}
      <div ref={mapContainer} style={styles.mapCanvas} />

      {/* Resilient Tactical Fallback if WebGL is unavailable */}
      {mapError && (
        <div style={styles.fallbackContainer}>
          <div style={styles.fallbackHeader}>
            <SatelliteIcon size={24} color="#38bdf8" />
            <div>
              <h4 style={styles.fallbackTitle}>Tactical 2D Vector Footprint Display</h4>
              <span style={styles.fallbackSubtitle}>Offline Local Vector Grid</span>
            </div>
          </div>
          <div style={styles.gridContainer}>
            {candidates.map((c) => {
              const isSelected = selectedCandidate?.candidate_id === c.candidate_id;
              return (
                <div
                  key={c.candidate_id}
                  onClick={() => onSelectCandidate(c)}
                  style={{
                    ...styles.gridCard,
                    borderColor: isSelected ? '#facc15' : '#334155',
                    backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.15)' : '#1e293b',
                  }}
                >
                  <div style={styles.gridCardHeader}>
                    <span style={styles.rankBadge}>#{c.rank}</span>
                    <span style={styles.confBadge}>{(c.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div style={styles.gridCardTitle}>{c.what}</div>
                  <div style={styles.gridCardSub}>{c.target_id}</div>
                  <div style={styles.gridCoords}>
                    {c.where.centroid[1].toFixed(4)}°N, {c.where.centroid[0].toFixed(4)}°E
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'relative',
    width: '100%',
    height: '100%',
    minHeight: '480px',
    backgroundColor: '#06090e',
    overflow: 'hidden',
    borderRadius: '8px',
    border: '1px solid #182635',
  },
  mapCanvas: {
    width: '100%',
    height: '100%',
    minHeight: '480px',
  },
  overlayBar: {
    position: 'absolute',
    top: 12,
    left: 12,
    right: 12,
    zIndex: 10,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 14px',
    backgroundColor: 'rgba(9, 14, 22, 0.9)',
    backdropFilter: 'blur(12px)',
    borderRadius: '6px',
    border: '1px solid rgba(24, 38, 53, 0.9)',
    boxShadow: '0 4px 20px rgba(0, 0, 0, 0.6)',
    pointerEvents: 'none',
  },
  aoiBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '0.78rem',
    fontWeight: 600,
    color: '#cbd5e1',
    letterSpacing: '0.03em',
    pointerEvents: 'auto',
  },
  aoiText: {
    whiteSpace: 'nowrap',
    fontFamily: 'monospace',
    letterSpacing: '0.04em',
  },
  airGapTag: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '2px 6px',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    border: '1px solid rgba(16, 185, 129, 0.3)',
    borderRadius: '4px',
    fontSize: '0.62rem',
    fontWeight: 700,
    color: '#10b981',
    letterSpacing: '0.08em',
    fontFamily: 'monospace',
    marginLeft: '6px',
  },
  dot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    backgroundColor: '#10b981',
    boxShadow: '0 0 8px #10b981',
    flexShrink: 0,
  },
  temporalControlGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    pointerEvents: 'auto',
  },
  epochBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '5px 12px',
    fontSize: '0.72rem',
    fontWeight: 700,
    letterSpacing: '0.05em',
    borderRadius: '4px',
    border: '1px solid',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  epochDateBadge: {
    fontSize: '0.66rem',
    padding: '2px 6px',
    borderRadius: '3px',
    fontFamily: 'monospace',
    letterSpacing: '0.02em',
  },
  headerControls: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    pointerEvents: 'auto',
  },
  fitBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '5px 11px',
    fontSize: '0.72rem',
    fontWeight: 600,
    letterSpacing: '0.04em',
    borderRadius: '4px',
    border: '1px solid #182635',
    backgroundColor: '#0f1722',
    color: '#cbd5e1',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  toggleBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '5px 11px',
    fontSize: '0.72rem',
    fontWeight: 600,
    letterSpacing: '0.04em',
    borderRadius: '4px',
    border: '1px solid',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  legend: {
    display: 'flex',
    gap: '10px',
    fontSize: '0.72rem',
    fontWeight: 600,
    fontFamily: 'monospace',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    whiteSpace: 'nowrap',
  },
  reticleOverlay: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    zIndex: 5,
    pointerEvents: 'none',
    opacity: 0.5,
  },
  fallbackContainer: {
    position: 'absolute',
    inset: 0,
    backgroundColor: '#06090e',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    overflowY: 'auto',
  },
  fallbackHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    borderBottom: '1px solid #182635',
    paddingBottom: '12px',
  },
  fallbackTitle: {
    margin: 0,
    fontSize: '1.05rem',
    color: '#f8fafc',
    letterSpacing: '0.04em',
  },
  fallbackSubtitle: {
    fontSize: '0.78rem',
    color: '#94a3b8',
  },
  gridContainer: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '12px',
  },
  gridCard: {
    padding: '12px',
    borderRadius: '6px',
    border: '1px solid #182635',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  gridCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: '6px',
  },
  rankBadge: {
    fontSize: '0.75rem',
    fontWeight: 700,
    color: '#38bdf8',
  },
  confBadge: {
    fontSize: '0.75rem',
    fontWeight: 700,
    color: '#10b981',
  },
  gridCardTitle: {
    fontSize: '0.85rem',
    fontWeight: 600,
    color: '#f1f5f9',
    marginBottom: '2px',
  },
  gridCardSub: {
    fontSize: '0.7rem',
    fontFamily: 'monospace',
    color: '#94a3b8',
    marginBottom: '6px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  gridCoords: {
    fontSize: '0.72rem',
    color: '#64748b',
  },
};
