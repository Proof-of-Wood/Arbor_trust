import { useState } from 'react';
import { useAuth } from '../App';
import { TreePine, ShieldCheck, User, Building, HardHat } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const [rol, setRol] = useState('Titular');
  const [ruc, setRuc] = useState('20123456789');
  const [serfor, setSerfor] = useState('REG-SER-2026-0001');
  const [dni, setDni] = useState('12345678');
  const [placa, setPlaca] = useState('ABC-123');

  const handleRoleSelect = (selectedRol) => {
    setRol(selectedRol);
    if (selectedRol === 'Titular') {
      setRuc('20123456789');
      setSerfor('');
      setDni('');
      setPlaca('');
    } else if (selectedRol === 'Regente') {
      setRuc('');
      setSerfor('REG-SER-2026-0001');
      setDni('12345678');
      setPlaca('');
    } else if (selectedRol === 'OSINFOR') {
      setRuc('');
      setSerfor('');
      setDni('');
      setPlaca('');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    login({
      rol,
      ruc: rol === 'Titular' ? ruc : '',
      serfor: rol === 'Regente' ? serfor : '',
      dni: rol === 'Regente' ? dni : '',
      placa: rol === 'Transportista' ? placa : '',
    });
  };

  return (
    <div className="login-container" style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '80vh',
      padding: '2rem'
    }}>
      <div className="card" style={{
        maxWidth: '480px',
        width: '100%',
        padding: '2.5rem',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        background: 'var(--bg-surface)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '60px',
            height: '60px',
            borderRadius: '16px',
            background: 'rgba(74, 222, 128, 0.1)',
            color: 'var(--accent)',
            marginBottom: '1rem'
          }}>
            <TreePine size={32} />
          </div>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 'bold', margin: '0 0 0.5rem', color: 'var(--text-primary)' }}>
            ArborTrust
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: 0 }}>
            Plataforma GovTech de Trazabilidad e Interoperabilidad PIDE
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label className="form-label" style={{ marginBottom: '0.75rem', display: 'block' }}>
              Seleccione su Rol de Simulación PIDE
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
              <button
                type="button"
                onClick={() => handleRoleSelect('Titular')}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: rol === 'Titular' ? '2px solid var(--accent)' : '1px solid var(--border)',
                  background: rol === 'Titular' ? 'rgba(74, 222, 128, 0.08)' : 'transparent',
                  color: rol === 'Titular' ? 'var(--accent)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <Building size={20} />
                <span style={{ fontSize: '0.8rem', fontWeight: '500' }}>Titular</span>
              </button>

              <button
                type="button"
                onClick={() => handleRoleSelect('Regente')}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: rol === 'Regente' ? '2px solid var(--accent)' : '1px solid var(--border)',
                  background: rol === 'Regente' ? 'rgba(74, 222, 128, 0.08)' : 'transparent',
                  color: rol === 'Regente' ? 'var(--accent)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <HardHat size={20} />
                <span style={{ fontSize: '0.8rem', fontWeight: '500' }}>Regente</span>
              </button>

              <button
                type="button"
                onClick={() => handleRoleSelect('OSINFOR')}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  borderRadius: '8px',
                  border: rol === 'OSINFOR' ? '2px solid var(--accent)' : '1px solid var(--border)',
                  background: rol === 'OSINFOR' ? 'rgba(74, 222, 128, 0.08)' : 'transparent',
                  color: rol === 'OSINFOR' ? 'var(--accent)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <ShieldCheck size={20} />
                <span style={{ fontSize: '0.8rem', fontWeight: '500' }}>OSINFOR</span>
              </button>
            </div>
          </div>

          {rol === 'Titular' && (
            <div className="form-group">
              <label className="form-label" htmlFor="ruc">RUC del Titular</label>
              <input
                id="ruc"
                type="text"
                className="form-input"
                value={ruc}
                onChange={(e) => setRuc(e.target.value)}
                placeholder="Ej. 20123456789"
                required
              />
            </div>
          )}

          {rol === 'Regente' && (
            <>
              <div className="form-group">
                <label className="form-label" htmlFor="serfor">Registro SERFOR</label>
                <input
                  id="serfor"
                  type="text"
                  className="form-input"
                  value={serfor}
                  onChange={(e) => setSerfor(e.target.value)}
                  placeholder="Ej. REG-SER-2026-0001"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="dni">DNI de Identidad</label>
                <input
                  id="dni"
                  type="text"
                  className="form-input"
                  value={dni}
                  onChange={(e) => setDni(e.target.value)}
                  placeholder="Ej. 12345678"
                  required
                />
              </div>
            </>
          )}

          {rol === 'OSINFOR' && (
            <div style={{
              background: 'rgba(74, 222, 128, 0.05)',
              border: '1px solid rgba(74, 222, 128, 0.2)',
              borderRadius: '8px',
              padding: '1rem',
              fontSize: '0.85rem',
              color: 'var(--text-secondary)'
            }}>
              <p style={{ margin: 0, lineHeight: '1.4' }}>
                <strong>Acceso Administrativo Global:</strong> Como supervisor de OSINFOR tendrá visibilidad total para control en ruta, trazabilidad ex-post y penalización en cascada.
              </p>
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            style={{
              width: '100%',
              padding: '0.85rem',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              marginTop: '0.5rem'
            }}
          >
            <User size={18} /> Iniciar Sesión en ArborTrust
          </button>
        </form>
      </div>
    </div>
  );
}
