import { createContext, useContext, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { Sun, Moon, TreePine, ClipboardEdit, Globe, ShieldCheck } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Timeline from './pages/Timeline';
import Formulario from './pages/Formulario';
import './index.css';

// ── Theme Context ──────────────────────────────────────────
const ThemeContext = createContext(null);
export const useTheme = () => useContext(ThemeContext);

// ── App Root ───────────────────────────────────────────────
function App() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('arbortrust-theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('arbortrust-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      <Router>
        <Navbar theme={theme} toggleTheme={toggleTheme} />
        <main style={{ flexGrow: 1 }}>
          <Routes>
            <Route path="/"                 element={<Formulario />} />
            <Route path="/trazabilidad"     element={<Timeline />} />
            <Route path="/trazabilidad/:id" element={<Timeline />} />
            <Route path="/fiscalizador"     element={<Dashboard />} />
          </Routes>
        </main>
        <footer className="footer">
          <p style={{ margin: 0 }}>
            ArborTrust · Pasaporte Digital Forestal · Hackatón TransformaGob 2026 · OSINFOR
          </p>
        </footer>
      </Router>
    </ThemeContext.Provider>
  );
}

// ── Navbar Component ───────────────────────────────────────
function Navbar({ theme, toggleTheme }) {
  return (
    <nav className="navbar">
      {/* Brand */}
      <div className="navbar-brand">
        <img src="/osinfor_logo.png" alt="OSINFOR - Organismo de Supervisión de los Recursos Forestales y de Fauna Silvestre" className="navbar-logo-large" />
        <div className="navbar-divider" />
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <div className="navbar-title-main" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '1.2rem', fontWeight: 'bold' }}>
            <TreePine size={20} style={{ color: 'var(--accent)' }} />
            ArborTrust
          </div>
          <div className="navbar-subtitle-main" style={{ fontSize: '0.85rem', opacity: 0.8 }}>Pasaporte Digital Forestal</div>
        </div>
      </div>

      {/* Links */}
      <div className="nav-links">
        <NavLink to="/"             className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ClipboardEdit size={16} /> Registro Operativo
          </div>
        </NavLink>
        <NavLink to="/trazabilidad" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Globe size={16} /> Pasaporte Digital
          </div>
        </NavLink>
        <NavLink to="/fiscalizador" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldCheck size={16} /> Control en Ruta
          </div>
        </NavLink>

        {/* Theme Toggle */}
        <button className="theme-toggle" onClick={toggleTheme} title={`Cambiar a modo ${theme === 'dark' ? 'claro' : 'oscuro'}`}>
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </nav>
  );
}

export default App;
