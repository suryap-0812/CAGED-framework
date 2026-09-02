import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { HealthPage } from './pages/HealthPage';
import { AnalyticsPage } from './pages/AnalyticsPage';

const ArchitectureDocs: React.FC = () => (
  <div className="glass-card" style={{ padding: '32px' }}>
    <h2>System Architecture Documentation</h2>
    <p style={{ marginTop: '12px', color: 'var(--text-secondary)' }}>
      CAGED architecture specifications are detailed in <code>docs/architecture.md</code>.
    </p>
  </div>
);

const RoadmapDocs: React.FC = () => (
  <div className="glass-card" style={{ padding: '32px' }}>
    <h2>Phase Development Roadmap</h2>
    <p style={{ marginTop: '12px', color: 'var(--text-secondary)' }}>
      CAGED 20-phase roadmap details are stored in <code>docs/development-plan.md</code>.
    </p>
  </div>
);

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="app-container">
        <Header />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<AnalyticsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/health" element={<HealthPage />} />
            <Route path="/docs/architecture" element={<ArchitectureDocs />} />
            <Route path="/docs/roadmap" element={<RoadmapDocs />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
};
