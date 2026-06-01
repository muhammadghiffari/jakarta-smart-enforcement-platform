import { motion } from 'framer-motion';
import {
  Activity,
  ArrowUpRight,
  CheckCircle2,
  Clock3,
  Crosshair,
  MapPin,
  RadioTower,
  Route,
  SlidersHorizontal,
} from 'lucide-react';
import { useMemo, useState, useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

import { demoDeployments, demoHotspots, hourlyViolations, violationMix } from '../lib/demoContent';
import CCTVModal from '../components/CCTVModal';

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, delay } },
});

const stagger = { animate: { transition: { staggerChildren: 0.06 } } };
const itemFade = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.32 } },
};

// ── Violation Map ─────────────────────────────────────────────────────────────

export function ViolationMapPage() {
  const [selected, setSelected] = useState(demoHotspots[0]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedZone, setSelectedZone] = useState<{name: string, type: string} | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  const maxCount = Math.max(...demoHotspots.map((h) => h.count));

  // Coordinate mapping for all corridors in Jakarta
  const HOTSPOT_COORDS: Record<string, [number, number]> = {
    'Bundaran HI': [106.8230, -6.1950],
    'Sudirman': [106.8224, -6.2030],
    'Kuningan': [106.8326, -6.2240],
    'Semanggi': [106.8170, -6.2190],
    'Monas': [106.8272, -6.1754],
  };

  const handleVisit = (hs: typeof demoHotspots[0]) => {
    setSelected(hs);
    const coords = HOTSPOT_COORDS[hs.corridor];
    if (coords && mapRef.current) {
      mapRef.current.flyTo({
        center: coords,
        zoom: 14.8, // Zoom in to see the details of the zone
        speed: 1.2,
        curve: 1.42,
        essential: true
      });
    }
  };

  const handleResetView = () => {
    if (mapRef.current) {
      mapRef.current.flyTo({
        center: [106.8228, -6.1980],
        zoom: 12.2, // Zoom out to show all corridors
        speed: 1.0,
        essential: true
      });
    }
  };

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Initialize MapLibre GL
    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [106.8228, -6.1980], // Centered between Monas and Kuningan
      zoom: 12.2, // Zoomed out to show the city overview
      scrollZoom: true,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    mapRef.current = map;

    map.on('load', () => {
      // Add Pilot Zones GeoJSON Source
      map.addSource('zones-pilot', {
        type: 'geojson',
        data: '/zones_pilot.geojson'
      });

      // Add fill layer for the zones
      map.addLayer({
        id: 'zones-fill',
        type: 'fill',
        source: 'zones-pilot',
        paint: {
          'fill-color': [
            'match',
            ['get', 'zone_type'],
            'BUSWAY_LANE', '#ff0055',
            'BICYCLE_LANE', '#00d4ff',
            'NO_PARKING', '#ffaa00',
            /* other */ '#333333'
          ],
          'fill-opacity': 0.15
        }
      });

      // Add line layer for zone borders
      map.addLayer({
        id: 'zones-line',
        type: 'line',
        source: 'zones-pilot',
        paint: {
          'line-color': [
            'match',
            ['get', 'zone_type'],
            'BUSWAY_LANE', '#ff0055',
            'BICYCLE_LANE', '#00d4ff',
            'NO_PARKING', '#ffaa00',
            /* other */ '#333333'
          ],
          'line-width': 2,
          'line-dasharray': [2, 2]
        }
      });

      // Add click listener
      map.on('click', 'zones-fill', (e) => {
        if (!e.features || e.features.length === 0) return;
        const feature = e.features[0];
        
        setSelectedZone({
          name: feature.properties.name || 'Unknown Zone',
          type: feature.properties.zone_type || 'GENERAL'
        });
        setIsModalOpen(true);
      });

      // Change cursor to pointer when hovering over zones
      map.on('mouseenter', 'zones-fill', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'zones-fill', () => {
        map.getCanvas().style.cursor = '';
      });
    });

    return () => {
      map.remove();
    };
  }, []);

  const handleSelect = (hs: typeof demoHotspots[0]) => {
    handleVisit(hs);
    
    // Smoothly scroll the window back up to the map so the user can see the transition
    const mapElement = document.getElementById('live');
    if (mapElement) {
      mapElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <>
      <style>{`
        .quick-visit-panel {
          position: absolute;
          top: 16px;
          left: 16px;
          z-index: 10;
          background: rgba(10, 15, 30, 0.85);
          padding: 12px;
          border-radius: 8px;
          backdrop-filter: blur(10px);
          border: 1px solid rgba(0, 212, 255, 0.25);
          width: 220px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.5);
          transition: all 0.3s ease;
        }
        .quick-visit-header {
          margin: 0 0 8px 0;
          font-size: 0.8rem;
          color: #00d4ff;
          text-transform: uppercase;
          letter-spacing: 1px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .quick-visit-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .quick-visit-btn {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          color: rgba(255, 255, 255, 0.8);
          padding: 8px 10px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.75rem;
          text-align: left;
          transition: all 0.2s ease;
          outline: none;
        }
        .quick-visit-btn:hover {
          background: rgba(255, 255, 255, 0.08);
          border-color: rgba(255, 255, 255, 0.15);
          color: #ffffff;
        }
        .quick-visit-btn.active {
          background: rgba(0, 212, 255, 0.15);
          border-color: rgba(0, 212, 255, 0.5);
          color: #ffffff;
          box-shadow: 0 0 10px rgba(0, 212, 255, 0.1);
        }
        .quick-visit-btn-reset {
          background: none;
          border: none;
          color: rgba(255,255,255,0.6);
          cursor: pointer;
          font-size: 0.65rem;
          text-transform: uppercase;
          text-decoration: underline;
          outline: none;
          padding: 2px 6px;
          border-radius: 3px;
          transition: all 0.2s ease;
        }
        .quick-visit-btn-reset:hover {
          color: #ffffff;
          background: rgba(255, 255, 255, 0.1);
        }

        @media (max-width: 768px) {
          .quick-visit-panel {
            width: calc(100% - 32px);
            max-width: none;
            top: auto;
            bottom: 120px; /* position above legend */
            left: 16px;
            right: 16px;
            padding: 8px 12px;
          }
          .quick-visit-header {
            margin-bottom: 6px;
          }
          .quick-visit-list {
            flex-direction: row;
            overflow-x: auto;
            gap: 8px;
            padding-bottom: 4px;
            scrollbar-width: none;
          }
          .quick-visit-list::-webkit-scrollbar {
            display: none;
          }
          .quick-visit-btn {
            flex-shrink: 0;
            padding: 6px 10px;
          }
        }
      `}</style>

      <CCTVModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        zoneInfo={selectedZone} 
      />

      <motion.section className="ops-hero ops-hero-dark" {...fadeUp(0)}>
        <div className="ops-hero-copy">
          <p className="eyebrow">Spatial risk view</p>
          <h1>Jakarta corridors, ranked by enforcement urgency.</h1>
          <p>
            H3 hotspot aggregation turns recent violations into a patrol-ready map with clear
            priority, corridor context, and suggested response windows.
          </p>
        </div>
        <div className="hero-stat-panel" aria-label="Map summary">
          <span>Active hotspots</span>
          <strong>{demoHotspots.length}</strong>
          <small style={{ color: 'var(--text-muted)', fontSize: 12 }}>Last 60 minutes</small>
        </div>
      </motion.section>

      <section className="content-band" id="live">
        <div className="map-layout">
          {/* City map */}
          <motion.div
            className="city-map"
            aria-label="Violation hotspot map"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            ref={mapContainerRef}
            style={{ position: 'relative', width: '100%', height: '100%', minHeight: '580px', overflow: 'hidden' }}
          >
            {/* Quick Visit Panel Overlay */}
            <div className="quick-visit-panel">
               <h4 className="quick-visit-header">
                 <span>Visit Locations</span>
                 <button onClick={handleResetView} className="quick-visit-btn-reset">Reset</button>
               </h4>
               <div className="quick-visit-list">
                 {demoHotspots.map((hs) => {
                   const isSelected = selected.id === hs.id;
                   return (
                     <button
                       key={hs.id}
                       onClick={() => handleVisit(hs)}
                       className={`quick-visit-btn ${isSelected ? 'active' : ''}`}
                     >
                       <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                         <MapPin size={12} style={{ color: isSelected ? '#00d4ff' : 'rgba(255,255,255,0.4)' }} />
                         {hs.corridor}
                       </span>
                       <span style={{ fontSize: '0.65rem', background: 'rgba(255,255,255,0.1)', padding: '2px 4px', borderRadius: '3px', color: 'rgba(255,255,255,0.6)' }}>
                         {hs.risk}
                       </span>
                     </button>
                   );
                 })}
               </div>
            </div>

            {/* Legend */}
            <div style={{ position: 'absolute', bottom: 16, left: 16, zIndex: 10, background: 'rgba(0,0,0,0.6)', padding: '12px', borderRadius: '8px', backdropFilter: 'blur(4px)', border: '1px solid rgba(255,255,255,0.1)' }}>
               <h4 style={{ margin: '0 0 8px 0', fontSize: '0.8rem', color: '#fff', textTransform: 'uppercase' }}>Zone Key</h4>
               <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', marginBottom: '4px' }}><div style={{ width: 12, height: 12, backgroundColor: '#ff0055', opacity: 0.6, border: '1px solid #ff0055' }} /> Busway Lane</div>
               <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', marginBottom: '4px' }}><div style={{ width: 12, height: 12, backgroundColor: '#00d4ff', opacity: 0.6, border: '1px solid #00d4ff' }} /> Bicycle Lane</div>
               <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem' }}><div style={{ width: 12, height: 12, backgroundColor: '#ffaa00', opacity: 0.6, border: '1px solid #ffaa00' }} /> No Parking</div>
            </div>
          </motion.div>

          {/* Inspector */}
          <motion.aside className="inspector-panel" {...fadeUp(0.15)}>
            <p className="eyebrow">Selected cell</p>
            <h2>{selected.corridor}</h2>
            <div className="metric-row">
              <span>Risk score</span>
              <strong style={{ color: 'var(--accent)' }}>{selected.risk}</strong>
            </div>
            <div className="metric-row">
              <span>Detections</span>
              <strong>{selected.count}</strong>
            </div>
            <div className="risk-meter" aria-label={`Risk ${selected.risk}%`}>
              <motion.span
                style={{ width: `${selected.risk}%` }}
                initial={{ width: 0 }}
                animate={{ width: `${selected.risk}%` }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
              />
            </div>
            <button className="btn-primary" type="button" id="btn-focus-patrol" style={{ width: '100%', marginTop: 8 }}>
              <Crosshair size={15} aria-hidden="true" />
              <span>Focus patrol plan</span>
            </button>
          </motion.aside>
        </div>
      </section>

      <section className="content-band parchment-band" id="insights">
        <div className="section-heading">
          <p className="eyebrow">Priority list</p>
          <h2>Hotspots that need attention first.</h2>
        </div>
        <motion.div className="rank-list" variants={stagger} initial="initial" animate="animate">
          {demoHotspots.map((hs, i) => (
            <motion.button
              key={hs.id}
              className="rank-item"
              type="button"
              onClick={() => handleSelect(hs)}
              variants={itemFade}
              id={`rank-${hs.id}`}
            >
              <span className="rank-number">{String(i + 1).padStart(2, '0')}</span>
              <span className="rank-main">
                <strong>{hs.corridor}</strong>
                <small>{hs.count} detections in active window</small>
              </span>
              <span className="bar-track">
                <motion.span
                  style={{ width: `${(hs.count / maxCount) * 100}%` }}
                  initial={{ width: 0 }}
                  animate={{ width: `${(hs.count / maxCount) * 100}%` }}
                  transition={{ duration: 0.7, delay: i * 0.08, ease: 'easeOut' }}
                />
              </span>
              <span className="rank-score">{hs.risk}</span>
            </motion.button>
          ))}
        </motion.div>
      </section>
    </>
  );
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export function AnalyticsPage() {
  const maxValue = Math.max(...hourlyViolations.map((d) => d.value));
  const totalViolations = hourlyViolations.reduce((s, d) => s + d.value, 0);
  const peak = hourlyViolations.reduce((b, d) => (d.value > b.value ? d : b), hourlyViolations[0]);

  return (
    <>
      <motion.section className="ops-hero" {...fadeUp(0)}>
        <div className="ops-hero-copy">
          <p className="eyebrow">Decision analytics</p>
          <h1>Evidence, throughput, and risk in one readable rhythm.</h1>
          <p>
            The analytics view keeps the operational story simple: when violations peak, which
            categories dominate, and where reviewer time is being spent.
          </p>
        </div>
        <div className="hero-stat-grid" aria-label="Analytics summary">
          <div>
            <span>Today</span>
            <strong>{totalViolations}</strong>
          </div>
          <div>
            <span>Peak hour</span>
            <strong>{peak.label}:00</strong>
          </div>
          <div>
            <span>Auto-ready</span>
            <strong>78%</strong>
          </div>
        </div>
      </motion.section>

      <section className="content-band" id="insights">
        <div className="analytics-grid">
          {/* Bar chart */}
          <motion.div className="chart-panel" {...fadeUp(0.08)}>
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Hourly volume</p>
                <h2>Violation load</h2>
              </div>
              <Activity size={20} aria-hidden="true" />
            </div>
            <div className="bar-chart" aria-label="Hourly violations chart">
              {hourlyViolations.map((item, i) => (
                <div className="bar-column" key={item.label}>
                  <motion.span
                    initial={{ height: '4%' }}
                    animate={{ height: `${Math.max(5, (item.value / maxValue) * 100)}%` }}
                    transition={{ duration: 0.65, delay: i * 0.04, ease: 'easeOut' }}
                  />
                  <small>{item.label}</small>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Mix donut-style list */}
          <motion.div className="chart-panel" {...fadeUp(0.14)}>
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Violation mix</p>
                <h2>Category share</h2>
              </div>
              <ArrowUpRight size={20} aria-hidden="true" />
            </div>
            <div className="mix-list">
              {violationMix.map((item, i) => (
                <motion.div
                  className="mix-row"
                  key={item.label}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.35, delay: 0.15 + i * 0.07 }}
                >
                  <span>{item.label}</span>
                  <strong>{item.value}%</strong>
                  <div className="bar-track">
                    <motion.span
                      initial={{ width: 0 }}
                      animate={{ width: `${item.value}%` }}
                      transition={{ duration: 0.7, delay: 0.2 + i * 0.07, ease: 'easeOut' }}
                    />
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      <section className="content-band parchment-band" id="review">
        <motion.div className="review-metrics" variants={stagger} initial="initial" animate="animate">
          {[
            { label: 'Median review', value: '42s',   icon: Clock3 },
            { label: 'Legal mapping', value: '100%',  icon: CheckCircle2 },
            { label: 'Camera uptime', value: '97.8%', icon: RadioTower },
          ].map(({ label, value, icon: Icon }) => (
            <motion.div className="metric-tile" key={label} variants={itemFade}>
              <Icon size={20} aria-hidden="true" />
              <span>{label}</span>
              <strong>{value}</strong>
            </motion.div>
          ))}
        </motion.div>
      </section>
    </>
  );
}

// ── Optimizer ─────────────────────────────────────────────────────────────────
export function OptimizerPage() {
  const [officers, setOfficers] = useState(4);
  const selectedDeployments = useMemo(() => demoDeployments.slice(0, officers), [officers]);
  const averageCoverage = Math.round(
    selectedDeployments.reduce((s, d) => s + d.coverage, 0) / selectedDeployments.length,
  );

  return (
    <>
      <motion.section className="ops-hero ops-hero-dark" {...fadeUp(0)}>
        <div className="ops-hero-copy">
          <p className="eyebrow">MCLP scenario planner</p>
          <h1>Place officers where each assignment covers the most risk.</h1>
          <p>
            Tune deployment capacity and review recommended cells before dispatch. The result is
            deterministic and ready to explain in an audit trail.
          </p>
        </div>
        <div className="optimizer-control">
          <SlidersHorizontal size={20} aria-hidden="true" />
          <label htmlFor="officer-count">Officers available</label>
          <div className="stepper">
            <button
              type="button"
              id="officer-decrement"
              onClick={() => setOfficers((v) => Math.max(1, v - 1))}
            >
              −
            </button>
            <motion.strong
              key={officers}
              initial={{ scale: 1.2, opacity: 0.5 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.22 }}
            >
              {officers}
            </motion.strong>
            <button
              type="button"
              id="officer-increment"
              onClick={() => setOfficers((v) => Math.min(demoDeployments.length, v + 1))}
            >
              +
            </button>
          </div>
          <input
            id="officer-count"
            min={1}
            max={demoDeployments.length}
            type="range"
            value={officers}
            onChange={(e) => setOfficers(Number(e.target.value))}
          />
        </div>
      </motion.section>

      <section className="content-band" id="insights">
        <motion.div className="optimizer-summary" {...fadeUp(0.06)}>
          <div>
            <span>Recommended posts</span>
            <strong>{selectedDeployments.length}</strong>
          </div>
          <div>
            <span>Avg. coverage</span>
            <strong style={{ color: 'var(--accent)' }}>{averageCoverage}%</strong>
          </div>
          <div>
            <span>Primary SLA</span>
            <strong>30 min</strong>
          </div>
        </motion.div>

        <motion.div
          className="deployment-list"
          variants={stagger}
          initial="initial"
          animate="animate"
        >
          {selectedDeployments.map((dep, i) => (
            <motion.article className="deployment-item" key={dep.id} variants={itemFade}>
              <span
                className="rank-number"
                style={{ fontSize: 28, color: i === 0 ? 'var(--accent)' : undefined }}
              >
                {String(i + 1).padStart(2, '0')}
              </span>
              <div>
                <p className="eyebrow" style={{ marginBottom: 4 }}>
                  {dep.priority} priority
                </p>
                <h2>{dep.corridor}</h2>
                <p>{dep.reasoning}</p>
              </div>
              <div className="deployment-meta">
                <span>
                  <MapPin size={13} aria-hidden="true" />
                  {dep.h3_index}
                </span>
                <span>
                  <Route size={13} aria-hidden="true" />
                  ETA {dep.eta}
                </span>
                <strong>{dep.coverage}% coverage</strong>
              </div>
            </motion.article>
          ))}
        </motion.div>
      </section>
    </>
  );
}
