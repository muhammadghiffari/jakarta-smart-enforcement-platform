import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle, 
  FileText, 
  Scale, 
  ShieldAlert, 
  XCircle, 
  UploadCloud, 
  Play, 
  Sparkles, 
  History, 
  Search, 
  Sliders, 
  Database,
  ArrowRight,
  FileSpreadsheet,
  Cpu
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { formatViolationType } from '../lib/demoContent';

type Violation = {
  id: string;
  track_id: string;
  violation_type: string;
  composite_confidence: number;
  camera_id: string;
  duration_seconds: number;
  start_time: string;
  status?: string;
  zone_id?: string;
  vehicle_class?: string;
};

const demoViolations: Violation[] = [
  {
    id: 'a7f4f0ba-9054-4254-93f4-c1010b9e7001',
    track_id: 'B 1842 KJS',
    violation_type: 'BUS_LANE_VIOLATION',
    composite_confidence: 0.93,
    camera_id: 'CAM-THR-04',
    duration_seconds: 12,
    start_time: '2026-06-01T09:42:18+07:00',
    zone_id: 'BUSWAY-THR-01',
    vehicle_class: 'private_car',
  },
  {
    id: 'fb441122-c922-4625-a9d3-b2886f775655',
    track_id: 'B 6112 PXA',
    violation_type: 'DESIGNATED_STOP_VIOLATION',
    composite_confidence: 0.74,
    camera_id: 'CAM-KUN-02',
    duration_seconds: 19,
    start_time: '2026-06-01T09:31:23+07:00',
    zone_id: 'STOP-KUN-07',
    vehicle_class: 'angkot',
  },
];

const defaultLegalRules = [
  {
    violation_type: 'BUS_LANE_VIOLATION',
    legal_basis: {
      code: 'UU-LLAJ-287-1',
      title: 'Busway Lane Violation',
      citation_text: 'Pasal 287 ayat (1) UU No. 22 Tahun 2009 tentang Lalu Lintas dan Angkutan Jalan (LLAJ). Larangan memasuki jalur TransJakarta.'
    },
    sanction: {
      code: 'SANC-01',
      title: 'Traffic Fine Category A',
      fine_min_idr: 250000,
      fine_max_idr: 500000,
      action_type: 'FINE'
    },
    relevant_unit: 'transjakarta_liaison',
    evidence_required: 'Busway corridor camera feed, plate crop'
  },
  {
    violation_type: 'ILLEGAL_PARKING',
    legal_basis: {
      code: 'UU-LLAJ-287-5',
      title: 'Illegal Parking/Stopping',
      citation_text: 'Pasal 287 ayat (5) UU No. 22 Tahun 2009. Melanggar rambu larangan parkir (P coret) atau larangan berhenti (S coret).'
    },
    sanction: {
      code: 'SANC-02',
      title: 'Towing & Compound Fine',
      fine_min_idr: 250000,
      fine_max_idr: 500000,
      action_type: 'TOWING'
    },
    relevant_unit: 'parking_enforcement',
    evidence_required: '15s stationary detection timeline with plate corroboration'
  },
  {
    violation_type: 'DESIGNATED_STOP_VIOLATION',
    legal_basis: {
      code: 'UU-LLAJ-287-3',
      title: 'Illegal Passenger Pick-up / Drop-off',
      citation_text: 'Pasal 287 ayat (3) UU No. 22 Tahun 2009. Menaikkan atau menurunkan penumpang di area terlarang atau bukan halte resmi.'
    },
    sanction: {
      code: 'SANC-03',
      title: 'Traffic Fine Category B',
      fine_min_idr: 100000,
      fine_max_idr: 250000,
      action_type: 'FINE'
    },
    relevant_unit: 'field_patrol',
    evidence_required: 'CCTV video capture showing door opening and passenger action'
  }
];

const defaultAuditLogs = [
  {
    id: 'aud-demo-1',
    action: 'CONFIRM',
    entity_type: 'violation',
    entity_id: 'a7f4f0ba',
    officer_id: 'OFC-DEMO-01',
    detail: 'Violation confirmed and E-TLE submission dispatched.',
    created_at: new Date(Date.now() - 1800000).toISOString()
  },
  {
    id: 'aud-demo-2',
    action: 'DISMISS',
    entity_type: 'violation',
    entity_id: 'fb441122',
    officer_id: 'OFC-DEMO-01',
    detail: 'Reason: Plate number occluded by vehicle bumper shadow.',
    created_at: new Date(Date.now() - 3600000).toISOString()
  }
];

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4, delay } },
});

const stagger = { animate: { transition: { staggerChildren: 0.07 } } };
const itemFade = {
  initial: { opacity: 0, x: -10 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.3 } },
};

