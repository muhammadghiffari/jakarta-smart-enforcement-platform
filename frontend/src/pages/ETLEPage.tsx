import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, FileText, Scale, ShieldAlert, XCircle } from 'lucide-react';
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
  const [violations, setViolations] = useState<Violation[]>(demoViolations);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(demoViolations[0]?.id ?? '');
  const [notice, setNotice] = useState('Demo queue loaded while the API is warming up.');

  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [reportContent, setReportContent] = useState('');
  const [reportLoading, setReportLoading] = useState(false);

  const selected = violations.find((v) => v.id === selectedId) ?? violations[0];

  const queueSummary = useMemo(() => {
    const ready = violations.filter((v) => v.composite_confidence >= 0.75).length;
    return [
      { label: 'Pending review', value: violations.length },
      { label: 'Auto-ready',     value: ready },
      { label: 'Manual gate',    value: violations.length - ready },
    ];
  }, [violations]);

  const fetchViolations = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/v1/violations?status=DETECTED`);
      if (!res.ok) throw new Error('Unable to load queue');
      const data = (await res.json()) as { items?: Violation[] };
      const items = data.items ?? [];
      setViolations(items);
      setSelectedId((cur) => (items.some((i) => i.id === cur) ? cur : items[0]?.id ?? ''));
      setNotice('Connected to API queue. Data is live.');
    } catch {
      setNotice('⚠️ Using curated demo queue. API queue is not reachable yet. Start the backend or continue in Demo Mode.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(fetchViolations, 0);
    const timer   = window.setInterval(fetchViolations, 5000);
    return () => { window.clearTimeout(initial); window.clearInterval(timer); };
  }, [fetchViolations]);

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
    } catch {
      removeFromQueue(violation.id);
      setNotice(`${violation.track_id} approved in demo mode.`);
    }
  };

  const handleDismiss = async (violation: Violation) => {
    try {
      await fetch(`${apiBase}/api/v1/violations/${violation.id}/dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ officer_id: 'OFC-DEMO-01', reason: 'DEMO DISMISS' }),
      });
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
      // Demo fallback text if the API isn't running
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

  return (
    <>
      {/* ── HERO ── */}
      <motion.section className="ops-hero" {...fadeUp(0)}>
        <div className="ops-hero-copy">
          <p className="eyebrow">Human-in-the-loop enforcement</p>
          <h1>A focused E-TLE queue with clear legal and confidence gates.</h1>
          <p>
            Reviewers see the evidence, model confidence, deterministic rule checks, and audit action
            in one place before the ticket is confirmed.
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

      {/* ── QUEUE + EVIDENCE ── */}
      <section className="content-band" id="review">
        <div className="queue-shell">
          {/* Queue sidebar */}
          <motion.aside className="queue-list" aria-label="Violation queue" {...fadeUp(0.08)}>
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Detected</p>
                <h2>Queue</h2>
              </div>
              <span className={`status-pill ${!loading ? 'is-live' : ''}`}>
                <span className="live-dot" />
                {loading ? 'Syncing' : 'Ready'}
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
            {selected && (
              <motion.article
                className="evidence-panel"
                key={selected.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0, transition: { duration: 0.3 } }}
                exit={{ opacity: 0, y: -8, transition: { duration: 0.2 } }}
              >
                {/* Evidence clip preview — CV annotated screenshot */}
                <div className="evidence-preview" style={{ padding: 0, overflow: 'hidden', background: '#000' }}>
                  <img
                    src="/cv_evidence.png"
                    alt={`CV evidence: ${selected.track_id} – ${selected.camera_id}`}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px', display: 'block' }}
                    onError={(e) => {
                      // Fallback: show camera icon with metadata overlay if image missing
                      (e.target as HTMLImageElement).style.display = 'none';
                    }}
                  />
                  {/* Overlay HUD on top of the image */}
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
                      to the audit log.
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
            )}
          </AnimatePresence>
        </div>
        <p className="notice-line">{notice}</p>
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
                  href={`${apiBase}/api/v1/violations/${selected.id}/berita_acara?format=pdf`} 
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
