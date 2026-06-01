import { motion } from 'framer-motion';
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  Cpu,
  Database,
  FileImage,
  Gauge,
  HardDrive,
  Loader2,
  Play,
  RadioTower,
  ScanLine,
  ShieldCheck,
  Upload,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { ChangeEvent } from 'react';

import SignalScene from '../components/SignalScene';
import { demoFeedEvents, formatViolationType } from '../lib/demoContent';
import type { FeedEvent } from '../lib/demoContent';

type IncomingViolation = {
  id: string;
  type: string;
  plate: string;
  camera: string;
  timestamp: string;
  confidence?: number;
};

type Detection = {
  id: string;
  bbox: number[];
  class_name: string;
  confidence: number;
  plates: { bbox: number[]; confidence: number }[];
};

type InferenceResult = {
  source: SourceInfo;
  model: {
    vehicle_model: string;
    vehicle_model_exists: boolean;
    plate_model: string;
    plate_model_exists: boolean;
    plate_detection: boolean;
  };
  elapsed_ms: number;
  image_width: number;
  image_height: number;
  detections: Detection[];
  annotated_image: string;
};

type SourceInfo = {
  type: string;
  name: string;
  path: string | null;
  note: string;
};

type ModelStatus = {
  sources: SourceInfo[];
  vehicle_model: string;
  vehicle_model_exists: boolean;
  vehicle_loaded: boolean;
  plate_model: string;
  plate_model_exists: boolean;
  plate_loaded: boolean;
};

const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const normalizeTimestamp = (value: string) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.45, delay } },
});

const stagger = {
  animate: { transition: { staggerChildren: 0.07 } },
};

const itemFade = {
  initial: { opacity: 0, x: -12 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.35 } },
};

