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
      setNotice('Connected to API queue.');
    } catch {
      setNotice('Using curated demo queue. API queue is not reachable yet.');
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
                {/* Evidence clip preview */}
                <div className="evidence-preview">
                  <div className="camera-reticle" />
                  <FileText size={40} aria-hidden="true" style={{ color: 'var(--text-muted)' }} />
                  <span>Evidence clip</span>
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
    </>
  );
}
