import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as maplibregl from 'maplibre-gl';
import { setWorkerUrl } from 'maplibre-gl';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import 'maplibre-gl/dist/maplibre-gl.css';

setWorkerUrl(maplibreWorkerUrl);
import { ApiClient } from '../api/client';
import { EvidenceFirstCandidate } from '../types/api';
import {
  SatelliteIcon,
  LayersIcon,
  CalendarIcon,
  CrosshairIcon,
  ShieldIcon,
} from './Icons';

export type ComparisonMode =
  | 'SINGLE'
  | 'SWIPE'
  | 'OPACITY'
  | 'SPYGLASS'
  | 'SIDE_BY_SIDE'
  | 'FLICKER'
  | 'DIFFERENCE'
  | 'CHANGE_MASK';

interface MapViewerProps {
  candidates: EvidenceFirstCandidate[];
  selectedCandidate: EvidenceFirstCandidate | null;
  onSelectCandidate: (candidate: EvidenceFirstCandidate) => void;
  activeEpoch?: 'T1' | 'T2';
  onEpochChange?: (epoch: 'T1' | 'T2') => void;
}

export const MapViewer: React.FC<MapViewerProps> = ({
  candidates,
  selectedCandidate,
  onSelectCandidate,
  activeEpoch: controlledEpoch,
  onEpochChange,
}) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [showAllFootprints, setShowAllFootprints] = useState<boolean>(true);

  const activeEpoch = controlledEpoch !== undefined ? controlledEpoch : 'T1';
  const handleEpochChange = (epoch: 'T1' | 'T2') => {
    if (onEpochChange) onEpochChange(epoch);
  };

  // 7 Comparison Modes State
  const [comparisonMode, setComparisonMode] = useState<ComparisonMode>('SWIPE');
  const [swipePos, setSwipePos] = useState<number>(50); // percentage 0 - 100
  const [opacityVal, setOpacityVal] = useState<number>(0.5); // 0.0 - 1.0
  const [spyglassPos, setSpyglassPos] = useState<{ x: number; y: number }>({ x: 300, y: 240 });
  const [spyglassRadius, setSpyglassRadius] = useState<number>(110);
  const [isFlickering, setIsFlickering] = useState<boolean>(true);
  const [flickerIntervalMs, setFlickerIntervalMs] = useState<number>(500);
  const [flickerFrame, setFlickerFrame] = useState<'T1' | 'T2'>('T1');
  const [isDraggingSwipe, setIsDraggingSwipe] = useState<boolean>(false);
  const [isDraggingSpyglass, setIsDraggingSpyglass] = useState<boolean>(false);

  const containerRef = useRef<HTMLDivElement>(null);

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

    // Spatial deduplication
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

      // Semi-transparent footprint fill
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

      // Footprint borders
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

      // Highlight border for SELECTED candidate
      map.addLayer({
        id: lineSelectedLayerId,
        type: 'line',
        source: sourceId,
        filter: ['==', ['get', 'isSelected'], 1],
        layout: {
          visibility: 'visible',
        },
        paint: {
          'line-color': '#facc15',
          'line-width': 2.5,
          'line-opacity': 0.95,
        },
      });

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
    }

    // Raster Underlay
    let rasterUrl: string | null = null;
    let rasterCoords:
      | [[number, number], [number, number], [number, number], [number, number]]
      | null = null;

    if (selectedCandidate) {
      const isChange =
        selectedCandidate.target_type === 'CHANGE' ||
        Boolean(selectedCandidate.evidence?.before_scene_preview_url);

      if (isChange) {
        rasterUrl =
          activeEpoch === 'T1'
            ? selectedCandidate.evidence?.before_scene_preview_url || selectedCandidate.evidence?.preview_url || null
            : selectedCandidate.evidence?.after_scene_preview_url || selectedCandidate.evidence?.scene_preview_url || selectedCandidate.evidence?.preview_url || null;
      } else {
        rasterUrl =
          selectedCandidate.evidence?.scene_preview_url ||
          selectedCandidate.evidence?.preview_url ||
          (selectedCandidate.which?.tile_id
            ? ApiClient.getTilePreviewUrl(selectedCandidate.which.tile_id)
            : null);
      }

      rasterCoords =
        selectedCandidate.evidence?.scene_coordinates ||
        selectedCandidate.where?.coordinates ||
        (selectedCandidate.where?.bbox
          ? [
              [selectedCandidate.where.bbox[0], selectedCandidate.where.bbox[3]],
              [selectedCandidate.where.bbox[2], selectedCandidate.where.bbox[3]],
              [selectedCandidate.where.bbox[2], selectedCandidate.where.bbox[1]],
              [selectedCandidate.where.bbox[0], selectedCandidate.where.bbox[1]],
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
          if (map.getLayer(rasterLayerId)) map.removeLayer(rasterLayerId);
          if (map.getSource(rasterSourceId)) map.removeSource(rasterSourceId);
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
      if (map.getLayer(rasterLayerId)) map.removeLayer(rasterLayerId);
      if (map.getSource(rasterSourceId)) map.removeSource(rasterSourceId);
    }

    // Auto-fit camera
    if (selectedCandidate) {
      const targetBbox = selectedCandidate.evidence?.scene_bbox || selectedCandidate.where.bbox;
      const [minLon, minLat, maxLon, maxLat] = targetBbox;
      map.fitBounds([[minLon, minLat], [maxLon, maxLat]], { padding: 40, maxZoom: 15, duration: 800 });
    }
  }, [candidates, selectedCandidate, mapLoaded, onSelectCandidate, activeEpoch]);

  // Flicker interval timer
  useEffect(() => {
    if (comparisonMode !== 'FLICKER' || !isFlickering) return;
    const interval = setInterval(() => {
      setFlickerFrame((prev) => {
        const next = prev === 'T1' ? 'T2' : 'T1';
        handleEpochChange(next);
        return next;
      });
    }, flickerIntervalMs);
    return () => clearInterval(interval);
  }, [comparisonMode, isFlickering, flickerIntervalMs]);

  // Mouse handlers for swipe and spyglass drag
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (isDraggingSwipe) {
      const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
      setSwipePos(pct);
    }

    if (isDraggingSpyglass || comparisonMode === 'SPYGLASS') {
      setSpyglassPos({ x, y });
    }
  }, [isDraggingSwipe, isDraggingSpyglass, comparisonMode]);

  const handleMouseUp = useCallback(() => {
    setIsDraggingSwipe(false);
    setIsDraggingSpyglass(false);
  }, []);

  const currentCandidate = selectedCandidate || (candidates.length > 0 ? candidates[0] : null);
  const isBitemporal =
    selectedCandidate?.target_type === 'CHANGE' ||
    Boolean(selectedCandidate?.evidence?.before_date || selectedCandidate?.evidence?.before_scene_preview_url);

  const t1Url = selectedCandidate?.evidence?.before_scene_preview_url || selectedCandidate?.evidence?.preview_url;
  const t2Url = selectedCandidate?.evidence?.after_scene_preview_url || selectedCandidate?.evidence?.scene_preview_url || selectedCandidate?.evidence?.preview_url;
  const maskUrl = selectedCandidate?.evidence?.mask_url || (selectedCandidate?.target_id ? ApiClient.getChangeMaskUrl(selectedCandidate.target_id) : '');

  const beforeDateStr = selectedCandidate?.evidence?.before_date || '2023-02-03';
  const afterDateStr = selectedCandidate?.evidence?.after_date || '2024-11-29';

  return (
    <div
      ref={containerRef}
      style={styles.container}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {mapError && <div style={styles.errorAlert}>{mapError}</div>}
      {/* Top Map Header Overlay Bar */}
      <div style={styles.overlayBar}>
        {/* Left: AOI & Satellite Sensor Context */}
        <div style={styles.aoiBadge}>
          <SatelliteIcon size={16} color="#38bdf8" />
          <span style={styles.dot} />
          <span style={styles.aoiText}>
            {currentCandidate && currentCandidate.where.centroid[1] > 25
              ? 'Jewar Airport Corridor (T43RGM • EPSG:32643)'
              : 'Western Ghats, MH (EPSG:32643)'}
          </span>
          <span style={styles.airGapTag}>
            <ShieldIcon size={10} color="#10b981" style={{ marginRight: '3px' }} />
            AIR-GAPPED
          </span>
        </div>

        {/* Center: 7 Comparison Modes Toolbar */}
        {isBitemporal && (
          <div style={styles.modeButtonGroup}>
            {(
              [
                { id: 'SINGLE', label: 'SINGLE' },
                { id: 'SWIPE', label: 'SWIPE ⬌' },
                { id: 'OPACITY', label: 'OPACITY ◐' },
                { id: 'SPYGLASS', label: 'SPYGLASS ⊙' },
                { id: 'SIDE_BY_SIDE', label: 'SIDE-BY-SIDE ◫' },
                { id: 'FLICKER', label: 'FLICKER ⚡' },
                { id: 'DIFFERENCE', label: 'DIFF Δ' },
                { id: 'CHANGE_MASK', label: 'MASK ▦' },
              ] as { id: ComparisonMode; label: string }[]
            ).map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setComparisonMode(m.id)}
                style={{
                  ...styles.modeBtn,
                  backgroundColor: comparisonMode === m.id ? '#38bdf8' : '#0f1722',
                  color: comparisonMode === m.id ? '#06090e' : '#94a3b8',
                  borderColor: comparisonMode === m.id ? '#38bdf8' : '#1e293b',
                  fontWeight: comparisonMode === m.id ? 800 : 500,
                }}
              >
                {m.label}
              </button>
            ))}
          </div>
        )}

        {/* Right: Controls */}
        <div style={styles.headerControls}>
          <button
            type="button"
            onClick={() => setShowAllFootprints((prev) => !prev)}
            style={styles.toggleBtn}
            title="Toggle candidate footprint outlines"
          >
            <LayersIcon size={13} color={showAllFootprints ? '#38bdf8' : '#64748b'} />
            <span>FOOTPRINTS {showAllFootprints ? 'ON' : 'OFF'}</span>
          </button>
        </div>
      </div>

      {/* Mode Specific Interactive Control Bar */}
      {isBitemporal && comparisonMode !== 'SINGLE' && (
        <div style={styles.subControlBar}>
          {comparisonMode === 'SWIPE' && (
            <div style={styles.subControlRow}>
              <span style={styles.subControlLabel}>SWIPE DIVIDER:</span>
              <input
                type="range"
                min={0}
                max={100}
                value={swipePos}
                onChange={(e) => setSwipePos(Number(e.target.value))}
                style={styles.slider}
              />
              <span style={styles.subControlVal}>{Math.round(swipePos)}%</span>
              <span style={styles.subControlHint}>[T1 Before ({beforeDateStr}) ◀ | ▶ T2 After ({afterDateStr})]</span>
            </div>
          )}

          {comparisonMode === 'OPACITY' && (
            <div style={styles.subControlRow}>
              <span style={styles.subControlLabel}>T2 OPACITY CROSS-FADER:</span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={opacityVal}
                onChange={(e) => setOpacityVal(Number(e.target.value))}
                style={styles.slider}
              />
              <span style={styles.subControlVal}>{Math.round(opacityVal * 100)}%</span>
              <span style={styles.subControlHint}>[0% = Pure T1 Before | 100% = Pure T2 After]</span>
            </div>
          )}

          {comparisonMode === 'SPYGLASS' && (
            <div style={styles.subControlRow}>
              <span style={styles.subControlLabel}>LOUPE RADIUS:</span>
              <input
                type="range"
                min={60}
                max={220}
                value={spyglassRadius}
                onChange={(e) => setSpyglassRadius(Number(e.target.value))}
                style={styles.slider}
              />
              <span style={styles.subControlVal}>{spyglassRadius}px</span>
              <span style={styles.subControlHint}>Move cursor over map to reveal T2 Post-Event inside lens</span>
            </div>
          )}

          {comparisonMode === 'FLICKER' && (
            <div style={styles.subControlRow}>
              <button
                type="button"
                onClick={() => setIsFlickering(!isFlickering)}
                style={styles.flickerToggleBtn}
              >
                {isFlickering ? '⏸ PAUSE FLICKER' : '▶ RESUME FLICKER'}
              </button>
              <span style={styles.subControlLabel}>RATE:</span>
              <select
                value={flickerIntervalMs}
                onChange={(e) => setFlickerIntervalMs(Number(e.target.value))}
                style={styles.select}
              >
                <option value={750}>0.75s (Slow)</option>
                <option value={500}>0.50s (Nominal)</option>
                <option value={250}>0.25s (Fast)</option>
                <option value={150}>0.15s (Rapid)</option>
              </select>
              <span style={{ ...styles.subControlVal, color: flickerFrame === 'T1' ? '#38bdf8' : '#10b981' }}>
                ACTIVE: {flickerFrame === 'T1' ? `T1 (${beforeDateStr})` : `T2 (${afterDateStr})`}
              </span>
            </div>
          )}

          {comparisonMode === 'DIFFERENCE' && (
            <div style={styles.subControlRow}>
              <span style={styles.subControlLabel}>SPECTRAL DIFFERENCE BLEND:</span>
              <span style={styles.subControlHint}>
                Absolute delta |T2 - T1| with high-contrast luminance inversion. Alterations and new pavement glow brightly.
              </span>
            </div>
          )}

          {comparisonMode === 'CHANGE_MASK' && (
            <div style={styles.subControlRow}>
              <span style={styles.subControlLabel}>THRESHOLDED CHANGE MASK:</span>
              <span style={styles.subControlHint}>
                Pure-NumPy 8-connected component filter & Otsu thresholded binary mask.
              </span>
            </div>
          )}
        </div>
      )}

      {/* MapLibre Canvas Container */}
      <div ref={mapContainer} style={styles.mapCanvas} />

      {/* Interactive Overlays for Advanced Comparison Modes */}
      {isBitemporal && t1Url && t2Url && (
        <>
          {/* Mode 1: SWIPE Overlay */}
          {comparisonMode === 'SWIPE' && (
            <div style={styles.swipeContainer}>
              {/* T2 Clip Layer */}
              <div
                style={{
                  ...styles.swipeLayer,
                  clipPath: `inset(0 0 0 ${swipePos}%)`,
                }}
              >
                <img src={t2Url} alt="T2 After" style={styles.fullImg} />
                <span style={styles.swipeBadgeRight}>T2 AFTER ({afterDateStr})</span>
              </div>

              {/* T1 Under Layer */}
              <div
                style={{
                  ...styles.swipeLayer,
                  clipPath: `inset(0 ${100 - swipePos}% 0 0)`,
                  zIndex: 2,
                }}
              >
                <img src={t1Url} alt="T1 Before" style={styles.fullImg} />
                <span style={styles.swipeBadgeLeft}>T1 BEFORE ({beforeDateStr})</span>
              </div>

              {/* Draggable Divider Handle */}
              <div
                style={{
                  ...styles.swipeDivider,
                  left: `${swipePos}%`,
                }}
                onMouseDown={() => setIsDraggingSwipe(true)}
              >
                <div style={styles.dividerLine} />
                <div style={styles.dividerHandle}>
                  <span>⬌</span>
                </div>
              </div>
            </div>
          )}

          {/* Mode 2: OPACITY Cross-fade Overlay */}
          {comparisonMode === 'OPACITY' && (
            <div style={styles.opacityContainer}>
              <img src={t1Url} alt="T1 Base" style={styles.opacityImg} />
              <img
                src={t2Url}
                alt="T2 Overlay"
                style={{
                  ...styles.opacityImg,
                  opacity: opacityVal,
                }}
              />
              <div style={styles.opacityHud}>
                <span>T1: {Math.round((1 - opacityVal) * 100)}%</span>
                <span>T2: {Math.round(opacityVal * 100)}%</span>
              </div>
            </div>
          )}

          {/* Mode 3: SPYGLASS / LOUPE Overlay */}
          {comparisonMode === 'SPYGLASS' && (
            <div style={styles.spyglassContainer}>
              {/* Base T1 Image */}
              <img src={t1Url} alt="T1 Background" style={styles.spyglassBaseImg} />

              {/* Circular Loupe revealing T2 */}
              <div
                style={{
                  ...styles.spyglassLens,
                  left: `${spyglassPos.x - spyglassRadius}px`,
                  top: `${spyglassPos.y - spyglassRadius}px`,
                  width: `${spyglassRadius * 2}px`,
                  height: `${spyglassRadius * 2}px`,
                }}
              >
                <img
                  src={t2Url}
                  alt="T2 Inside Loupe"
                  style={{
                    position: 'absolute',
                    left: `-${spyglassPos.x - spyglassRadius}px`,
                    top: `-${spyglassPos.y - spyglassRadius}px`,
                    width: containerRef.current?.clientWidth || '100%',
                    height: containerRef.current?.clientHeight || '100%',
                    objectFit: 'cover',
                  }}
                />
                <div style={styles.lensCrosshair}>
                  <CrosshairIcon size={24} color="#38bdf8" />
                </div>
                <span style={styles.lensBadge}>T2 AFTER</span>
              </div>
            </div>
          )}

          {/* Mode 4: SIDE_BY_SIDE Synchronized View */}
          {comparisonMode === 'SIDE_BY_SIDE' && (
            <div style={styles.sideBySideContainer}>
              <div style={styles.sideCol}>
                <div style={styles.sideHeader}>
                  <CalendarIcon size={12} color="#38bdf8" />
                  <span>T1 PRE-EVENT ({beforeDateStr})</span>
                </div>
                <img src={t1Url} alt="T1 Side" style={styles.sideImg} />
              </div>
              <div style={styles.sideDivider} />
              <div style={styles.sideCol}>
                <div style={styles.sideHeader}>
                  <CalendarIcon size={12} color="#10b981" />
                  <span>T2 POST-EVENT ({afterDateStr})</span>
                </div>
                <img src={t2Url} alt="T2 Side" style={styles.sideImg} />
              </div>
            </div>
          )}

          {/* Mode 5: FLICKER Rapid Alternation */}
          {comparisonMode === 'FLICKER' && (
            <div style={styles.flickerContainer}>
              <img
                src={flickerFrame === 'T1' ? t1Url : t2Url}
                alt="Flicker Frame"
                style={styles.fullImg}
              />
              <div style={styles.flickerIndicator}>
                <span
                  style={{
                    ...styles.flickerBadge,
                    backgroundColor: flickerFrame === 'T1' ? '#38bdf8' : '#10b981',
                    color: '#06090e',
                  }}
                >
                  {flickerFrame === 'T1' ? `T1 BEFORE (${beforeDateStr})` : `T2 AFTER (${afterDateStr})`}
                </span>
              </div>
            </div>
          )}

          {/* Mode 6: DIFFERENCE High-Contrast Blend */}
          {comparisonMode === 'DIFFERENCE' && (
            <div style={styles.differenceContainer}>
              <img src={t1Url} alt="T1 Base" style={styles.diffBaseImg} />
              <img src={t2Url} alt="T2 Diff" style={styles.diffBlendImg} />
              <div style={styles.diffHud}>
                <span style={styles.diffHudTitle}>SPECTRAL DIFFERENCE MAP (HIGH CONSTRAST)</span>
                <span style={styles.diffHudSub}>Neon highlights indicate genuine land-cover structural deviations</span>
              </div>
            </div>
          )}

          {/* Mode 7: CHANGE MASK Direct Thresholded Overlay */}
          {comparisonMode === 'CHANGE_MASK' && (
            <div style={styles.changeMaskContainer}>
              <img src={t2Url} alt="T2 Satellite" style={styles.fullImg} />
              {maskUrl && (
                <img
                  src={maskUrl}
                  alt="Change Mask"
                  style={styles.maskOverlayImg}
                />
              )}
              <div style={styles.maskHud}>
                <span style={styles.maskHudBadge}>OTSU CLAMPED BINARY CHANGE MASK</span>
                <span style={styles.maskHudSub}>Red clusters represent filtered 8-connected changed pixels</span>
              </div>
            </div>
          )}
        </>
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
    userSelect: 'none',
  },
  overlayBar: {
    position: 'absolute',
    top: '12px',
    left: '12px',
    right: '12px',
    zIndex: 20,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(11, 17, 24, 0.92)',
    backdropFilter: 'blur(8px)',
    border: '1px solid #1e293b',
    borderRadius: '6px',
    padding: '6px 12px',
    gap: '12px',
  },
  aoiBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '0.75rem',
    fontWeight: 700,
    color: '#e2e8f0',
  },
  dot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#10b981',
  },
  aoiText: {
    fontFamily: 'ui-monospace, monospace',
  },
  airGapTag: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '0.65rem',
    fontWeight: 800,
    color: '#10b981',
    backgroundColor: 'rgba(16, 185, 129, 0.12)',
    padding: '2px 6px',
    borderRadius: '3px',
    border: '1px solid rgba(16, 185, 129, 0.3)',
  },
  modeButtonGroup: {
    display: 'flex',
    gap: '4px',
    backgroundColor: '#0c131c',
    padding: '3px',
    borderRadius: '4px',
    border: '1px solid #1e293b',
  },
  modeBtn: {
    border: '1px solid transparent',
    padding: '4px 8px',
    fontSize: '0.68rem',
    borderRadius: '3px',
    cursor: 'pointer',
    letterSpacing: '0.04em',
    transition: 'all 0.15s ease',
  },
  headerControls: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  toggleBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#0f172a',
    border: '1px solid #334155',
    color: '#94a3b8',
    padding: '5px 10px',
    fontSize: '0.7rem',
    fontWeight: 600,
    borderRadius: '4px',
    cursor: 'pointer',
  },
  subControlBar: {
    position: 'absolute',
    top: '56px',
    left: '12px',
    right: '12px',
    zIndex: 19,
    backgroundColor: 'rgba(15, 23, 42, 0.94)',
    backdropFilter: 'blur(8px)',
    border: '1px solid #1e293b',
    borderRadius: '4px',
    padding: '6px 12px',
  },
  subControlRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    fontSize: '0.75rem',
  },
  subControlLabel: {
    color: '#94a3b8',
    fontWeight: 700,
    letterSpacing: '0.05em',
  },
  subControlVal: {
    color: '#38bdf8',
    fontWeight: 800,
    fontFamily: 'monospace',
  },
  subControlHint: {
    color: '#64748b',
    fontSize: '0.7rem',
    marginLeft: 'auto',
  },
  slider: {
    width: '140px',
    cursor: 'pointer',
  },
  select: {
    backgroundColor: '#070d19',
    border: '1px solid #334155',
    color: '#f8fafc',
    padding: '3px 8px',
    fontSize: '0.7rem',
    borderRadius: '3px',
    cursor: 'pointer',
  },
  flickerToggleBtn: {
    backgroundColor: '#38bdf8',
    color: '#06090e',
    border: 'none',
    padding: '4px 10px',
    fontSize: '0.7rem',
    fontWeight: 700,
    borderRadius: '3px',
    cursor: 'pointer',
  },
  mapCanvas: {
    width: '100%',
    height: '100%',
  },
  swipeContainer: {
    position: 'absolute',
    top: '90px',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 10,
    overflow: 'hidden',
  },
  swipeLayer: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    overflow: 'hidden',
  },
  fullImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  swipeBadgeLeft: {
    position: 'absolute',
    top: '12px',
    left: '12px',
    backgroundColor: 'rgba(6, 9, 14, 0.8)',
    color: '#38bdf8',
    border: '1px solid #38bdf8',
    padding: '4px 8px',
    fontSize: '0.7rem',
    fontWeight: 700,
    borderRadius: '3px',
  },
  swipeBadgeRight: {
    position: 'absolute',
    top: '12px',
    right: '12px',
    backgroundColor: 'rgba(6, 9, 14, 0.8)',
    color: '#10b981',
    border: '1px solid #10b981',
    padding: '4px 8px',
    fontSize: '0.7rem',
    fontWeight: 700,
    borderRadius: '3px',
  },
  swipeDivider: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: '30px',
    transform: 'translateX(-50%)',
    zIndex: 15,
    cursor: 'ew-resize',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  dividerLine: {
    width: '2px',
    height: '100%',
    backgroundColor: '#facc15',
    boxShadow: '0 0 8px rgba(250, 204, 21, 0.8)',
  },
  dividerHandle: {
    position: 'absolute',
    top: '50%',
    transform: 'translateY(-50%)',
    width: '26px',
    height: '26px',
    borderRadius: '50%',
    backgroundColor: '#facc15',
    color: '#06090e',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '0.8rem',
    fontWeight: 900,
    boxShadow: '0 0 10px rgba(0,0,0,0.6)',
  },
  opacityContainer: {
    position: 'absolute',
    top: '90px',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 10,
  },
  opacityImg: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  opacityHud: {
    position: 'absolute',
    bottom: '16px',
    left: '16px',
    backgroundColor: 'rgba(15, 23, 42, 0.85)',
    padding: '6px 12px',
    borderRadius: '4px',
    border: '1px solid #334155',
    display: 'flex',
    gap: '16px',
    fontSize: '0.75rem',
    fontWeight: 700,
    color: '#f8fafc',
  },
  spyglassContainer: {
    position: 'absolute',
    top: '90px',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 10,
    overflow: 'hidden',
  },
  spyglassBaseImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  spyglassLens: {
    position: 'absolute',
    borderRadius: '50%',
    overflow: 'hidden',
    border: '3px solid #38bdf8',
    boxShadow: '0 0 20px rgba(56, 189, 248, 0.6), inset 0 0 15px rgba(0,0,0,0.5)',
    zIndex: 12,
  },
  lensCrosshair: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    pointerEvents: 'none',
    opacity: 0.7,
  },
  lensBadge: {
    position: 'absolute',
    bottom: '8px',
    left: '50%',
    transform: 'translateX(-50%)',
    backgroundColor: 'rgba(6, 9, 14, 0.85)',
    color: '#10b981',
    border: '1px solid #10b981',
    fontSize: '0.6rem',
    fontWeight: 800,
    padding: '1px 6px',
    borderRadius: '2px',
  },
  sideBySideContainer: {
    position: 'absolute',
    top: '90px',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 10,
    display: 'flex',
  },
  sideCol: {
    flex: 1,
    height: '100%',
    position: 'relative',
    overflow: 'hidden',
  },
  sideDivider: {
    width: '2px',
    backgroundColor: '#1e293b',
  },
  sideHeader: {
    position: 'absolute',
    top: '8px',
    left: '8px',
    zIndex: 12,
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: 'rgba(15, 23, 42, 0.85)',
    padding: '4px 8px',
    borderRadius: '3px',
    border: '1px solid #334155',
    fontSize: '0.7rem',
    fontWeight: 700,
    color: '#f8fafc',
  },
  sideImg: {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  flickerContainer: {
    position: 'absolute',
    top: '90px',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 10,
  },
  flickerIndicator: {
    position: 'absolute',
    top: '16px',
    left: '16px',
    zIndex: 15,
  },
  flickerBadge: {
    padding: '6px 12px',
    fontSize: '0.8rem',
    fontWeight: 800,
    borderRadius: '4px',
    letterSpacing: '0.05em',
  },
  differenceContainer: {
    position: 'absolute',
    top: '90px',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 10,
  },
  diffBaseImg: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  },
  diffBlendImg: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    mixBlendMode: 'difference',
    filter: 'contrast(200%) brightness(140%)',
  },
  diffHud: {
    position: 'absolute',
    bottom: '16px',
    left: '16px',
    backgroundColor: 'rgba(15, 23, 42, 0.9)',
    border: '1px solid #38bdf8',
    padding: '8px 12px',
    borderRadius: '4px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  diffHudTitle: {
    color: '#38bdf8',
    fontSize: '0.75rem',
    fontWeight: 800,
  },
  diffHudSub: {
    color: '#94a3b8',
    fontSize: '0.7rem',
  },
  changeMaskContainer: {
    position: 'absolute',
    top: '90px',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 10,
  },
  maskOverlayImg: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    opacity: 0.85,
    mixBlendMode: 'screen',
  },
  maskHud: {
    position: 'absolute',
    bottom: '16px',
    left: '16px',
    backgroundColor: 'rgba(15, 23, 42, 0.9)',
    border: '1px solid #ef4444',
    padding: '8px 12px',
    borderRadius: '4px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  maskHudBadge: {
    color: '#f87171',
    fontSize: '0.75rem',
    fontWeight: 800,
  },
  maskHudSub: {
    color: '#94a3b8',
    fontSize: '0.7rem',
  },
};
