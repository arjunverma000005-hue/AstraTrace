import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { ApiClient } from '../api/client';
import { EvidenceFirstCandidate } from '../types/api';

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
  const [focusSingleTile, setFocusSingleTile] = useState<boolean>(false);

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
              'background-color': '#0b1120',
            },
          },
        ],
      };

      const map = new maplibregl.Map({
        container: mapContainer.current,
        style: offlineStyle,
        center: [73.59, 18.96], // Default Western Ghats AOI
        zoom: 11,
        attributionControl: false,
      });

      map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');
      map.addControl(
        new maplibregl.ScaleControl({ maxWidth: 100, unit: 'metric' }),
        'bottom-left',
      );

      map.on('load', () => {
        setMapLoaded(true);
      });

      map.on('error', (e: any) => {
        // Log map warnings without crashing
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

  // Update candidate vector layers when candidates or selection changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const sourceId = 'candidates-source';
    const fillLayerId = 'candidates-fill';
    const lineLayerId = 'candidates-line';
    const rasterSourceId = 'selected-candidate-raster-source';
    const rasterLayerId = 'selected-candidate-raster-layer';

    // Filter and deduplicate candidates by spatial footprint
    let displayCandidates = candidates;
    if (focusSingleTile && selectedCandidate) {
      displayCandidates = [selectedCandidate];
    } else {
      // Spatial deduplication: if multiple temporal observations share the same bbox, retain one feature
      const seenBoxes = new Set<string>();
      const deduped: EvidenceFirstCandidate[] = [];
      for (const c of candidates) {
        const boxKey = c.where?.bbox ? c.where.bbox.map((v) => v.toFixed(5)).join(':') : (c.target_id || c.candidate_id);
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
      displayCandidates = deduped;
    }

    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: displayCandidates.map((c) => {
        const isSelected =
          selectedCandidate &&
          ((c.candidate_id && selectedCandidate.candidate_id === c.candidate_id) ||
           (c.target_id && selectedCandidate.target_id === c.target_id) ||
           (c.where?.bbox && selectedCandidate.where?.bbox &&
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

      // Semi-transparent footprint fill
      map.addLayer({
        id: fillLayerId,
        type: 'fill',
        source: sourceId,
        paint: {
          'fill-color': [
            'case',
            ['==', ['get', 'review_status'], 'CONFIRMED'],
            '#10b981', // green
            ['==', ['get', 'review_status'], 'REJECTED'],
            '#ef4444', // red
            ['==', ['get', 'review_status'], 'FLAGGED_FOR_INSPECTION'],
            '#f59e0b', // amber
            '#3b82f6', // blue (pending)
          ],
          'fill-opacity': [
            'case',
            ['==', ['get', 'isSelected'], 1],
            0.15,
            0.25,
          ],
        },
      });

      // High-contrast footprint border
      map.addLayer({
        id: lineLayerId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': [
            'case',
            ['==', ['get', 'isSelected'], 1],
            '#facc15', // yellow highlight
            '#38bdf8', // light blue
          ],
          'line-width': [
            'case',
            ['==', ['get', 'isSelected'], 1],
            3,
            1.5,
          ],
        },
      });

      // Click to select candidate
      map.on('click', fillLayerId, (e: any) => {
        if (e.features && e.features[0]) {
          const cid = e.features[0].properties?.candidate_id;
          const tid = e.features[0].properties?.target_id;
          const match = candidates.find(
            (c) => (cid && (c.candidate_id === cid || c.target_id === cid)) ||
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

    // Dynamic Sentinel-2 optical raster underlay for selected candidate
    const bbox = selectedCandidate?.where?.bbox;
    const hasValidBbox =
      Array.isArray(bbox) &&
      bbox.length === 4 &&
      bbox.every((v) => typeof v === 'number' && !isNaN(v));

    const tileId = selectedCandidate?.which?.tile_id || selectedCandidate?.target_id;
    const rasterUrl =
      selectedCandidate?.evidence?.preview_url ||
      (tileId ? ApiClient.getTilePreviewUrl(tileId) : null);

    if (selectedCandidate && hasValidBbox && rasterUrl) {
      const coordinates: [
        [number, number],
        [number, number],
        [number, number],
        [number, number]
      ] = selectedCandidate.where.coordinates || [
        [bbox[0], bbox[3]], // Top-Left: [minLon, maxLat]
        [bbox[2], bbox[3]], // Top-Right: [maxLon, maxLat]
        [bbox[2], bbox[1]], // Bottom-Right: [maxLon, minLat]
        [bbox[0], bbox[1]], // Bottom-Left: [minLon, minLat]
      ];

      const existingRasterSource = map.getSource(rasterSourceId) as maplibregl.ImageSource | undefined;
      if (existingRasterSource && typeof existingRasterSource.updateImage === 'function') {
        try {
          existingRasterSource.updateImage({
            url: rasterUrl,
            coordinates,
          });
          if (!map.getLayer(rasterLayerId)) {
            const beforeLayer = map.getLayer(fillLayerId) ? fillLayerId : undefined;
            map.addLayer(
              {
                id: rasterLayerId,
                type: 'raster',
                source: rasterSourceId,
                paint: {
                  'raster-opacity': 0.95,
                  'raster-fade-duration': 300,
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
            coordinates,
          });
          const beforeLayer = map.getLayer(fillLayerId) ? fillLayerId : undefined;
          map.addLayer(
            {
              id: rasterLayerId,
              type: 'raster',
              source: rasterSourceId,
              paint: {
                'raster-opacity': 0.95,
                'raster-fade-duration': 300,
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

    // Auto-fit to selected candidate or all candidates
    if (selectedCandidate) {
      const [minLon, minLat, maxLon, maxLat] = selectedCandidate.where.bbox;
      map.fitBounds(
        [
          [minLon, minLat],
          [maxLon, maxLat],
        ],
        { padding: 40, maxZoom: 16.5, duration: 800 },
      );
    } else if (candidates.length > 0) {
      const primaryCluster = candidates.filter(
        (c) => (candidates[0].where.centroid[1] > 25 ? c.where.centroid[1] > 25 : c.where.centroid[1] <= 25),
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
        { padding: 50, maxZoom: 14, duration: 800 },
      );
    }
  }, [candidates, selectedCandidate, mapLoaded, onSelectCandidate, focusSingleTile]);

  const currentCandidate = selectedCandidate || (candidates.length > 0 ? candidates[0] : null);
  const aoiLabel =
    currentCandidate && currentCandidate.where.centroid[1] > 25
      ? 'AOI: Jewar Airport Corridor (T43RGM • EPSG:32643)'
      : 'AOI: Western Ghats, MH (EPSG:32643 / EPSG:4326)';

  return (
    <div style={styles.container}>
      {/* Map Header Overlay */}
      <div style={styles.overlayBar}>
        <div style={styles.aoiBadge}>
          <span style={styles.dot} />
          <span>{aoiLabel}</span>
        </div>
        <div style={styles.headerControls}>
          <button
            type="button"
            onClick={() => setFocusSingleTile((prev) => !prev)}
            style={{
              ...styles.focusBtn,
              backgroundColor: focusSingleTile ? '#facc15' : 'rgba(30, 41, 59, 0.9)',
              color: focusSingleTile ? '#0f172a' : '#94a3b8',
              borderColor: focusSingleTile ? '#eab308' : '#475569',
            }}
            title="Toggle single selected tile isolation mode"
          >
            {focusSingleTile ? '🎯 Single Tile Focused' : '🔲 All Footprints'}
          </button>
          <div style={styles.legend}>
            <span style={{ ...styles.legendItem, color: '#38bdf8' }}>■ Pending</span>
            <span style={{ ...styles.legendItem, color: '#10b981' }}>■ Confirmed</span>
            <span style={{ ...styles.legendItem, color: '#f59e0b' }}>■ Flagged</span>
            <span style={{ ...styles.legendItem, color: '#ef4444' }}>■ Rejected</span>
          </div>
        </div>
      </div>

      {/* MapLibre Canvas Container */}
      <div ref={mapContainer} style={styles.mapCanvas} />

      {/* Resilient Tactical Fallback if WebGL is unavailable */}
      {mapError && (
        <div style={styles.fallbackContainer}>
          <div style={styles.fallbackHeader}>
            <span style={styles.fallbackIcon}>🛰️</span>
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
    backgroundColor: '#0b1120',
    overflow: 'hidden',
    borderRadius: '8px',
    border: '1px solid #1e293b',
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
    padding: '8px 14px',
    backgroundColor: 'rgba(15, 23, 42, 0.88)',
    backdropFilter: 'blur(8px)',
    borderRadius: '6px',
    border: '1px solid rgba(51, 65, 85, 0.8)',
    pointerEvents: 'none',
  },
  aoiBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#94a3b8',
    letterSpacing: '0.04em',
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: '#10b981',
    boxShadow: '0 0 8px #10b981',
  },
  headerControls: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
    pointerEvents: 'auto',
  },
  focusBtn: {
    pointerEvents: 'auto',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    fontSize: '0.72rem',
    fontWeight: 600,
    borderRadius: '4px',
    border: '1px solid',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  legend: {
    display: 'flex',
    gap: '12px',
    fontSize: '0.75rem',
    fontWeight: 600,
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  fallbackContainer: {
    position: 'absolute',
    inset: 0,
    backgroundColor: '#0f172a',
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
    borderBottom: '1px solid #334155',
    paddingBottom: '12px',
  },
  fallbackIcon: {
    fontSize: '1.8rem',
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
    border: '1px solid #334155',
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
