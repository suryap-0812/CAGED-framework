import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer style={{
      borderTop: '1px solid var(--border-color)',
      padding: '24px',
      textAlign: 'center',
      fontSize: '0.85rem',
      color: 'var(--text-muted)',
      background: 'var(--bg-secondary)'
    }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          CAGED Framework v0.1.0 — Privacy-Preserving Behavioral Analytics
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <span>Privacy by Design</span>
          <span>•</span>
          <span>Statistical Causal Inference</span>
        </div>
      </div>
    </footer>
  );
};