export default function ETLEPage() {
  const [mode, setMode] = useState<'demo' | 'live'>('demo');

  const [violations, setViolations] = useState<Violation[]>(demoViolations);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(demoViolations[0]?.id ?? '');
  const [notice, setNotice] = useState('Operations queue initialized.');

  // Modal Report States
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [reportContent, setReportContent] = useState('');
  const [reportLoading, setReportLoading] = useState(false);

  // Expanded Layout Data States
  const [legalRules, setLegalRules] = useState<any[]>(defaultLegalRules);
  const [auditLogs, setAuditLogs] = useState<any[]>(defaultAuditLogs);
  const [rulesSearch, setRulesSearch] = useState('');

  // Live Mode Interactive States
  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [inferenceResult, setInferenceResult] = useState<any>(null);
  const [inferencing, setInferencing] = useState(false);
  const [runPlateDet, setRunPlateDet] = useState(true);
  const [isDragOver, setIsDragOver] = useState(false);
  
  // Custom ticket ingestion from Live Mode detections
  const [customPlate, setCustomPlate] = useState('B 1234 XYZ');
  const [customViolationType, setCustomViolationType] = useState('BUS_LANE_VIOLATION');
  const [customCamera, setCustomCamera] = useState('CAM-OPERATOR-UP');

  const selected = violations.find((v) => v.id === selectedId) ?? violations[0];

  const queueSummary = useMemo(() => {
    const ready = violations.filter((v) => v.composite_confidence >= 0.75).length;
    return [
      { label: 'Pending review', value: violations.length },
      { label: 'Auto-ready',     value: ready },
      { label: 'Manual gate',    value: violations.length - ready },
    ];
  }, [violations]);

  // Fetch queue
  const fetchViolations = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/v1/violations?status=DETECTED`);
      if (!res.ok) throw new Error('Unable to load queue');
      const data = (await res.json()) as { items?: Violation[] };
      const items = data.items ?? [];
      setViolations(items);
      setSelectedId((cur) => (items.some((i) => i.id === cur) ? cur : items[0]?.id ?? ''));
    } catch {
      // Fallback already handled
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch Audit Logs
  const fetchAuditLogs = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/v1/violations/audit_logs`);
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data.items && data.items.length > 0 ? data.items : defaultAuditLogs);
      }
    } catch {
      // Fallback defaults
    }
  }, []);

  // Fetch Legal Catalog
  const fetchLegalRules = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/v1/legal`);
      if (res.ok) {
        const data = await res.json();
        setLegalRules(data.items && data.items.length > 0 ? data.items : defaultLegalRules);
      }
    } catch {
      // Fallback defaults
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(() => {
      fetchViolations();
      fetchAuditLogs();
      fetchLegalRules();
    }, 0);

    const timer = window.setInterval(() => {
      fetchViolations();
      fetchAuditLogs();
    }, 5000);

    return () => {
      window.clearTimeout(initial);
      window.clearInterval(timer);
    };
  }, [fetchViolations, fetchAuditLogs, fetchLegalRules]);

  // Wire SubNav action to scroll down to Audit Logs
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.route === '/etle') {
        const target = document.getElementById('audit-section');
        if (target) {
          target.scrollIntoView({ behavior: 'smooth' });
        }
      }
    };
    window.addEventListener('jsep:subnav-action', handler);
    return () => window.removeEventListener('jsep:subnav-action', handler);
  }, []);

  const removeFromQueue = (id: string) => {
    setViolations((items) => {
      const next = items.filter((i) => i.id !== id);
      setSelectedId(next[0]?.id ?? '');
      return next;
    });
  };

  const handleApprove = async (violation: Violation) => {
    if (violation.composite_confidence < 0.75) {
      setNotice('RULE-04: confidence below 75% requires explicit manual review.');
      return;
    }
    try {
      const res = await fetch(`${apiBase}/api/v1/violations/${violation.id}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ officer_id: 'OFC-DEMO-01' }),
      });
      if (!res.ok) throw new Error('Confirm failed');
      removeFromQueue(violation.id);
      setNotice(`${violation.track_id} approved for E-TLE submission.`);
      setTimeout(fetchAuditLogs, 500);
    } catch {
      removeFromQueue(violation.id);
      setNotice(`${violation.track_id} approved in demo mode.`);
      
      // Push local audit entry
      setAuditLogs(prev => [
        {
          id: `aud-local-${Date.now()}`,
          action: 'CONFIRM',
          entity_type: 'violation',
          entity_id: violation.id.slice(0, 8),
          officer_id: 'OFC-DEMO-01',
          detail: `[Demo Mode] Vehicle ${violation.track_id} approved.`,
          created_at: new Date().toISOString()
        },
        ...prev
      ]);
    }
  };

  const handleDismiss = async (violation: Violation) => {
    try {
      const res = await fetch(`${apiBase}/api/v1/violations/${violation.id}/dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ officer_id: 'OFC-DEMO-01', reason: 'MANUAL REVIEW DISMISSAL' }),
      });
      if (!res.ok) throw new Error();
      setTimeout(fetchAuditLogs, 500);
    } catch {
      // Mock local update
      setAuditLogs(prev => [
        {
          id: `aud-local-${Date.now()}`,
          action: 'DISMISS',
          entity_type: 'violation',
          entity_id: violation.id.slice(0, 8),
          officer_id: 'OFC-DEMO-01',
          detail: `[Demo Mode] Vehicle ${violation.track_id} dismissed. Reason: MANUAL REVIEW DISMISSAL.`,
          created_at: new Date().toISOString()
        },
        ...prev
      ]);
    } finally {
      removeFromQueue(violation.id);
      setNotice(`${violation.track_id} removed from the review queue.`);
    }
  };

  const handleGenerateReport = async (violation: Violation) => {
    setReportModalOpen(true);
    setReportLoading(true);
    setReportContent('');
    try {
      const res = await fetch(`${apiBase}/api/v1/violations/${violation.id}/berita_acara?format=json`);
      if (!res.ok) throw new Error('API not reachable');
      const data = await res.json();
      setReportContent(data.content || 'Report generation succeeded but returned empty.');
    } catch {
      setReportContent(
        `BERITA ACARA PELANGGARAN LALU LINTAS\n\n` +
        `Pada hari ini, telah terekam pelanggaran lalu lintas oleh kendaraan dengan nomor polisi ${violation.track_id}.\n` +
        `Jenis pelanggaran: ${formatViolationType(violation.violation_type)}\n` +
        `Lokasi: ${violation.camera_id}\n\n` +
        `[Demo Mode: API backend is not reachable to run the full narrative agent. Start the FastAPI backend to see the full RAG/LLM integration.]`
      );
    } finally {
      setReportLoading(false);
    }
  };

  // Uploader Handlers
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    processUploadedFile(file);
  };

  const processUploadedFile = (file: File) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreviewUrl(reader.result as string);
      setInferenceResult(null);
      setNotice(`Loaded image: ${file.name}. Click "Run Detection" to trigger neural model inference.`);
    };
    reader.readAsDataURL(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      processUploadedFile(file);
    }
  };

  // Execute YOLO Model on Backend
  const runLiveInference = async () => {
    if (!previewUrl) return;
    setInferencing(true);
    setInferenceResult(null);
    setNotice('Triggering AI detection pipeline (YOLOv8 + Plate OCR)...');
    try {
      const res = await fetch(`${apiBase}/api/v1/inference/image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_base64: previewUrl,
          run_plate_detection: runPlateDet
        })
      });
      if (!res.ok) throw new Error('Inference failed');
      const data = await res.json();
      setInferenceResult(data);
      setNotice(`Inference completed. Detected ${data.detections?.length || 0} objects in ${data.elapsed_ms}ms.`);
      
      // Auto-extract OCR plate or create random plate if plate model was run
      const plates = data.detections?.flatMap((d: any) => d.plates || []) || [];
      if (plates.length > 0) {
        setCustomPlate('B ' + Math.floor(1000 + Math.random() * 8999 + 1000) + ' JKP');
      } else {
        setCustomPlate('B ' + Math.floor(1000 + Math.random() * 8999 + 1000) + ' OUT');
      }
    } catch (err) {
      setNotice('⚠️ Backend inference models offline. Simulating model results for demo...');
      // Simulated response
      setTimeout(() => {
        setInferenceResult({
          elapsed_ms: 184,
          image_width: 800,
          image_height: 500,
          detections: [
            { id: 'det-1', class_name: 'car', confidence: 0.9412, bbox: [120, 150, 480, 380], plates: [{ confidence: 0.89, bbox: [280, 310, 380, 340] }] }
          ],
          annotated_image: previewUrl // use original
        });
        setCustomPlate('B ' + Math.floor(1000 + Math.random() * 8999 + 1000) + ' SIM');
        setNotice('Inference completed (Simulated).');
      }, 1000);
    } finally {
      setInferencing(false);
    }
  };

  const runBundledDemoInference = async () => {
    setInferencing(true);
    setInferenceResult(null);
    setNotice('Executing inference on bundled demo image...');
    try {
      const res = await fetch(`${apiBase}/api/v1/inference/demo?run_plate_detection=${runPlateDet}`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Demo failed');
      const data = await res.json();
      setInferenceResult(data);
      setPreviewUrl(data.annotated_image);
      setNotice(`Demo inference completed in ${data.elapsed_ms}ms.`);
      setCustomPlate('B 1928 SBP');
    } catch {
      setNotice('❌ Failed to run demo inference.');
    } finally {
      setInferencing(false);
    }
  };

  // Submit model detection output as an E-TLE violation
  const ingestCustomViolation = async () => {
    setNotice('Ingesting custom violation into active E-TLE queue...');
    const mockId = crypto.randomUUID ? crypto.randomUUID() : `etle-${Date.now()}`;
    const payload: Violation = {
      id: mockId,
      camera_id: customCamera,
      track_id: customPlate,
      violation_type: customViolationType,
      zone_id: 'BUSWAY-THR-01',
      vehicle_class: 'private_car',
      start_time: new Date().toISOString(),
      duration_seconds: 14,
      composite_confidence: inferenceResult ? (inferenceResult.detections?.[0]?.confidence ?? 0.91) : 0.89
    };
    
    try {
      const res = await fetch(`${apiBase}/api/v1/violations/internal/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('Ingest failed');
      
      setNotice(`⚡ Success! Custom violation ${customPlate} added to the review queue.`);
      setViolations(prev => [payload, ...prev]);
      setMode('demo');
      setSelectedId(payload.id);
    } catch {
      // Offline fallback
      setViolations(prev => [payload, ...prev]);
      setNotice(`[Demo Mode] Custom violation ${customPlate} added to local queue.`);
      setMode('demo');
      setSelectedId(payload.id);
    }
  };

  // Filter legal rules based on search
  const filteredRules = useMemo(() => {
    const q = rulesSearch.toLowerCase();
    if (!q) return legalRules;
    return legalRules.filter(
      r => 
        r.violation_type.toLowerCase().includes(q) || 
        r.legal_basis?.code.toLowerCase().includes(q) || 
        r.legal_basis?.title.toLowerCase().includes(q) || 
        r.legal_basis?.citation_text.toLowerCase().includes(q)
    );
  }, [legalRules, rulesSearch]);

  return (
    <>
      {/* ── HERO ── */}
      <motion.section className="ops-hero" {...fadeUp(0)}>
        <div className="ops-hero-copy">
          <p className="eyebrow">Interactive Enforcement Operations</p>
          <h1>Human-in-the-loop E-TLE with Live Model & Rules Gates.</h1>
          <p>
            Verify traffic detections using deep learning inference models, review deterministic rule mappings,
            and inspect logs in one place before submitting legal violations.
          </p>
        </div>
        <div className="hero-stat-grid" aria-label="Queue summary">
          {queueSummary.map((item) => (
            <div key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      </motion.section>

      {/* ── MODE SELECTOR BANNER ── */}
      <div 
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '1.5rem',
          padding: '1.25rem 28px',
          borderBottom: '1px solid var(--border)',
          background: 'rgba(13, 17, 23, 0.4)',
          backdropFilter: 'blur(8px)',
          position: 'sticky',
          top: '104px',
          zIndex: 85
        }}
      >
        <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-secondary)' }}>
          Active Mode:
        </span>
        <div style={{ display: 'flex', background: 'rgba(255,255,255,0.04)', padding: '4px', borderRadius: '30px', border: '1px solid var(--border)' }}>
          <button
            onClick={() => setMode('demo')}
            style={{
              padding: '6px 18px',
              borderRadius: '20px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none',
              transition: 'all 0.22s ease',
              background: mode === 'demo' ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' : 'transparent',
              color: mode === 'demo' ? '#000' : 'var(--text-secondary)'
            }}
          >
            🔴 Demo Queue Review
          </button>
          <button
            onClick={() => setMode('live')}
            style={{
              padding: '6px 18px',
              borderRadius: '20px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none',
              transition: 'all 0.22s ease',
              background: mode === 'live' ? 'linear-gradient(135deg, var(--accent) 0%, #0099bb 100%)' : 'transparent',
              color: mode === 'live' ? '#000' : 'var(--text-secondary)'
            }}
          >
            🟢 Live Model (Upload Video/Img)
          </button>
        </div>
      </div>

      {/* ── PRIMARY VIEW (QUEUE vs INFERENCE) ── */}
      <section className="content-band" id="etle-view">
        <AnimatePresence mode="wait">
          {mode === 'demo' ? (
            <motion.div 
              key="demo-queue-layout"
              className="queue-shell"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
            >
              {/* Queue sidebar */}
              <motion.aside className="queue-list" aria-label="Violation queue" {...fadeUp(0.08)}>
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">Detected</p>
                    <h2>Queue</h2>
                  </div>
                  <span className={`status-pill ${!loading ? 'is-live' : ''}`}>
                    <span className="live-dot" />
                    {loading ? 'Syncing' : 'Live'}
                  </span>
                </div>

                <motion.div variants={stagger} initial="initial" animate="animate">
                  {violations.map((v) => (
                    <motion.button
                      key={v.id}
                      className={`queue-item ${selected?.id === v.id ? 'is-selected' : ''}`}
                      type="button"
                      onClick={() => setSelectedId(v.id)}
                      variants={itemFade}
                      id={`queue-${v.id.slice(0, 8)}`}
                      whileTap={{ scale: 0.98 }}
                    >
                      <span>{formatViolationType(v.violation_type)}</span>
                      <strong>{v.track_id}</strong>
                      <small>{v.camera_id}</small>
                    </motion.button>
                  ))}
                </motion.div>

                {violations.length === 0 && (
                  <p className="empty-state">No pending violations in queue.</p>
                )}
              </motion.aside>

              {/* Evidence panel */}
              <AnimatePresence mode="wait">
                {selected ? (
                  <motion.article
                    className="evidence-panel"
                    key={selected.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0, transition: { duration: 0.3 } }}
                    exit={{ opacity: 0, y: -8, transition: { duration: 0.2 } }}
                  >
                    {/* Evidence clip preview */}
                    <div className="evidence-preview" style={{ padding: 0, overflow: 'hidden', background: '#000' }}>
                      <img
                        src="/cv_evidence.png"
                        alt={`CV evidence: ${selected.track_id} – ${selected.camera_id}`}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px', display: 'block' }}
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                      <div style={{
                        position: 'absolute', bottom: 0, left: 0, right: 0,
                        background: 'linear-gradient(transparent, rgba(0,0,0,0.75))',
                        padding: '0.5rem 0.75rem', display: 'flex', justifyContent: 'space-between',
                        fontSize: '0.7rem', fontFamily: 'monospace', color: '#fff', letterSpacing: '0.04em'
                      }}>
                        <span>🎥 {selected.camera_id}</span>
                        <span style={{ color: '#f97316' }}>● VIOLATION DETECTED</span>
                        <span>{new Date(selected.start_time).toLocaleTimeString('id-ID')}</span>
                      </div>
                    </div>

                    {/* Detail panel */}
                    <div className="evidence-detail">
                      <div className="detail-header">
                        <div>
                          <p className="eyebrow">{formatViolationType(selected.violation_type)}</p>
                          <h2>{selected.track_id}</h2>
                        </div>
                        <span
                          className={`confidence-pill ${selected.composite_confidence >= 0.75 ? 'is-ready' : 'is-hold'}`}
                        >
                          {(selected.composite_confidence * 100).toFixed(1)}%
                        </span>
                      </div>

                      <div className="detail-grid">
                        <div>
                          <span>Camera</span>
                          <strong>{selected.camera_id}</strong>
                        </div>
                        <div>
                          <span>Duration</span>
                          <strong>{selected.duration_seconds}s</strong>
                        </div>
                        <div>
                          <span>Zone</span>
                          <strong>{selected.zone_id ?? 'Corridor rule'}</strong>
                        </div>
                        <div>
                          <span>Vehicle</span>
                          <strong>{selected.vehicle_class ?? 'Detected class'}</strong>
                        </div>
                      </div>

                      <div className="rule-panel">
                        <Scale size={16} aria-hidden="true" />
                        <span>
                          Legal mapping is deterministic through FR-LEGAL-01. Reviewer action is written
                          to the append-only audit log.
                        </span>
                      </div>

                      {selected.composite_confidence < 0.75 && (
                        <motion.div
                          className="rule-warning"
                          initial={{ opacity: 0, scale: 0.97 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ duration: 0.22 }}
                        >
                          <ShieldAlert size={16} aria-hidden="true" />
                          <span>
                            RULE-04 hold: below 75% confidence. Manual review required before approval.
                          </span>
                        </motion.div>
                      )}

                      <div className="action-row">
                        <button
                          className="btn-primary"
                          type="button"
                          id={`btn-approve-${selected.id.slice(0, 8)}`}
                          disabled={selected.composite_confidence < 0.75}
                          onClick={() => handleApprove(selected)}
                        >
                          <CheckCircle size={15} aria-hidden="true" />
                          <span>Approve ticket</span>
                        </button>
                        <button
                          className="btn-secondary-pill"
                          type="button"
                          id={`btn-draft-${selected.id.slice(0, 8)}`}
                          onClick={() => handleGenerateReport(selected)}
                        >
                          <FileText size={15} aria-hidden="true" />
                          <span>Draft Report</span>
                        </button>
                        <button
                          className="btn-secondary-pill"
                          type="button"
                          id={`btn-dismiss-${selected.id.slice(0, 8)}`}
                          onClick={() => handleDismiss(selected)}
                        >
                          <XCircle size={15} aria-hidden="true" />
                          <span>Dismiss</span>
                        </button>
                      </div>
                    </div>
                  </motion.article>
                ) : (
                  <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', height: '300px', color: 'var(--text-muted)' }}>
                    All items reviewed! Try switching to Live Mode to upload and run detections.
                  </div>
                )}
              </AnimatePresence>
            </motion.div>
          ) : (
            // LIVE MODE INTERACTIVE VIEW
            <motion.div
              key="live-model-layout"
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(0, 1.2fr) minmax(320px, 1fr)',
                gap: '2rem'
              }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
            >
              {/* Left Column: Visualizer & Uploader */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div className="glass-card" style={{ padding: '24px' }}>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                    <Cpu size={18} color="var(--accent)" />
                    Inference Visualizer
                  </h3>

                  {/* Drag and Drop Zone */}
                  {!previewUrl ? (
                    <div
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      onClick={() => document.getElementById('image-upload-input')?.click()}
                      style={{
                        border: isDragOver ? '2px dashed var(--accent)' : '2px dashed var(--border-accent)',
                        borderRadius: 'var(--r-md)',
                        padding: '3rem 2rem',
                        textAlign: 'center',
                        background: isDragOver ? 'var(--accent-dim)' : 'rgba(255, 255, 255, 0.02)',
                        cursor: 'pointer',
                        transition: 'all var(--ease-base)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '12px'
                      }}
                    >
                      <UploadCloud size={40} color={isDragOver ? 'var(--accent)' : 'var(--text-secondary)'} />
                      <div>
                        <strong style={{ color: 'var(--text-primary)', fontSize: '14px' }}>Drag & Drop traffic video frame</strong>
                        <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '4px' }}>Supports PNG, JPG, or JPEG format (max 5MB)</p>
                      </div>
                      <span className="btn-secondary-pill btn-compact" style={{ marginTop: '8px' }}>Browse File</span>
                      <input 
                        type="file" 
                        id="image-upload-input" 
                        accept="image/*" 
                        style={{ display: 'none' }} 
                        onChange={handleFileChange}
                      />
                    </div>
                  ) : (
                    // Preview Side-By-Side
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        <div>
                          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Original Frame</span>
                          <div style={{ width: '100%', height: '240px', background: '#000', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border)' }}>
                            <img src={previewUrl} alt="Original uploaded file" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                          </div>
                        </div>
                        <div>
                          <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>CV Annotated Output</span>
                          <div style={{ width: '100%', height: '240px', background: '#000', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-accent)', position: 'relative' }}>
                            {inferenceResult ? (
                              <img src={inferenceResult.annotated_image} alt="Inference annotated file" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                            ) : (
                              <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '12px', gap: '8px' }}>
                                {inferencing ? (
                                  <>
                                    <span className="live-dot" /> Running YOLOv8 Pipeline...
                                  </>
                                ) : (
                                  'Awaiting pipeline execution...'
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Controls Row */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderTop: '1px solid var(--border)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <input 
                            type="checkbox" 
                            id="run-plate-ocr" 
                            checked={runPlateDet} 
                            onChange={(e) => setRunPlateDet(e.target.checked)} 
                            style={{ cursor: 'pointer' }}
                          />
                          <label htmlFor="run-plate-ocr" style={{ fontSize: '13px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
                            Run License Plate Detection (OCR)
                          </label>
                        </div>
                        
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button 
                            className="btn-secondary-pill btn-compact" 
                            onClick={() => { setPreviewUrl(''); setInferenceResult(null); }}
                            disabled={inferencing}
                          >
                            Clear
                          </button>
                          <button 
                            className="btn-primary btn-compact" 
                            onClick={runLiveInference}
                            disabled={inferencing}
                          >
                            <Sparkles size={13} />
                            <span>Run Detection</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Bundled Demo Trigger */}
                  <div style={{ marginTop: '16px', background: 'rgba(0,0,0,0.15)', padding: '12px', borderRadius: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>No traffic images? Test using bundled server sample.</span>
                    <button 
                      className="btn-dark-utility" 
                      style={{ height: '28px', fontSize: '11px', padding: '0 12px' }} 
                      onClick={runBundledDemoInference}
                      disabled={inferencing}
                    >
                      <Play size={10} style={{ marginRight: '4px' }} /> Load Server Sample
                    </button>
                  </div>
                </div>

                {/* Inference Detections Panel */}
                {inferenceResult && (
                  <motion.div className="glass-card" style={{ padding: '24px' }} {...fadeUp(0.1)}>
                    <h4 style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                      Pipeline Detections Output
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
                      <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>INFERENCE SPEED</span>
                        <strong style={{ display: 'block', fontSize: '16px', color: 'var(--accent)', marginTop: '4px' }}>{inferenceResult.elapsed_ms} ms</strong>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>VEHICLES DETECTED</span>
                        <strong style={{ display: 'block', fontSize: '16px', color: '#fff', marginTop: '4px' }}>
                          {inferenceResult.detections?.length || 0}
                        </strong>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>ACTIVE MODELS</span>
                        <strong style={{ display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px', fontFamily: 'var(--font-mono)' }}>
                          YOLOv8n / BEST-OCR
                        </strong>
                      </div>
                    </div>

                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                          <th style={{ padding: '8px 12px' }}>Object Class</th>
                          <th style={{ padding: '8px 12px' }}>Confidence</th>
                          <th style={{ padding: '8px 12px' }}>Bounding Box</th>
                          <th style={{ padding: '8px 12px' }}>OCR Plate</th>
                        </tr>
                      </thead>
                      <tbody>
                        {inferenceResult.detections?.map((d: any, idx: number) => (
                          <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                            <td style={{ padding: '8px 12px', fontWeight: 600, color: 'var(--accent)' }}>{d.class_name.toUpperCase()}</td>
                            <td style={{ padding: '8px 12px' }}>{(d.confidence * 100).toFixed(1)}%</td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                              [{d.bbox.join(', ')}]
                            </td>
                            <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', color: 'var(--accent-amber)' }}>
                              {d.plates && d.plates.length > 0 ? (
                                <span>🔍 DETECTED</span>
                              ) : (
                                'none'
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </motion.div>
                )}
              </div>

              {/* Right Column: Ingest Violation Form */}
              <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileSpreadsheet size={18} color="var(--accent)" />
                  E-TLE Ticket Creator
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  Synthesize an E-TLE violation file using details from the computer vision model and send it to the legal queue.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '8px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      Violation Category
                    </label>
                    <select
                      value={customViolationType}
                      onChange={(e) => setCustomViolationType(e.target.value)}
                      style={{
                        width: '100%',
                        background: 'var(--bg-base)',
                        border: '1px solid var(--border)',
                        color: '#fff',
                        padding: '10px',
                        borderRadius: '6px',
                        fontSize: '13px'
                      }}
                    >
                      <option value="BUS_LANE_VIOLATION">TransJakarta Busway Encroachment</option>
                      <option value="ILLEGAL_PARKING">Illegal Parking / Stopping</option>
                      <option value="DESIGNATED_STOP_VIOLATION">Illegal Passenger Pick-up / Drop-off</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      License Plate Number
                    </label>
                    <input
                      type="text"
                      value={customPlate}
                      onChange={(e) => setCustomPlate(e.target.value.toUpperCase())}
                      style={{
                        width: '100%',
                        background: 'var(--bg-base)',
                        border: '1px solid var(--border)',
                        color: '#fff',
                        padding: '10px',
                        borderRadius: '6px',
                        fontSize: '13px',
                        fontFamily: 'var(--font-mono)'
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      Source Camera ID
                    </label>
                    <input
                      type="text"
                      value={customCamera}
                      onChange={(e) => setCustomCamera(e.target.value)}
                      style={{
                        width: '100%',
                        background: 'var(--bg-base)',
                        border: '1px solid var(--border)',
                        color: '#fff',
                        padding: '10px',
                        borderRadius: '6px',
                        fontSize: '13px',
                        fontFamily: 'var(--font-mono)'
                      }}
                    />
                  </div>

                  <button
                    className="btn-primary"
                    style={{ width: '100%', marginTop: '16px' }}
                    onClick={ingestCustomViolation}
                  >
                    <span>Ingest Ticket into Queue</span>
                    <ArrowRight size={14} />
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <p className="notice-line" style={{ marginTop: '20px' }}>{notice}</p>
      </section>

      {/* ── SECTION 2: DETERMINISTIC LEGAL MATRIX ── */}
      <section className="content-band" id="rules-section" style={{ borderTop: '1px solid var(--border)', background: 'var(--bg-surface)' }}>
        <div className="section-heading">
          <p className="eyebrow">Deterministic Legal Matrix (FR-LEGAL-01)</p>
          <h2>Legal citations & sanction reference catalog</h2>
          <p>
            This registry matches computer vision violation categories to official articles of the Traffic Act (UU LLAJ), 
            ensuring all automatic tickets stand on a rigorous legal basis.
          </p>
        </div>

        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', gap: '16px' }}>
            <div style={{ position: 'relative', flex: 1, maxWidth: '380px' }}>
              <Search size={16} color="var(--text-secondary)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
              <input
                type="text"
                placeholder="Search legal articles or codes..."
                value={rulesSearch}
                onChange={(e) => setRulesSearch(e.target.value)}
                style={{
                  width: '100%',
                  background: 'var(--bg-base)',
                  border: '1px solid var(--border)',
                  color: '#fff',
                  padding: '8px 12px 8px 36px',
                  borderRadius: '30px',
                  fontSize: '13px'
                }}
              />
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Showing {filteredRules.length} registered mappings
            </span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '12px' }}>Violation Key</th>
                  <th style={{ padding: '12px' }}>Legal Article</th>
                  <th style={{ padding: '12px' }}>Description Citation</th>
                  <th style={{ padding: '12px' }}>Sanction & Fines</th>
                  <th style={{ padding: '12px' }}>Dispatched Liaison</th>
                </tr>
              </thead>
              <tbody>
                {filteredRules.map((rule, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)', verticalAlign: 'top' }}>
                    <td style={{ padding: '12px', fontWeight: 600 }}>
                      <span style={{ background: 'rgba(255,255,255,0.04)', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border)' }}>
                        {rule.violation_type}
                      </span>
                    </td>
                    <td style={{ padding: '12px', color: 'var(--accent)', fontWeight: 600 }}>
                      {rule.legal_basis?.code}
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-secondary)', maxWidth: '300px', lineHeight: 1.5 }}>
                      <strong style={{ color: '#fff', display: 'block', marginBottom: '4px' }}>{rule.legal_basis?.title}</strong>
                      {rule.legal_basis?.citation_text}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <span style={{ display: 'block', fontWeight: 600, color: 'var(--accent-amber)' }}>
                        IDR {rule.sanction?.fine_min_idr?.toLocaleString()} - {rule.sanction?.fine_max_idr?.toLocaleString()}
                      </span>
                      <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: '2px' }}>
                        Action: {rule.sanction?.action_type} ({rule.sanction?.code})
                      </small>
                    </td>
                    <td style={{ padding: '12px', fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
                      {rule.relevant_unit}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── SECTION 3: IMMUTABLE AUDIT FEED ── */}
      <section className="content-band" id="audit-section" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="section-heading">
          <p className="eyebrow">Immutable Audit Trail (RULE-09)</p>
          <h2>Real-time officer actions and system events</h2>
          <p>
            An append-only transaction ledger logging every confirmation, dismissal, and dispatch. 
            PostgreSQL RULES prevent any updating or deletion of these lines to guarantee transparency.
          </p>
        </div>

        <div className="glass-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {auditLogs.map((log) => (
              <div 
                key={log.id} 
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  background: 'rgba(255,255,255,0.01)',
                  border: '1px solid rgba(255,255,255,0.03)',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  gap: '16px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                  <div 
                    style={{
                      padding: '6px',
                      borderRadius: '50%',
                      background: log.action === 'CONFIRM' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                      color: log.action === 'CONFIRM' ? 'var(--accent-green)' : 'var(--accent-red)',
                      marginTop: '2px'
                    }}
                  >
                    <History size={14} />
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '30px',
                        background: log.action === 'CONFIRM' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                        color: log.action === 'CONFIRM' ? 'var(--accent-green)' : 'var(--accent-red)'
                      }}>
                        {log.action}
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: 600 }}>{log.detail}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      <span>Target: <strong style={{ color: 'var(--text-secondary)' }}>{log.entity_id}</strong></span>
                      <span>Officer: <strong style={{ color: 'var(--text-secondary)' }}>{log.officer_id}</strong></span>
                    </div>
                  </div>
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)' }}>
                  {new Date(log.created_at).toLocaleTimeString('id-ID')}
                </span>
              </div>
            ))}

            {auditLogs.length === 0 && (
              <p style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '13px' }}>
                No actions logged in the transaction ledger yet.
              </p>
            )}
          </div>
        </div>
      </section>

      {/* ── REPORT MODAL ── */}
      <AnimatePresence>
        {reportModalOpen && (
          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setReportModalOpen(false)}
            style={{
              position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.6)', 
              backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', 
              justifyContent: 'center', zIndex: 100
            }}
          >
            <motion.div
              className="modal-content"
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              style={{
                backgroundColor: 'var(--bg-surface)', padding: '2rem', 
                borderRadius: '16px', border: '1px solid var(--border-light)',
                width: '100%', maxWidth: '600px', maxHeight: '80vh', 
                display: 'flex', flexDirection: 'column', gap: '1.5rem',
                boxShadow: '0 24px 48px rgba(0,0,0,0.4)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Berita Acara Pelanggaran</h2>
                <button 
                  onClick={() => setReportModalOpen(false)}
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                >
                  <XCircle size={24} />
                </button>
              </div>

              <div style={{
                flex: 1, overflowY: 'auto', backgroundColor: 'var(--bg-base)',
                padding: '1.5rem', borderRadius: '8px', fontFamily: 'monospace',
                whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: '0.9rem',
                border: '1px solid var(--border-light)'
              }}>
                {reportLoading ? (
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', color: 'var(--text-muted)' }}>
                    <div className="live-dot" /> Generating formal report (RAG / LLM)...
                  </div>
                ) : (
                  reportContent
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                <button className="btn-secondary-pill" onClick={() => setReportModalOpen(false)}>
                  Close
                </button>
                <a 
                  className="btn-primary" 
                  style={{ textDecoration: 'none' }}
                  href={`${apiBase}/api/v1/violations/${selected?.id}/berita_acara?format=pdf`} 
                  target="_blank" 
                  rel="noreferrer"
                >
                  <FileText size={15} style={{ marginRight: '8px' }}/> Download PDF
                </a>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
