import React, { useState, useEffect } from 'react';
import { Camera, AlertCircle } from 'lucide-react';

interface ViolationEvent {
  id: string;
  type: string;
  plate: string;
  camera: string;
  timestamp: string;
}

export default function DashboardPage() {
  const [events, setEvents] = useState<ViolationEvent[]>([]);

  // Connect to FastAPI WebSocket (PRD FR-DASH-02)
  useEffect(() => {
    const ws = new WebSocket(import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/feed');
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'NEW_VIOLATION') {
        setEvents(prev => [message.data, ...prev].slice(0, 20)); // Keep last 20
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, []);

  return (
    <div className="p-section max-w-[1440px] mx-auto flex flex-col md:flex-row gap-12">
      {/* Left Col: Camera Grid */}
      <div className="flex-1">
        <h2 className="text-display-md mb-6">Live Camera Grid</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="store-utility-card flex flex-col">
              <div className="bg-canvas-parchment aspect-video rounded-sm flex items-center justify-center border border-divider-soft relative overflow-hidden">
                <Camera className="w-8 h-8 text-ink-muted-48 opacity-50" />
                <div className="absolute top-2 right-2 bg-black/60 px-2 py-1 rounded text-[10px] text-white tracking-widest font-mono">LIVE</div>
              </div>
              <div className="mt-4 flex justify-between items-center">
                <span className="font-body-strong">CAM-DEMO-SUD-0{i}</span>
                <span className="text-[12px] text-green-600 font-semibold px-2 py-1 bg-green-50 rounded">Active</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Col: Live Violation Feed */}
      <div className="w-full md:w-[400px]">
        <h2 className="text-display-md mb-6 flex items-center space-x-2">
          <AlertCircle className="w-6 h-6 text-red-500" />
          <span>Real-time Feed</span>
        </h2>
        <div className="flex flex-col gap-4">
          {events.length === 0 ? (
            <div className="text-ink-muted-48 text-center p-8 border border-dashed border-hairline rounded-lg">
              Waiting for violations...
            </div>
          ) : (
            events.map(ev => (
              <div key={ev.id} className="store-utility-card p-4 flex flex-col hover:border-primary transition-colors cursor-pointer animate-in fade-in slide-in-from-top-2">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-[12px] font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded">{ev.type.replace('_', ' ')}</span>
                  <span className="text-[12px] text-ink-muted-80">{ev.timestamp}</span>
                </div>
                <div className="text-[17px] font-body-strong">{ev.plate}</div>
                <div className="text-[14px] text-ink-muted-80 mt-1">{ev.camera}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
