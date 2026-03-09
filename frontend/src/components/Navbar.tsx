import React from 'react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/history', label: 'History' },
  { to: '/statistics', label: 'Statistics' },
  { to: '/prediction', label: 'Prediction' },
  { to: '/collection', label: 'Collection' },
];

const Navbar: React.FC = () => {
  return (
    <nav
      style={{
        background: '#1e293b',
        borderBottom: '1px solid #334155',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        height: 60,
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      <div
        style={{
          fontWeight: 700,
          fontSize: 20,
          color: '#6366f1',
          marginRight: 40,
        }}
      >
        Lotto AI
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            style={({ isActive }) => ({
              padding: '8px 16px',
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 500,
              background: isActive ? '#6366f1' : 'transparent',
              color: isActive ? '#fff' : '#94a3b8',
              transition: 'all 0.2s',
            })}
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
};

export default Navbar;
