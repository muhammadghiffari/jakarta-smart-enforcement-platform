export type DemoCamera = {
  id: string;
  name: string;
  corridor: string;
  status: 'Online' | 'Review' | 'Offline';
  fps: number;
  detections: number;
  confidence: number;
};

export type FeedEvent = {
  id: string;
  type: string;
  plate: string;
  camera: string;
  timestamp: string;
  confidence: number;
};

export type Hotspot = {
  id: string;
  corridor: string;
  risk: number;
  count: number;
  top: string;
  left: string;
};

export type Deployment = {
  id: string;
  corridor: string;
  h3_index: string;
  priority: 'HIGH' | 'MEDIUM';
  eta: string;
  coverage: number;
  reasoning: string;
};

export const demoCameras: DemoCamera[] = [
  {
    id: 'CAM-SUD-01',
    name: 'Sudirman North Gate',
    corridor: 'Jl. Jend. Sudirman',
    status: 'Online',
    fps: 29,
    detections: 142,
    confidence: 0.94,
  },
  {
    id: 'CAM-THR-04',
    name: 'Thamrin Bus Lane',
    corridor: 'Bundaran HI',
    status: 'Online',
    fps: 30,
    detections: 118,
    confidence: 0.91,
  },
  {
    id: 'CAM-KUN-02',
    name: 'Kuningan Priority Lane',
    corridor: 'Rasuna Said',
    status: 'Review',
    fps: 24,
    detections: 76,
    confidence: 0.82,
  },
  {
    id: 'CAM-GAT-07',
    name: 'Gatot Subroto Ramp',
    corridor: 'Semanggi',
    status: 'Online',
    fps: 28,
    detections: 96,
    confidence: 0.88,
  },
];

export const demoFeedEvents: FeedEvent[] = [
  {
    id: 'EVT-4318',
    type: 'BUS_LANE_VIOLATION',
    plate: 'B 1842 KJS',
    camera: 'CAM-THR-04',
    timestamp: '09:42:18',
    confidence: 0.93,
  },
  {
    id: 'EVT-4317',
    type: 'ILLEGAL_PARKING',
    plate: 'B 2291 RFD',
    camera: 'CAM-SUD-01',
    timestamp: '09:39:04',
    confidence: 0.86,
  },
  {
    id: 'EVT-4316',
    type: 'ODD_EVEN_RESTRICTION',
    plate: 'B 7730 TQ',
    camera: 'CAM-GAT-07',
    timestamp: '09:35:51',
    confidence: 0.79,
  },
  {
    id: 'EVT-4315',
    type: 'DESIGNATED_STOP_VIOLATION',
    plate: 'B 6112 PXA',
    camera: 'CAM-KUN-02',
    timestamp: '09:31:23',
    confidence: 0.74,
  },
];

export const demoHotspots: Hotspot[] = [
  { id: 'HS-01', corridor: 'Bundaran HI', risk: 92, count: 41, top: '31%', left: '48%' },
  { id: 'HS-02', corridor: 'Sudirman', risk: 84, count: 33, top: '52%', left: '42%' },
  { id: 'HS-03', corridor: 'Kuningan', risk: 76, count: 27, top: '46%', left: '63%' },
  { id: 'HS-04', corridor: 'Semanggi', risk: 68, count: 22, top: '65%', left: '53%' },
  { id: 'HS-05', corridor: 'Monas', risk: 54, count: 14, top: '20%', left: '39%' },
];

export const demoDeployments: Deployment[] = [
  {
    id: 'DEP-01',
    corridor: 'Bundaran HI',
    h3_index: '8a2e69c2b59ffff',
    priority: 'HIGH',
    eta: '12 min',
    coverage: 92,
    reasoning: 'Highest weighted risk across bus-lane and stopping violations.',
  },
  {
    id: 'DEP-02',
    corridor: 'Sudirman Southbound',
    h3_index: '8a2e69c2b587fff',
    priority: 'HIGH',
    eta: '18 min',
    coverage: 86,
    reasoning: 'Dense repeated detections with strong camera confidence.',
  },
  {
    id: 'DEP-03',
    corridor: 'Rasuna Said',
    h3_index: '8a2e69c288b7fff',
    priority: 'MEDIUM',
    eta: '21 min',
    coverage: 74,
    reasoning: 'Good marginal coverage for illegal parking review.',
  },
  {
    id: 'DEP-04',
    corridor: 'Semanggi Ramp',
    h3_index: '8a2e69c2a997fff',
    priority: 'MEDIUM',
    eta: '27 min',
    coverage: 69,
    reasoning: 'Covers a secondary cluster without duplicating patrol radius.',
  },
];

export const hourlyViolations = [
  { label: '06', value: 18 },
  { label: '07', value: 42 },
  { label: '08', value: 73 },
  { label: '09', value: 88 },
  { label: '10', value: 61 },
  { label: '11', value: 39 },
  { label: '12', value: 45 },
  { label: '13', value: 58 },
  { label: '14', value: 64 },
  { label: '15', value: 71 },
  { label: '16', value: 96 },
  { label: '17', value: 104 },
];

export const violationMix = [
  { label: 'Bus lane', value: 41 },
  { label: 'Stopping', value: 27 },
  { label: 'Odd-even', value: 19 },
  { label: 'Parking', value: 13 },
];

export const formatViolationType = (value: string) =>
  value
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
