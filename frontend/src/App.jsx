import { createContext, useContext, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Sun, Moon, TreePine, ClipboardEdit, Globe, ShieldCheck, LogOut } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Timeline from './pages/Timeline';
import Formulario from './pages/Formulario';
import Login from './pages/Login';
import './index.css';

// ── Theme Context ──────────────────────────────────────────
const ThemeContext = createContext(null);
export const useTheme = () => useContext(ThemeContext);

// ── Auth Context ───────────────────────────────────────────
const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function HomeRedirect() {
  const { auth } = useAuth();
  if (!auth) {
    return <Navigate to="/login" replace />;
  }
  if (auth.rol === 'Regente' || auth.rol === 'ARFFS') {
    return <Navigate to="/panel-regente" replace />;
  }
  if (auth.rol === 'Titular' || auth.rol === 'Operador_CTP') {
    return <Navigate to="/panel-titular" replace />;
  }
  if (auth.rol === 'OSINFOR') {
    return <Navigate to="/dashboard-fiscalizador" replace />;
  }
  return <Navigate to="/login" replace />;
}

function ProtectedRoute({ children, allowedRoles }) {
  const { auth } = useAuth();
  if (!auth) {
    return <Navigate to="/login" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(auth.rol)) {
    if (auth.rol === 'Regente' || auth.rol === 'ARFFS') {
      return <Navigate to="/panel-regente" replace />;
    }
    if (auth.rol === 'Titular' || auth.rol === 'Operador_CTP') {
      return <Navigate to="/panel-titular" replace />;
    }
    if (auth.rol === 'OSINFOR') {
      return <Navigate to="/dashboard-fiscalizador" replace />;
    }
    return <Navigate to="/login" replace />;
  }
  return children;
}

// ── App Root ───────────────────────────────────────────────
function App() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('arbortrust-theme') || 'dark';
  });

  const [auth, setAuth] = useState(() => {
    const rol = localStorage.getItem('pide_rol');
    if (!rol) return null;
    return {
      rol,
      ruc: localStorage.getItem('pide_ruc') || '',
      serfor: localStorage.getItem('pide_serfor') || '',
      dni: localStorage.getItem('pide_dni') || '',
      placa: localStorage.getItem('pide_placa') || '',
    };
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('arbortrust-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  const login = (userData) => {
    localStorage.setItem('pide_rol', userData.rol || '');
    localStorage.setItem('pide_ruc', userData.ruc || '');
    localStorage.setItem('pide_serfor', userData.serfor || '');
    localStorage.setItem('pide_dni', userData.dni || '');
    localStorage.setItem('pide_placa', userData.placa || '');
    setAuth(userData);
  };

  const logout = () => {
    localStorage.removeItem('pide_rol');
    localStorage.removeItem('pide_ruc');
    localStorage.removeItem('pide_serfor');
    localStorage.removeItem('pide_dni');
    localStorage.removeItem('pide_placa');
    setAuth(null);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      <AuthContext.Provider value={{ auth, login, logout }}>
        <Router>
          <Navbar theme={theme} toggleTheme={toggleTheme} />
          <main style={{ flexGrow: 1 }}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={<HomeRedirect />} />
              <Route 
                path="/panel-regente" 
                element={
                  <ProtectedRoute allowedRoles={['Regente', 'ARFFS']}>
                    <Formulario />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/panel-titular" 
                element={
                  <ProtectedRoute allowedRoles={['Titular', 'Operador_CTP']}>
                    <Formulario />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/dashboard-fiscalizador" 
                element={
                  <ProtectedRoute allowedRoles={['OSINFOR']}>
                    <Dashboard />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/trazabilidad" 
                element={
                  <ProtectedRoute allowedRoles={['Titular', 'OSINFOR', 'Transportista']}>
                    <Timeline />
                  </ProtectedRoute>
                } 
              />
              <Route 
                path="/trazabilidad/:id" 
                element={
                  <ProtectedRoute allowedRoles={['Titular', 'OSINFOR', 'Transportista']}>
                    <Timeline />
                  </ProtectedRoute>
                } 
              />
            </Routes>
          </main>
          <footer className="footer">
            <p style={{ margin: 0 }}>
              ArborTrust · Pasaporte Digital Forestal · Hackatón TransformaGob 2026 · OSINFOR
            </p>
          </footer>
        </Router>
      </AuthContext.Provider>
    </ThemeContext.Provider>
  );
}

// ── Navbar Component ───────────────────────────────────────
function Navbar({ theme, toggleTheme }) {
  const { auth, logout } = useAuth();

  return (
    <nav className="navbar">
      {/* Brand */}
      <div className="navbar-brand">
        <img src="/osinfor_logo.png" alt="OSINFOR" className="navbar-logo-large" />
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
        {auth ? (
          <>
            {/* Regente Links */}
            {(auth.rol === 'Regente' || auth.rol === 'ARFFS') && (
              <NavLink to="/panel-regente" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ClipboardEdit size={16} /> Carga de Planes
                </div>
              </NavLink>
            )}

            {/* Titular Links */}
            {(auth.rol === 'Titular' || auth.rol === 'Operador_CTP') && (
              <>
                <NavLink to="/panel-titular" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <ClipboardEdit size={16} /> Registro Operativo
                  </div>
                </NavLink>
                <NavLink to="/trazabilidad" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Globe size={16} /> Pasaporte Digital
                  </div>
                </NavLink>
              </>
            )}

            {/* OSINFOR Links */}
            {auth.rol === 'OSINFOR' && (
              <>
                <NavLink to="/dashboard-fiscalizador" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <ShieldCheck size={16} /> Control en Ruta
                  </div>
                </NavLink>
                <NavLink to="/trazabilidad" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Globe size={16} /> Pasaporte Digital
                  </div>
                </NavLink>
              </>
            )}

            {/* Active Profile Info */}
            <div style={{
              fontSize: '0.8rem',
              padding: '0.25rem 0.75rem',
              borderRadius: '20px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem'
            }}>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)' }}></span>
              <span>
                {auth.rol === 'Titular' ? `Titular: ${auth.ruc}` : (auth.rol === 'Regente' ? `Regente: ${auth.serfor}` : 'OSINFOR')}
              </span>
            </div>

            {/* Logout */}
            <button className="nav-link" onClick={logout} style={{ background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <LogOut size={16} /> Salir
            </button>
          </>
        ) : (
          <NavLink to="/login" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            Ingresar
          </NavLink>
        )}

        {/* Theme Toggle */}
        <button className="theme-toggle" onClick={toggleTheme} title={`Cambiar a modo ${theme === 'dark' ? 'claro' : 'oscuro'}`}>
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </nav>
  );
}

export default App;
