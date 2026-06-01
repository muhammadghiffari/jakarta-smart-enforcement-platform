import { motion, AnimatePresence } from 'framer-motion';
import {
  Award,
  Bell,
  CheckCircle2,
  FileClock,
  Map,
  MapPin,
  Radio,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

type CRMReport = {
  id: string;
  jaki_report_id: string;
  source: string;
  category: string;
  category_raw?: string;
  category_normalized?: string;
  lat: number;
  lng: number;
  photo_url: string;
  description: string;
  user_id_hashed: string;
  citizen_score?: number;
  cctv_score?: number;
  combined_confidence?: number;
  status: string;
  created_at: string;
};

type CitizenPoint = {
  id: string;
  user_id_hashed: string;
  points_total: number;
  reports_count: number;
  corroborated: number;
  updated_at: string;
};

type UnitDispatch = {
  id: string;
  violation_id?: string;
  crm_report_id?: string;
  unit_code: string;
  corridor: string;
  h3_cell: string;
  status: string;
  dispatched_at: string;
  acknowledged_at?: string;
  source_type: string;
  violation_type: string;
  details: string;
};

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.45, delay } },
});

export default function CRMDispatchPage() {
  const [reports, setReports] = useState<CRMReport[]>([]);
  const [points, setPoints] = useState<CitizenPoint[]>([]);
  const [dispatches, setDispatches] = useState<UnitDispatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [notice, setNotice] = useState('Loading CRM & Dispatch logs...');

  // Fallback demo data to keep UI looking pristine when backend is disconnected
  const demoReports: CRMReport[] = [
    {
      id: 'r1',
      jaki_report_id: 'JAKI-982142',
      source: 'JAKI',
      category: 'ILLEGAL_PARKING',
      lat: -6.2088,
      lng: 106.8456,
      photo_url: 'https://jsep.dishub.go.id/mock_photo.jpg',
      description: 'A black SUV parking on the sidewalk near Bundaran HI',
      user_id_hashed: 'usr_f892a10c',
      citizen_score: 0.85,
      cctv_score: 0.90,
      combined_confidence: 0.88,
      status: 'VERIFIED',
      created_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    },
    {
      id: 'r2',
      jaki_report_id: 'JAKI-124958',
      source: 'JAKI',
      category: 'BUSWAY_VIOLATION',
      lat: -6.1950,
      lng: 106.8230,
      photo_url: 'https://jsep.dishub.go.id/mock_photo.jpg',
      description: 'Several motorbikes entering the TransJakarta lane',
      user_id_hashed: 'usr_39fa20b1',
      citizen_score: 0.75,
      cctv_score: 0.95,
      combined_confidence: 0.87,
      status: 'VERIFIED',
      created_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    }
  ];

  const demoPoints: CitizenPoint[] = [
    { id: 'p1', user_id_hashed: 'usr_f892a10c', points_total: 450, reports_count: 9, corroborated: 8, updated_at: '' },
    { id: 'p2', user_id_hashed: 'usr_39fa20b1', points_total: 300, reports_count: 6, corroborated: 6, updated_at: '' },
    { id: 'p3', user_id_hashed: 'usr_87bc201a', points_total: 200, reports_count: 5, corroborated: 4, updated_at: '' },
  ];

  const demoDispatches: UnitDispatch[] = [
    {
      id: 'd1',
      crm_report_id: 'r1',
      unit_code: 'parking_enforcement',
      corridor: 'Bundaran HI - Sudirman',
      h3_cell: '8a2f15c2d1b7fff',
      status: 'DISPATCHED',
      dispatched_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
      source_type: 'CITIZEN (JAKI)',
      violation_type: 'ILLEGAL_PARKING',
      details: 'JAKI ID: JAKI-982142 | Sidewalk parking Bundaran HI',
    },
    {
      id: 'd2',
      violation_id: 'v2',
      unit_code: 'transjakarta_liaison',
      corridor: 'Kuningan Corridor',
      h3_cell: '8a2f15c2d587fff',
      status: 'ACKNOWLEDGED',
      dispatched_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      acknowledged_at: new Date(Date.now() - 1000 * 60 * 25).toISOString(),
      source_type: 'SYSTEM (E-TLE)',
      violation_type: 'BUSWAY_VIOLATION',
      details: 'Plate: B 9999 ABC | CAM: CAM-THR-02',
    }
  ];

  const fetchCRMData = useCallback(async () => {
    try {
      const [reportsRes, pointsRes, dispatchesRes] = await Promise.all([
        fetch(`${apiBase}/api/v1/jaki/reports`),
        fetch(`${apiBase}/api/v1/jaki/points`),
        fetch(`${apiBase}/api/v1/jaki/dispatches`),
      ]);

      if (!reportsRes.ok || !pointsRes.ok || !dispatchesRes.ok) {
        throw new Error('Backend endpoints not fully warmed up or seeding');
      }

      const reportsData = await reportsRes.json();
      const pointsData = await pointsRes.json();
      const dispatchesData = await dispatchesRes.json();

      setReports(reportsData.items && reportsData.items.length > 0 ? reportsData.items : demoReports);
      setPoints(pointsData.items && pointsData.items.length > 0 ? pointsData.items : demoPoints);
      setDispatches(dispatchesData.items && dispatchesData.items.length > 0 ? dispatchesData.items : demoDispatches);
      setNotice('Connected to real-time CRM & Dispatch databases.');
    } catch {
      setReports(demoReports);
      setPoints(demoPoints);
      setDispatches(demoDispatches);
      setNotice('⚠️ Curated simulation mode active. Connect backend to view live PGSQL triggers.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCRMData();
    const interval = setInterval(fetchCRMData, 3000);
    return () => clearInterval(interval);
  }, [fetchCRMData]);

  const triggerJakiReport = async () => {
    setSimulating(true);
    setNotice('Simulating citizen report ingestion via JAKI webhook...');
    try {
      const res = await fetch(`${apiBase}/api/v1/demo/trigger/E`, { method: 'POST' });
      if (res.ok) {
        setNotice('⚡ JAKI Report ingested! CCTV corroboration executed automatically.');
        setTimeout(fetchCRMData, 800);
      } else {
        throw new Error();
      }
    } catch {
      // Mock client-side insertion for the visual demo if backend is offline
      const mockId = `JAKI-${Math.floor(100000 + Math.random() * 900000)}`;
      const mockUser = `usr_${Math.random().toString(36).substring(2, 10)}`;
      const categories = ['ILLEGAL_PARKING', 'BUSWAY_VIOLATION', 'ILLEGAL_DROPOFF'];
      const chosenCat = categories[Math.floor(Math.random() * categories.length)];
      
      const newReport: CRMReport = {
        id: `r-${Date.now()}`,
        jaki_report_id: mockId,
        source: 'JAKI',
        category: chosenCat,
        lat: -6.2000 + (Math.random() - 0.5) * 0.05,
        lng: 106.8200 + (Math.random() - 0.5) * 0.05,
        photo_url: '',
        description: `Synthetic citizen report of ${chosenCat.replace('_', ' ').toLowerCase()}`,
        user_id_hashed: mockUser,
        citizen_score: 0.82,
        cctv_score: 0.92,
        combined_confidence: 0.88,
        status: 'VERIFIED',
        created_at: new Date().toISOString(),
      };

      const newDispatch: UnitDispatch = {
        id: `d-${Date.now()}`,
        crm_report_id: newReport.id,
        unit_code: chosenCat === 'ILLEGAL_PARKING' ? 'parking_enforcement' : chosenCat === 'BUSWAY_VIOLATION' ? 'transjakarta_liaison' : 'field_patrol',
        corridor: 'Sudirman-Thamrin Pilot Zone',
        h3_cell: '8a2f15c2d1b7fff',
        status: 'DISPATCHED',
        dispatched_at: new Date().toISOString(),
        source_type: 'CITIZEN (JAKI)',
        violation_type: chosenCat,
        details: `JAKI ID: ${mockId} | Auto corroborated by CCTV (0.88)`,
      };

      setReports((prev) => [newReport, ...prev]);
      setDispatches((prev) => [newDispatch, ...prev]);
      
      // Update points
      setPoints((prev) => {
        const idx = prev.findIndex((p) => p.user_id_hashed === 'usr_f892a10c');
        if (idx !== -1) {
          const updated = [...prev];
          updated[idx] = {
            ...updated[idx],
            points_total: updated[idx].points_total + 50,
            reports_count: updated[idx].reports_count + 1,
            corroborated: updated[idx].corroborated + 1,
          };
          return updated;
        }
        return prev;
      });

      setNotice('⚡ Client simulation ingested. (Backend offline fallback)');
    } finally {
      setSimulating(false);
    }
  };

  const getUnitName = (code: string) => {
    const names: Record<string, string> = {
      parking_enforcement: 'Parking Enforcement Unit',
      transjakarta_liaison: 'TransJakarta Liaison',
      bicycle_lane_patrol: 'Bicycle Lane Patrol',
      field_patrol: 'Field Patrol Unit',
      general_operations: 'General Operations',
    };
    return names[code] || code;
  };

  const getUnitBadgeColor = (code: string) => {
    const colors: Record<string, string> = {
      parking_enforcement: 'rgba(255, 170, 0, 0.15)',
      transjakarta_liaison: 'rgba(255, 0, 85, 0.15)',
      bicycle_lane_patrol: 'rgba(0, 212, 255, 0.15)',
      field_patrol: 'rgba(50, 200, 100, 0.15)',
    };
    return colors[code] || 'rgba(150, 150, 150, 0.15)';
  };

  const getUnitTextColor = (code: string) => {
    const colors: Record<string, string> = {
      parking_enforcement: '#ffaa00',
      transjakarta_liaison: '#ff0055',
      bicycle_lane_patrol: '#00d4ff',
      field_patrol: '#32c864',
    };
    return colors[code] || '#aaaaaa';
  };

  const formatCategory = (cat: string) => {
    return cat.replace('_', ' ');
  };

  return (
    <div className="etle-container" style={{ padding: '0 24px 24px 24px', minHeight: 'calc(100vh - 120px)' }}>
      {/* Premium header */}
      <motion.div className="etle-header glass-panel" {...fadeUp(0)} style={{ marginBottom: 24, padding: '16px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Shield size={18} color="#00d4ff" />
              DISPATCH & CITIZEN CRM PORTAL
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
              Visualizing the legal routing matrix and gamified citizen report verification.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', background: 'rgba(255,255,255,0.05)', padding: '6px 12px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
              {notice}
            </span>
            <button
              onClick={triggerJakiReport}
              disabled={simulating}
              className="btn-primary"
              style={{ padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}
            >
              <Send size={13} />
              {simulating ? 'Ingesting...' : 'Ingest JAKI Report (Scenario E)'}
            </button>
          </div>
        </div>
      </motion.div>

      {/* Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        
        {/* Left Side: Citizen CRM & Gamification */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          
          {/* Card 1: Citizen Points & Engagement Leaderboard */}
          <motion.div className="glass-panel" {...fadeUp(0.1)} style={{ padding: 24 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <Award size={16} color="#ffaa00" />
              Citizen Reporting Gamification (FR-VIO-08 / RULE-10)
            </h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: 20 }}>
              
              {/* Concept text */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, borderRight: '1px solid rgba(255,255,255,0.06)', paddingRight: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ padding: 8, borderRadius: 8, background: 'rgba(0, 212, 255, 0.1)', color: '#00d4ff' }}>
                    <Users size={16} />
                  </div>
                  <div>
                    <h4 style={{ fontSize: 12, fontWeight: 600 }}>Active Citizenry</h4>
                    <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Public participation tracked anonymously via cryptographic hashes.</p>
                  </div>
                </div>
                
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ padding: 8, borderRadius: 8, background: 'rgba(50, 200, 100, 0.1)', color: '#32c864' }}>
                    <TrendingUp size={16} />
                  </div>
                  <div>
                    <h4 style={{ fontSize: 12, fontWeight: 600 }}>Impact Rewards</h4>
                    <p style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Earn 50 Points for verified reports. Directly incentivizes quality reports.</p>
                  </div>
                </div>
              </div>

              {/* Leaderboard */}
              <div>
                <h4 style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
                  Top Citizen Contributors
                </h4>
                {loading ? (
                  <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>Loading leaderboard...</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {points.map((p, i) => (
                      <div
                        key={p.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          background: 'rgba(255,255,255,0.02)',
                          padding: '8px 12px',
                          borderRadius: 8,
                          border: '1px solid rgba(255,255,255,0.04)',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{ fontSize: 11, fontWeight: 700, color: i === 0 ? '#ffaa00' : i === 1 ? '#cccccc' : '#cc7744', width: 14 }}>
                            #{i + 1}
                          </span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.8)' }}>
                            {p.user_id_hashed.substring(0, 12)}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: 16, fontSize: 11 }}>
                          <span style={{ color: 'var(--text-muted)' }}>
                            <strong style={{ color: '#fff' }}>{p.reports_count}</strong> rpts
                          </span>
                          <span style={{ color: '#00d4ff', fontWeight: 600 }}>
                            {p.points_total} pts
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>

          {/* Card 2: Citizen Reports Live Feed */}
          <motion.div className="glass-panel" {...fadeUp(0.2)} style={{ padding: 24, flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: 380 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <Radio size={16} color="#00d4ff" />
              Ingested JAKI Complaint Webhooks
            </h3>
            
            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexGrow: 1, color: 'var(--text-muted)', fontSize: 13 }}>
                Loading complaints...
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto', maxHeight: 420 }}>
                <AnimatePresence>
                  {reports.map((r) => (
                    <motion.div
                      key={r.id}
                      initial={{ opacity: 0, x: -16 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 16 }}
                      style={{
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        borderRadius: 10,
                        padding: 16,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 10,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: 12, fontWeight: 700, color: '#fff', background: 'rgba(0, 212, 255, 0.1)', padding: '3px 8px', borderRadius: 4 }}>
                            {r.jaki_report_id}
                          </span>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                            {new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <ShieldCheck size={13} color="#32c864" />
                          <span style={{ fontSize: 10, fontWeight: 700, color: '#32c864', letterSpacing: '0.05em' }}>
                            {r.status}
                          </span>
                        </div>
                      </div>

                      <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.85)', lineHeight: 1.4 }}>
                        {r.description}
                      </p>

                      {/* CCTV Corroboration Engine Display */}
                      <div style={{
                        background: 'rgba(15, 23, 42, 0.4)',
                        border: '1px solid rgba(255,255,255,0.03)',
                        borderRadius: 8,
                        padding: '10px 12px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: 11
                      }}>
                        <div style={{ display: 'flex', gap: 16 }}>
                          <span style={{ color: 'var(--text-muted)' }}>
                            Citizen trust: <strong style={{ color: '#fff' }}>{r.citizen_score ?? 0.8}</strong>
                          </span>
                          <span style={{ color: 'var(--text-muted)' }}>
                            CCTV match: <strong style={{ color: '#fff' }}>{r.cctv_score ?? 0.9}</strong>
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ color: 'var(--text-muted)' }}>Combined:</span>
                          <span style={{
                            color: (r.combined_confidence ?? 0.85) >= 0.85 ? '#32c864' : '#ffaa00',
                            fontWeight: 700
                          }}>
                            {Math.round((r.combined_confidence ?? 0.85) * 100)}%
                          </span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)' }}>
                          <MapPin size={12} />
                          <span>{r.lat.toFixed(4)}, {r.lng.toFixed(4)}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span style={{ color: 'var(--text-muted)' }}>Type:</span>
                          <span style={{ color: '#00d4ff', fontWeight: 600 }}>{formatCategory(r.category)}</span>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </motion.div>

        </div>

        {/* Right Side: Unit Dispatch Operations */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          
          {/* Card 3: Routing Matrix Rules (Display reference only) */}
          <motion.div className="glass-panel" {...fadeUp(0.15)} style={{ padding: 24 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <ShieldAlert size={16} color="#ff0055" />
              Deterministic Agency Routing Matrix (FR-LEGAL-01)
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 11, marginBottom: 14, lineHeight: 1.4 }}>
              Based on traffic law categories, violations are dispatched deterministically to the authorized agency units instantly.
            </p>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div style={{ padding: '10px 12px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.75)' }}>ILLEGAL PARKING</span>
                <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: 'rgba(255, 170, 0, 0.12)', color: '#ffaa00' }}>PARKING ENFORCEMENT</span>
              </div>
              <div style={{ padding: '10px 12px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.75)' }}>BUSWAY VIOLATION</span>
                <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: 'rgba(255, 0, 85, 0.12)', color: '#ff0055' }}>TRANSJAKARTA LIAISON</span>
              </div>
              <div style={{ padding: '10px 12px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.75)' }}>BICYCLE VIOLATION</span>
                <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: 'rgba(0, 212, 255, 0.12)', color: '#00d4ff' }}>BICYCLE PATROL</span>
              </div>
              <div style={{ padding: '10px 12px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 10, fontWeight: 600, color: 'rgba(255,255,255,0.75)' }}>ILLEGAL DROPOFF</span>
                <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: 'rgba(50, 200, 100, 0.12)', color: '#32c864' }}>FIELD PATROL</span>
              </div>
            </div>
          </motion.div>

          {/* Card 4: Unit Dispatches Center (Routing Feed) */}
          <motion.div className="glass-panel" {...fadeUp(0.25)} style={{ padding: 24, flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: 380 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <FileClock size={16} color="#ff0055" />
              Operational Agency Unit Dispatches
            </h3>

            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexGrow: 1, color: 'var(--text-muted)', fontSize: 13 }}>
                Loading dispatch matrix logs...
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflowY: 'auto', maxHeight: 420 }}>
                <AnimatePresence>
                  {dispatches.map((d) => (
                    <motion.div
                      key={d.id}
                      initial={{ opacity: 0, x: 16 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -16 }}
                      style={{
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                        borderRadius: 10,
                        padding: 16,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 10,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <span style={{
                            fontSize: 10,
                            fontWeight: 700,
                            padding: '3px 8px',
                            borderRadius: 4,
                            background: getUnitBadgeColor(d.unit_code),
                            color: getUnitTextColor(d.unit_code),
                            letterSpacing: '0.02em'
                          }}>
                            {getUnitName(d.unit_code).toUpperCase()}
                          </span>
                          <span style={{ fontSize: 10, background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', padding: '3px 8px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>
                            {d.source_type}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#32c864', fontSize: 10, fontWeight: 700 }}>
                          <CheckCircle2 size={12} />
                          <span>{d.status}</span>
                        </div>
                      </div>

                      <p style={{ fontSize: 12, color: 'rgba(255,255,255,0.85)' }}>
                        {d.details}
                      </p>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 11, borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: 10 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)' }}>
                          <Map size={11} />
                          <span>{d.corridor}</span>
                        </div>
                        <span style={{ color: 'var(--text-muted)' }}>
                          {new Date(d.dispatched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            )}
          </motion.div>

        </div>

      </div>
    </div>
  );
}
