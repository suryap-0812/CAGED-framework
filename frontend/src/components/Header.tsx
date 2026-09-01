import React from 'react';
import { ShieldCheck, Activity, Database, FileText } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export const Header: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { label: 'System Health', path: '/', icon: Activity },
    { label: 'Architecture', path: '/docs/architecture', icon: Database },
    { label: 'Roadmap', path: '/docs/roadmap', icon: FileText },
  ];

  return (
    <header style={{
      borderBottom: '1px solid var(--border-color)',
      background: 'rgba(11, 15, 25, 0.8)',
      backdropFilter: 'blur(16px)',
      position: 'sticky',
      top: 0,
      zIndex: 100
    }}>
      <div style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '16px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        {/* Brand Logo */}
        <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            boxShadow: 'var(--shadow-glow)'
          }}>
            <ShieldCheck size={24} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em', color: '#fff' }}>
              CAGED
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Causal Engagement Analytics
            </div>
          </div>
        </Link>

        {/* Navigation */}
        <nav style={{ display: 'flex', gap: '8px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 14px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  textDecoration: 'none',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  background: isActive ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                  border: isActive ? '1px solid var(--border-active)' : '1px solid transparent',
                  transition: 'all 0.2s ease'
                }}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
