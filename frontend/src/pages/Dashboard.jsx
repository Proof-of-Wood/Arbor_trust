import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import {
  ShieldAlert, AlertTriangle, RefreshCw, CheckCircle,
  FileSearch, Clock, TrendingUp, Zap
} from 'lucide-react';

const colorMap = { Rojo: 'red', Amarillo: 'yellow', Verde: 'green' };

const reglaLabel = {
  gtf_asociada:            'GTF Asociada',
  existencia_arbol:        'Existencia del Árbol',
  volumen_disponible:      'Volumen vs. Saldo',
  cronologia_operaciones:  'Cronología de Operaciones',
};

export default function Dashboard() {
  const [alertas, setAlertas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [filter, setFilter]   = useState('all');

  const cargarFallas = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.obtenerFallas();
      setAlertas(data.reportes || []);
      setLastUpdate(new Date());
    } catch (err) {
      console.error("Error cargando alertas:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    cargarFallas();
    const interval = setInterval(cargarFallas, 15000);
    return () => clearInterval(interval);
  }, [cargarFallas]);

  const totalRojos    = alertas.filter(a => a.color_semaforo === 'Rojo').length;
  const totalAmarillos = alertas.filter(a => a.color_semaforo === 'Amarillo').length;
  const totalVerdes   = alertas.filter(a => a.color_semaforo === 'Verde').length;

  const filtered = filter === 'all'
    ? alertas
    : alertas.filter(a => a.color_semaforo === filter);

  return (
    <div className="page-wrapper">

      {/* ── Header ── */}
      <div className="page-header flex-between" style={{ flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="page-title text-gradient">Panel del Fiscalizador</h1>
          <p className="page-description">
            Sistema integrador y verificador de fraude en la cadena de valor maderera.
            Detecta inconsistencias en tiempo real basadas en los Lineamientos OSINFOR.
          </p>
        </div>
        <button className="btn btn-outline" onClick={cargarFallas} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin-icon' : ''} />
          {loading ? 'Actualizando...' : 'Actualizar'}
        </button>
      </div>

      {/* Timestamp */}
      {lastUpdate && (
        <p className="text-muted mb-lg" style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Clock size={13} />
          Última actualización: {lastUpdate.toLocaleTimeString('es-PE')}
          &nbsp;·&nbsp; Auto-refresh cada 15s
        </p>
      )}

      {/* ── Stats ── */}
      <div className="stats-grid">
        <div className="stat-card" style={{ borderTop: '3px solid var(--red-text)' }}>
          <div className="flex-between">
            <span className="stat-label">Fallas Críticas</span>
            <ShieldAlert size={20} style={{ color: 'var(--red-text)' }} />
          </div>
          <div className="stat-number text-red">{totalRojos}</div>
          <p className="text-muted" style={{ fontSize: '0.78rem', margin: 0 }}>Requieren acción inmediata</p>
        </div>

        <div className="stat-card" style={{ borderTop: '3px solid var(--yellow-text)' }}>
          <div className="flex-between">
            <span className="stat-label">Alertas</span>
            <AlertTriangle size={20} style={{ color: 'var(--yellow-text)' }} />
          </div>
          <div className="stat-number text-yellow">{totalAmarillos}</div>
          <p className="text-muted" style={{ fontSize: '0.78rem', margin: 0 }}>Pendientes de revisión</p>
        </div>

        <div className="stat-card" style={{ borderTop: '3px solid var(--green-text)' }}>
          <div className="flex-between">
            <span className="stat-label">Conformes</span>
            <CheckCircle size={20} style={{ color: 'var(--green-text)' }} />
          </div>
          <div className="stat-number text-green">{totalVerdes}</div>
          <p className="text-muted" style={{ fontSize: '0.78rem', margin: 0 }}>Trazabilidad verificada</p>
        </div>

        <div className="stat-card">
          <div className="flex-between">
            <span className="stat-label">Total Registros</span>
            <TrendingUp size={20} style={{ color: 'var(--accent)' }} />
          </div>
          <div className="stat-number text-accent">{alertas.length}</div>
          <p className="text-muted" style={{ fontSize: '0.78rem', margin: 0 }}>Eventos analizados</p>
        </div>
      </div>

      {/* ── Filtros ── */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <span className="text-muted" style={{ fontSize: '0.85rem', alignSelf: 'center' }}>Filtrar:</span>
        {[
          { key: 'all',      label: 'Todos' },
          { key: 'Rojo',     label: 'Fallas Críticas' },
          { key: 'Amarillo', label: 'Alertas' },
          { key: 'Verde',    label: 'Conformes' },
        ].map(f => (
          <button
            key={f.key}
            className={`btn ${filter === f.key ? 'btn-primary' : 'btn-outline'}`}
            style={{ padding: '0.4rem 1rem', fontSize: '0.85rem' }}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* ── Lista de alertas ── */}
      {loading && alertas.length === 0 ? (
        <div className="loading-state">
          <span className="loading-spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
          <p>Consultando el motor de validación...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state card-flat">
          <div className="empty-state-icon" style={{ color: 'var(--text-muted)' }}>
            <CheckCircle size={48} />
          </div>
          <h3 style={{ margin: 0, marginTop: '1rem' }}>
            {filter !== 'all' ? `Sin registros con estado "${filter}"` : 'Sin alertas activas'}
          </h3>
          <p style={{ maxWidth: 380, textAlign: 'center', margin: 0 }}>
            Todos los lotes registrados cumplen las reglas de trazabilidad del D.L. N° 1085.
          </p>
        </div>
      ) : (
        <div className="grid-2" style={{ alignItems: 'start' }}>
          {filtered.map((alerta) => {
            const color = colorMap[alerta.color_semaforo] || 'gray';
            return (
              <div
                key={alerta.validacion_id}
                className="card"
                style={{ borderLeft: `4px solid var(--${color}-text)` }}
              >
                {/* Header de la card */}
                <div className="flex-between mb-md" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
                  <span className={`badge badge-${color}`}>
                    {alerta.color_semaforo === 'Rojo' && <ShieldAlert size={12} />}
                    {alerta.color_semaforo === 'Amarillo' && <AlertTriangle size={12} />}
                    {alerta.color_semaforo === 'Verde' && <CheckCircle size={12} />}
                    {alerta.color_semaforo}
                  </span>
                  <span className="text-muted" style={{ fontSize: '0.78rem' }}>
                    {alerta.fecha_validacion
                      ? new Date(alerta.fecha_validacion).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })
                      : 'Fecha desconocida'
                    }
                  </span>
                </div>

                {/* Identidad */}
                <h3 style={{ margin: '0 0 0.25rem', fontSize: '1.1rem' }}>
                  Lote: <span className="text-accent">{alerta.lote_id}</span>
                </h3>
                <p className="text-muted" style={{ fontSize: '0.8rem', margin: '0 0 1rem' }}>
                  GTF: <strong className="text-secondary">{alerta.numero_gtf || 'No asignada'}</strong>
                  &nbsp;·&nbsp; Titular: <strong className="text-secondary">{alerta.titular || 'Desconocido'}</strong>
                </p>

                {/* Regla infringida */}
                <div style={{ background: 'var(--bg-surface)', padding: '0.85rem', borderRadius: '10px', marginBottom: '1rem' }}>
                  <div className="flex gap-sm mb-sm">
                    <Zap size={15} style={{ color: `var(--${color}-text)`, flexShrink: 0, marginTop: '1px' }} />
                    <span className="form-label" style={{ margin: 0 }}>
                      Regla Infringida: {reglaLabel[alerta.regla] || alerta.regla}
                    </span>
                  </div>
                  <p className="text-secondary" style={{ margin: 0, fontSize: '0.88rem', lineHeight: 1.5 }}>
                    {alerta.mensaje}
                  </p>
                </div>

                {/* Acción */}
                <a
                  href={`/trazabilidad/${alerta.lote_id}`}
                  className="btn btn-outline w-full"
                  style={{ justifyContent: 'center' }}
                >
                  <FileSearch size={16} />
                  Inspeccionar Cadena de Custodia
                </a>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
