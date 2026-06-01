import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  BarChart3,
  Bell,
  FileCheck2,
  LayoutDashboard,
  Map,
  Menu,
  Route,
  Settings,
  Shield,
  X,
  Zap,
} from 'lucide-react';
import { useState } from 'react';
import { BrowserRouter as Router, NavLink, Route as AppRoute, Routes, useLocation } from 'react-router-dom';

import DashboardPage from './pages/DashboardPage';
import ETLEPage from './pages/ETLEPage';
import { AnalyticsPage, OptimizerPage, ViolationMapPage } from './pages/OperationsPages';
import CRMDispatchPage from './pages/CRMDispatchPage';

const navItems = [
  { to: '/',          label: 'Dashboard', icon: LayoutDashboard },
  { to: '/map',       label: 'Map',       icon: Map },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/optimizer', label: 'Optimizer', icon: Route },
  { to: '/etle',      label: 'E-TLE',    icon: FileCheck2 },
  { to: '/crm-dispatch', label: 'CRM & Dispatch', icon: Shield },
];

const routeMeta: Record<string, {
  title: string;
  action: string;
  icon: typeof Activity;
  links: { label: string; href: string }[];
}> = {
  '/':          { title: 'Operations Center',       action: 'Generate Report',   icon: Activity,   links: [{ label: 'Live Feed', href: '#live' }, { label: 'KPIs', href: '#kpis' }, { label: 'Alerts', href: '#alerts' }] },
  '/map':       { title: 'Violation Intelligence',  action: 'Export Map',        icon: Map,        links: [{ label: 'Heatmap', href: '#heatmap' }, { label: 'Zones', href: '#zones' }, { label: 'Stops', href: '#stops' }] },
  '/analytics': { title: 'Analytics',               action: 'Share Brief',       icon: BarChart3,  links: [{ label: 'Trends', href: '#trends' }, { label: 'Breakdown', href: '#breakdown' }, { label: 'Leaderboard', href: '#leaderboard' }] },
  '/optimizer': { title: 'MCLP Optimizer',          action: 'Run Scenario',      icon: Route,      links: [{ label: 'Config', href: '#config' }, { label: 'Coverage', href: '#coverage' }, { label: 'Results', href: '#results' }] },
  '/etle':      { title: 'E-TLE Review & Inference', action: 'Open Audit Log',    icon: FileCheck2, links: [{ label: 'Queue / Model', href: '#etle-view' }, { label: 'Rules Engine', href: '#rules-section' }, { label: 'Audit Log', href: '#audit-section' }] },
  '/crm-dispatch': { title: 'CRM & Dispatch Routing', action: 'Trigger Complaint', icon: Shield,  links: [{ label: 'Dispatch', href: '#dispatch' }, { label: 'Reports', href: '#reports' }, { label: 'Leaderboard', href: '#leaderboard' }] },
};

// Animated hexagon logo
function LogoBadge() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <path
        d="M14 2L25.26 8.5V21.5L14 28L2.74 21.5V8.5L14 2Z"
        fill="url(#logoGrad)"
      />
      <path
        d="M14 2L25.26 8.5V21.5L14 28L2.74 21.5V8.5L14 2Z"
        stroke="rgba(0,212,255,0.5)"
        strokeWidth="0.5"
        fill="none"
      />
      <Shield x="8" y="8" width="12" height="12" color="#000" strokeWidth="2" />
      <defs>
        <linearGradient id="logoGrad" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#00d4ff" />
          <stop offset="100%" stopColor="#0066aa" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function GlobalNav() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <header className="global-nav">
      {/* Brand */}
      <NavLink to="/" className="brand-mark" onClick={() => setIsOpen(false)}>
        <span className="brand-logo">
          <LogoBadge />
        </span>
        <span className="brand-wordmark">JSEP</span>
        <span style={{ color: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--font-mono)', marginLeft: 2 }}>v2</span>
      </NavLink>

      {/* Desktop nav */}
      <nav className="nav-links" aria-label="Primary navigation">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === '/'} className="nav-link">
            <Icon size={13} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Actions */}
      <div className="nav-actions">
        <button className="icon-button" type="button" aria-label="Notifications" id="nav-notifications">
          <Bell size={14} />
          <span className="notif-badge" aria-hidden="true" />
        </button>
        <button className="icon-button" type="button" aria-label="System status" id="nav-status">
          <Zap size={14} />
        </button>
        <button className="btn-dark-utility" type="button" id="nav-admin">
          <Settings size={13} aria-hidden="true" />
          <span>Admin</span>
        </button>
        <button
          className="icon-button nav-menu-button"
          type="button"
          aria-label="Toggle navigation"
          aria-expanded={isOpen}
          id="nav-mobile-toggle"
          onClick={() => setIsOpen((v) => !v)}
        >
          {isOpen ? <X size={16} /> : <Menu size={16} />}
        </button>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.nav
            className="mobile-menu"
            aria-label="Mobile navigation"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
          >
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className="mobile-link"
                onClick={() => setIsOpen(false)}
              >
                <Icon size={16} aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            ))}
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}

function SubNav() {
  const location = useLocation();
  const meta = routeMeta[location.pathname] ?? routeMeta['/'];
  const PageIcon = meta.icon;

  const handleAction = () => {
    // Dispatch a custom event that each page can listen to for its primary action
    window.dispatchEvent(new CustomEvent('jsep:subnav-action', {
      detail: { route: location.pathname, action: meta.action }
    }));
  };

  return (
    <div className="sub-nav">
      <div className="sub-nav-title">
        <PageIcon size={15} aria-hidden="true" />
        <span>{meta.title}</span>
      </div>
      <div className="sub-nav-links">
        {meta.links.map(({ label, href }) => (
          <a key={label} href={href}>{label}</a>
        ))}
        <button
          className="btn-primary btn-compact"
          type="button"
          id="subnav-action"
          onClick={handleAction}
        >
          <Zap size={13} aria-hidden="true" />
          <span>{meta.action}</span>
        </button>
      </div>
    </div>
  );
}

const pageVariants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3 } },
  exit:    { opacity: 0, y: -8, transition: { duration: 0.18 } },
};

function App() {
  return (
    <Router>
      <div className="app-shell">
        <GlobalNav />
        <SubNav />
        <main className="app-main">
          <AnimatePresence mode="wait">
            <Routes>
              <AppRoute path="/"          element={<motion.div key="dashboard" {...pageVariants}><DashboardPage /></motion.div>} />
              <AppRoute path="/map"       element={<motion.div key="map"       {...pageVariants}><ViolationMapPage /></motion.div>} />
              <AppRoute path="/analytics" element={<motion.div key="analytics" {...pageVariants}><AnalyticsPage /></motion.div>} />
              <AppRoute path="/optimizer" element={<motion.div key="optimizer" {...pageVariants}><OptimizerPage /></motion.div>} />
              <AppRoute path="/etle"      element={<motion.div key="etle"      {...pageVariants}><ETLEPage /></motion.div>} />
              <AppRoute path="/crm-dispatch" element={<motion.div key="crm-dispatch" {...pageVariants}><CRMDispatchPage /></motion.div>} />
            </Routes>
          </AnimatePresence>
        </main>
      </div>
    </Router>
  );
}

export default App;
