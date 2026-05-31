import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

interface Violation {
  id: string;
  track_id: string; // used as plate
  violation_type: string;
  composite_confidence: number;
  camera_id: string;
  duration_seconds: number;
  start_time: string;
}

export default function ETLEPage() {
  const [violations, setViolations] = useState<Violation[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchViolations = async () => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/violations?status=DETECTED`);
      const data = await res.json();
      setViolations(data.items || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchViolations();
    // Poll every 5s for new pending violations (or rely on WS in a larger state setup)
    const timer = setInterval(fetchViolations, 5000);
    return () => clearInterval(timer);
  }, []);

  const handleApprove = async (id: string, conf: number) => {
    if (conf < 0.75) {
      alert("Cannot auto-approve. Confidence < 0.75. Manual review required.");
      return;
    }
    
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/violations/${id}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ officer_id: 'OFC-DEMO-01' })
      });
      if (res.ok) {
        setViolations(vs => vs.filter(v => v.id !== id));
      } else {
        alert("Failed to confirm");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDismiss = async (id: string) => {
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/v1/violations/${id}/dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ officer_id: 'OFC-DEMO-01', reason: 'DEMO DISMISS' })
      });
      if (res.ok) {
        setViolations(vs => vs.filter(v => v.id !== id));
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="p-section max-w-[1440px] mx-auto">
      <div className="mb-12">
        <h1 className="text-display-lg">E-TLE Review Queue</h1>
        <p className="text-lead mt-4 text-body-muted">
          Review and approve detected violations for electronic ticketing.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {loading && <div className="text-ink-muted-80">Loading queue...</div>}
        {!loading && violations.map(v => (
          <div key={v.id} className="store-utility-card flex flex-col md:flex-row gap-6 animate-in fade-in slide-in-from-bottom-4">
            <div className="w-full md:w-1/3 bg-canvas-parchment rounded-sm aspect-video flex items-center justify-center border border-divider-soft">
               <span className="text-ink-muted-48">Violation Evidence Clip</span>
            </div>
            
            <div className="flex-1 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-display-md">{v.track_id}</h3>
                  <span className={`px-3 py-1 rounded-pill text-[12px] font-bold ${(v.composite_confidence || 0) >= 0.75 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    Conf: {((v.composite_confidence || 0) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="mt-2 text-[17px]">
                  <p><strong>Type:</strong> {v.violation_type.replace('_', ' ')}</p>
                  <p><strong>Camera:</strong> {v.camera_id}</p>
                  <p><strong>Duration:</strong> {v.duration_seconds || 0}s</p>
                </div>
              </div>

              <div className="flex items-center space-x-4 mt-6">
                <button 
                  onClick={() => handleApprove(v.id, v.composite_confidence || 0)}
                  className={`btn-primary flex items-center space-x-2 ${(v.composite_confidence || 0) < 0.75 ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={(v.composite_confidence || 0) < 0.75}
                >
                  <CheckCircle className="w-4 h-4" />
                  <span>Approve Ticket</span>
                </button>
                <button 
                  onClick={() => handleDismiss(v.id)}
                  className="btn-secondary-pill flex items-center space-x-2"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Dismiss</span>
                </button>
              </div>
              
              {(v.composite_confidence || 0) < 0.75 && (
                <p className="text-[12px] text-red-600 mt-2 font-semibold">
                  * RULE-04: Confidence below 75% requires explicit manual override.
                </p>
              )}
            </div>
          </div>
        ))}
        {!loading && violations.length === 0 && (
          <div className="text-center p-12 text-ink-muted-80">
            No pending violations in queue.
          </div>
        )}
      </div>
    </div>
  );
}
