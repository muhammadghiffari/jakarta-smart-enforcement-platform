import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Camera, Map, BarChart3, Users, FileText, Settings, ShieldAlert } from 'lucide-react';

import ETLEPage from './pages/ETLEPage';
import DashboardPage from './pages/DashboardPage';

// Placeholders for the main pages
const ViolationMapPage = () => <div className="p-section max-w-[1440px] mx-auto"><h1 className="text-display-lg">Hotspot Map</h1></div>;
const AnalyticsPage = () => <div className="p-section max-w-[1440px] mx-auto"><h1 className="text-display-lg">Analytics</h1></div>;
const OptimizerPage = () => <div className="p-section max-w-[1440px] mx-auto"><h1 className="text-display-lg">MCLP Optimizer</h1></div>;

const GlobalNav = () => (
  <nav className="h-[44px] bg-surface-black text-body-on-dark flex items-center justify-between px-6 sticky top-0 z-50">
    <div className="flex items-center space-x-6">
      <div className="flex items-center space-x-2 font-display font-semibold tracking-tight">
        <ShieldAlert className="w-5 h-5 text-primary-on-dark" />
        <span>JSEP</span>
      </div>
      <div className="hidden md:flex space-x-6 text-[12px] tracking-[-0.12px]">
        <Link to="/" className="hover:text-primary-on-dark transition-colors">Dashboard</Link>
        <Link to="/map" className="hover:text-primary-on-dark transition-colors">Map</Link>
        <Link to="/analytics" className="hover:text-primary-on-dark transition-colors">Analytics</Link>
        <Link to="/optimizer" className="hover:text-primary-on-dark transition-colors">Optimizer</Link>
        <Link to="/etle" className="hover:text-primary-on-dark transition-colors">E-TLE</Link>
      </div>
    </div>
    <div className="flex items-center space-x-4">
      <button className="btn-dark-utility">Admin</button>
    </div>
  </nav>
);

const SubNav = () => (
  <div className="h-[52px] bg-canvas-parchment/80 backdrop-blur-md border-b border-divider-soft flex items-center justify-between px-6 sticky top-[44px] z-40">
    <span className="text-[21px] font-semibold tracking-[0.231px]">Operations Center</span>
    <button className="btn-primary">Generate Report</button>
  </div>
);

function App() {
  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-canvas-parchment">
        <GlobalNav />
        <SubNav />
        <main className="flex-1 bg-canvas">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/map" element={<ViolationMapPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/optimizer" element={<OptimizerPage />} />
            <Route path="/etle" element={<ETLEPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
