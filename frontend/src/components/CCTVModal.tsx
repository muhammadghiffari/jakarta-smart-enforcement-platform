import { motion, AnimatePresence } from 'framer-motion';
import { X, Camera, AlertTriangle, Activity } from 'lucide-react';
import { useState, useEffect } from 'react';
import SignalScene from './SignalScene';

interface CCTVModalProps {
  isOpen: boolean;
  onClose: () => void;
  zoneInfo: {
    name: string;
    type: string;
  } | null;
}

export default function CCTVModal({ isOpen, onClose, zoneInfo }: CCTVModalProps) {
  const [videoError, setVideoError] = useState(false);

  // Reset video error state when modal opens
  useEffect(() => {
    if (isOpen) {
      setVideoError(false);
    }
  }, [isOpen]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <style>
            {`
              .cctv-modal-container {
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 95vw;
                max-width: 1200px;
                height: 85vh;
                background-color: #0a0f18;
                border: 1px solid rgba(0, 212, 255, 0.2);
                border-radius: 12px;
                z-index: 101;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                box-shadow: 0 24px 48px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(0, 212, 255, 0.1);
              }
              
              .cctv-modal-body {
                flex: 1;
                display: flex;
                flex-direction: row;
                position: relative;
                overflow: hidden;
              }
              
              .cctv-sidebar {
                width: 300px;
                border-left: 1px solid rgba(0, 212, 255, 0.1);
                background-color: rgba(0, 0, 0, 0.3);
                padding: 24px;
                display: flex;
                flex-direction: column;
                gap: 24px;
                overflow-y: auto;
              }
              
              @media (max-width: 768px) {
                .cctv-modal-container {
                  width: 100vw;
                  height: 100vh;
                  border-radius: 0;
                  border: none;
                }
                .cctv-modal-body {
                  flex-direction: column;
                }
                .cctv-sidebar {
                  width: 100%;
                  height: 40%;
                  border-left: none;
                  border-top: 1px solid rgba(0, 212, 255, 0.1);
                }
              }
            `}
          </style>

          <motion.div
            className="modal-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              backdropFilter: 'blur(4px)',
              zIndex: 100,
            }}
          />
          <motion.div
            className="cctv-modal-container"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
          >
            {/* Modal Header */}
            <header style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '16px 24px',
              borderBottom: '1px solid rgba(0, 212, 255, 0.1)',
              background: 'linear-gradient(to right, rgba(0, 212, 255, 0.05), transparent)',
              flexShrink: 0
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Camera size={20} color="#00d4ff" />
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#fff', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {zoneInfo?.name || 'Live Camera Feed'}
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)' }}>
                    <span style={{ display: 'inline-flex', width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#00ffaa', boxShadow: '0 0 8px #00ffaa' }} />
                    LIVE FEED ACTIVE
                    <span style={{ opacity: 0.5 }}>|</span>
                    ZONE TYPE: {zoneInfo?.type || 'UNKNOWN'}
                  </div>
                </div>
              </div>
              <button
                onClick={onClose}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'rgba(255,255,255,0.5)',
                  cursor: 'pointer',
                  padding: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: '4px',
                  transition: 'background 0.2s, color 0.2s'
                }}
                onMouseOver={(e) => { e.currentTarget.style.color = '#fff'; e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.1)'; }}
                onMouseOut={(e) => { e.currentTarget.style.color = 'rgba(255,255,255,0.5)'; e.currentTarget.style.backgroundColor = 'transparent'; }}
              >
                <X size={24} />
              </button>
            </header>

            {/* Main Content Area */}
            <div className="cctv-modal-body">
              {/* Scene Viewer */}
              <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
                 {/* Decorative overlay elements */}
                 <div style={{ position: 'absolute', top: 20, left: 20, zIndex: 10, color: '#00d4ff', fontFamily: 'monospace', fontSize: '12px', opacity: 0.7 }}>
                   REC [:::]<br/>
                   FPS: 60<br/>
                   LATENCY: 12ms
                 </div>
                 
                 {/* The actual 3D scene or Real Video */}
                 {!videoError ? (
                   <video 
                     src="/demo.mp4" 
                     autoPlay 
                     loop 
                     muted 
                     playsInline
                     onError={() => setVideoError(true)}
                     style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                   />
                 ) : (
                   <SignalScene />
                 )}
                 
                 {/* Reticle / Crosshair decorative */}
                 <div style={{
                   position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                   width: 'min(40vw, 300px)', height: 'min(40vh, 300px)', border: '1px solid rgba(0, 212, 255, 0.1)', pointerEvents: 'none', zIndex: 5
                 }}>
                    <div style={{ position: 'absolute', top: -5, left: -5, width: 20, height: 20, borderTop: '2px solid rgba(0, 212, 255, 0.5)', borderLeft: '2px solid rgba(0, 212, 255, 0.5)' }} />
                    <div style={{ position: 'absolute', top: -5, right: -5, width: 20, height: 20, borderTop: '2px solid rgba(0, 212, 255, 0.5)', borderRight: '2px solid rgba(0, 212, 255, 0.5)' }} />
                    <div style={{ position: 'absolute', bottom: -5, left: -5, width: 20, height: 20, borderBottom: '2px solid rgba(0, 212, 255, 0.5)', borderLeft: '2px solid rgba(0, 212, 255, 0.5)' }} />
                    <div style={{ position: 'absolute', bottom: -5, right: -5, width: 20, height: 20, borderBottom: '2px solid rgba(0, 212, 255, 0.5)', borderRight: '2px solid rgba(0, 212, 255, 0.5)' }} />
                 </div>
              </div>

              {/* Sidebar Metrics (Simulated CV Info) */}
              <aside className="cctv-sidebar">

                 <div>
                   <h4 style={{ color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.1em', marginBottom: '12px' }}>
                     Detection Status
                   </h4>
                   <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#00ffaa', backgroundColor: 'rgba(0, 255, 170, 0.05)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(0, 255, 170, 0.2)' }}>
                     <Activity size={20} />
                     <strong style={{ fontSize: '0.9rem' }}>SYSTEM NOMINAL</strong>
                   </div>
                 </div>
                 
                 <div>
                   <h4 style={{ color: 'rgba(255,255,255,0.4)', textTransform: 'uppercase', fontSize: '0.75rem', letterSpacing: '0.1em', marginBottom: '12px' }}>
                     Recent Alerts
                   </h4>
                   <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                     {[1, 2, 3].map((_, i) => (
                       <div key={i} style={{ display: 'flex', gap: '12px', padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px', borderLeft: '2px solid #ffaa00' }}>
                         <AlertTriangle size={16} color="#ffaa00" style={{ marginTop: '2px' }} />
                         <div>
                           <div style={{ fontSize: '0.85rem', color: '#fff', marginBottom: '4px' }}>Potential Violation detected</div>
                           <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)', fontFamily: 'monospace' }}>Confidence: {(0.85 + Math.random() * 0.14).toFixed(2)} - {Math.floor(Math.random() * 60)}s ago</div>
                         </div>
                       </div>
                     ))}
                   </div>
                 </div>
              </aside>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