export default function DashboardPage() {
  const [events, setEvents] = useState<FeedEvent[]>(demoFeedEvents);
  const [socketState, setSocketState] = useState<'Live' | 'Demo' | 'Offline'>('Demo');
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [result, setResult] = useState<InferenceResult | null>(null);
  const [preview, setPreview] = useState<string>('');
  const [isRunning, setIsRunning] = useState(false);
  const [notice, setNotice] = useState('Run the bundled sample or upload a traffic frame to execute the real detector.');

  useEffect(() => {
    fetch(`${apiBase}/api/v1/inference/model`)
      .then((res) => res.json())
      .then((data: ModelStatus) => setModelStatus(data))
      .catch(() => setNotice('Model API is not reachable yet. Start the backend, then run inference.'));
  }, []);

  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/feed';
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => setSocketState('Live');
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data) as { type?: string; data?: IncomingViolation };
      const incoming = message.data;
      if (message.type === 'NEW_VIOLATION' && incoming) {
        setEvents((prev) => [
          {
            id: incoming.id,
            type: incoming.type,
            plate: incoming.plate,
            camera: incoming.camera,
            timestamp: normalizeTimestamp(incoming.timestamp),
            confidence: incoming.confidence ?? 0,
          },
          ...prev,
        ].slice(0, 12));
      }
    };
    ws.onerror = () => setSocketState('Offline');
    ws.onclose = () => setSocketState((s) => (s === 'Live' ? 'Offline' : s));
    return () => ws.close();
  }, []);

  const topDetection = useMemo(
    () => result?.detections.reduce<Detection | null>(
      (best, item) => (!best || item.confidence > best.confidence ? item : best),
      null,
    ),
    [result],
  );

  const activeSource = result?.source ?? modelStatus?.sources?.[0];

  const runDemoInference = async () => {
    setIsRunning(true);
    setNotice('Running YOLO inference on the bundled Ultralytics traffic sample…');
    try {
      const res = await fetch(`${apiBase}/api/v1/inference/demo`, { method: 'POST' });
      if (!res.ok) throw new Error('Inference failed');
      const data = (await res.json()) as InferenceResult;
      setResult(data);
      setPreview('');
      setNotice(`Real model completed in ${data.elapsed_ms}ms — ${data.detections.length} detections.`);
    } catch {
      setNotice('Inference failed. Make sure the FastAPI backend is running on port 8000.');
    } finally {
      setIsRunning(false);
    }
  };

  const runImageInference = async (imageBase64: string) => {
    setIsRunning(true);
    setNotice('Running real detector on uploaded frame…');
    try {
      const res = await fetch(`${apiBase}/api/v1/inference/image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageBase64, run_plate_detection: false }),
      });
      if (!res.ok) throw new Error('Inference failed');
      const data = (await res.json()) as InferenceResult;
      setResult(data);
      setNotice(`Model returned ${data.detections.length} detections in ${data.elapsed_ms}ms.`);
    } catch {
      setNotice('Upload inference failed. Check API logs for model or image decode errors.');
    } finally {
      setIsRunning(false);
    }
  };

  const handleUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const imageBase64 = String(reader.result);
      setPreview(imageBase64);
      runImageInference(imageBase64);
    };
    reader.readAsDataURL(file);
  };

  return (
    <>
      {/* ── REAL SOURCE TRANSPARENCY BANNER ── */}
      <motion.section
        className="source-band"
        aria-label="Real model sources"
        {...fadeUp(0)}
      >
        {(modelStatus?.sources ?? []).map((source) => (
          <article className="source-card" key={source.type}>
            <Database size={17} aria-hidden="true" />
            <div>
              <strong>{source.name}</strong>
              <span>{source.path ?? 'Browser-selected image payload'}</span>
              <small>{source.note}</small>
            </div>
          </article>
        ))}

        {/* API endpoint always visible */}
        <article className="source-card">
          {modelStatus ? (
            <HardDrive size={17} aria-hidden="true" />
          ) : (
            <WifiOff size={17} aria-hidden="true" style={{ color: 'var(--accent-amber)' }} />
          )}
          <div>
            <strong style={{ color: modelStatus ? undefined : 'var(--accent-amber)' }}>
              {modelStatus ? 'Inference API' : 'API offline'}
            </strong>
            <span>{apiBase}/api/v1/inference/model</span>
            <small>
              {modelStatus
                ? `Weights: ${modelStatus.vehicle_model} — ${modelStatus.vehicle_model_exists ? '✓ found' : '✗ missing'}`
                : 'Start the FastAPI backend to activate the real source.'}
            </small>
          </div>
        </article>

        <article className="source-card">
          {socketState === 'Live' ? (
            <Wifi size={17} aria-hidden="true" style={{ color: 'var(--accent-green)' }} />
          ) : (
            <WifiOff size={17} aria-hidden="true" style={{ color: 'var(--accent-amber)' }} />
          )}
          <div>
            <strong style={{ color: socketState === 'Live' ? 'var(--accent-green)' : undefined }}>
              WebSocket — {socketState}
            </strong>
            <span>{import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/feed'}</span>
            <small>Live violation stream from detection pipeline.</small>
          </div>
        </article>
      </motion.section>

      {/* ── MODEL HERO ── */}
      <motion.section
        className="model-hero"
        id="live"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <motion.div className="model-copy" {...fadeUp(0.05)}>
          <p className="eyebrow">Real model online</p>
          <h1>JSEP sees the road before the queue fills up.</h1>
          <p>
            Run the local YOLO detector against an actual traffic frame, inspect the annotated
            evidence, then let deterministic rules decide what becomes an E-TLE case.
          </p>
          <div className="hero-actions">
            <button
              className="btn-primary"
              type="button"
              id="btn-run-demo"
              onClick={runDemoInference}
              disabled={isRunning}
            >
              {isRunning
                ? <Loader2 className="spin" size={16} aria-hidden="true" />
                : <Play size={16} aria-hidden="true" />}
              <span>Run real model</span>
            </button>
            <label className="btn-secondary-pill upload-button" htmlFor="frame-upload">
              <Upload size={16} aria-hidden="true" />
              <span>Upload frame</span>
              <input id="frame-upload" accept="image/*" type="file" onChange={handleUpload} />
            </label>
          </div>
        </motion.div>

        <motion.div className="model-stack" {...fadeUp(0.12)}>
          {/* 3D Signal Scene */}
          <div className="source-orbit" aria-label="WebGL camera network scene">
            <SignalScene />
            <div className="source-overlay">
              <span>
                <RadioTower size={11} aria-hidden="true" />
                Active source
              </span>
              <strong>{activeSource?.name ?? 'Waiting for source…'}</strong>
              <small>{activeSource?.path ?? 'Upload a frame or run the demo to connect a source.'}</small>
            </div>
          </div>

          {/* Model stage / inference canvas */}
          <div className="model-stage" aria-label="Model inference canvas">
            <div className="model-stage-top">
              <span
                className={`status-pill ${socketState === 'Live' ? 'is-live' : ''}`}
                id="ws-status-pill"
              >
                <span className="live-dot" />
                {socketState}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                {modelStatus?.vehicle_model ?? 'models/yolo26n.pt'}
              </span>
            </div>
            <div className="model-image-wrap">
              {result?.annotated_image || preview ? (
                <img src={result?.annotated_image ?? preview} alt="Model-annotated traffic frame" />
              ) : (
                <div className="empty-model-canvas">
                  <ScanLine size={40} aria-hidden="true" />
                  <span>Ready for inference</span>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.section>

      {/* ── RIBBON STATS ── */}
      <motion.section className="model-ribbon" id="insights" {...fadeUp(0.18)}>
        {[
          { icon: Gauge,       label: 'Latency',        value: result ? `${result.elapsed_ms}ms` : '—' },
          { icon: Camera,      label: 'Detections',     value: result?.detections.length ?? 0 },
          { icon: CheckCircle2,label: 'Top confidence', value: topDetection ? `${Math.round(topDetection.confidence * 100)}%` : '—' },
          { icon: ShieldCheck, label: 'Weights',        value: modelStatus?.vehicle_model_exists ? 'local ✓' : 'missing' },
        ].map(({ icon: Icon, label, value }) => (
          <motion.div key={label} whileHover={{ scale: 1.02 }} transition={{ duration: 0.15 }}>
            <Icon size={18} aria-hidden="true" />
            <span>{label}</span>
            <strong>{String(value)}</strong>
          </motion.div>
        ))}
      </motion.section>

      {/* ── DETECTION OUTPUT + LIVE BRIEF ── */}
      <section className="model-story-band">
        <div className="detection-sheet">
          <div className="section-heading">
            <p className="eyebrow">Detector output</p>
            <h2>Every box comes from the model, not a mocked dashboard tile.</h2>
          </div>
          <motion.div className="detection-list" variants={stagger} initial="initial" animate="animate">
            {result?.detections.length ? (
              result.detections.map((det) => (
                <motion.article className="detection-row" key={det.id} variants={itemFade}>
                  <Cpu size={17} aria-hidden="true" />
                  <div>
                    <strong>{det.class_name}</strong>
                    <span>bbox [{det.bbox.map((v) => Math.round(v)).join(', ')}]</span>
                  </div>
                  <span>{Math.round(det.confidence * 100)}%</span>
                </motion.article>
              ))
            ) : (
              <div className="empty-detections">
                <p><FileImage size={14} style={{ display: 'inline', marginRight: 6 }} aria-hidden="true" />{notice}</p>
              </div>
            )}
          </motion.div>
        </div>

        <aside className="live-brief" id="review">
          <p className="eyebrow">Event stream</p>
          <h2>Review signal</h2>
          <motion.div className="brief-feed" variants={stagger} initial="initial" animate="animate">
            {events.slice(0, 5).map((ev) => (
              <motion.article className="brief-item" key={ev.id} variants={itemFade}>
                <AlertCircle size={15} aria-hidden="true" />
                <div>
                  <strong>{ev.plate}</strong>
                  <span>{formatViolationType(ev.type)}</span>
                </div>
                <small style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontSize: 12 }}>
                  {Math.round(ev.confidence * 100)}%
                </small>
              </motion.article>
            ))}
          </motion.div>
          <p className="notice-line">{notice}</p>
        </aside>
      </section>
    </>
  );
}
