import { useState } from 'react';
import { api } from '../api';
import { Save, CheckCircle, ShieldAlert, AlertTriangle, Info, TreePine, Truck, Factory, Scissors, MapPin, Leaf, Lock, ShieldCheck, Globe } from 'lucide-react';

const SPECIES = ['Shihuahuaco', 'Cumala', 'Cedro', 'Tornillo', 'Lupuna', 'Caoba'];

const PUNTOS = {
  Tala:           { punto: 2, actor: 'Titular',      gtfReq: false, icon: TreePine, label: 'Tala de Árbol',       desc: 'Registro de extracción del árbol autorizado.' },
  Trozado:        { punto: 2, actor: 'Titular',      gtfReq: false, icon: Scissors, label: 'Trozado',              desc: 'División del árbol talado en trozas.' },
  Despacho:       { punto: 3, actor: 'Transportista',gtfReq: true,  icon: Truck,    label: 'Despacho / GTF',       desc: 'Movilización hacia el CTP con Guía de Transporte.' },
  Transformacion: { punto: 4, actor: 'Operador_CTP', gtfReq: false, icon: Factory,  label: 'Transformación CTP',   desc: 'Procesamiento en Centro de Transformación Primaria.' },
};

export default function Formulario() {
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState(null);
  const [form, setForm]         = useState({
    tipo_operacion: 'Tala',
    arbol_id:   '',
    troza_id:   '',
    lote_id:    '',
    parcela_corta: '',
    especie:    'Shihuahuaco',
    volumen:    '',
    numero_gtf: '',
    actor_id:   'ACTOR-001',
    fecha:      new Date().toISOString().split('T')[0],
    observacion:'',
  });

  const config = PUNTOS[form.tipo_operacion] || PUNTOS.Tala;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleTipoChange = (tipo) => {
    setForm(prev => ({ ...prev, tipo_operacion: tipo }));
    setResult(null);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const payload = {
        ...form,
        punto_cadena: config.punto,
        tipo_actor:   config.actor,
        volumen:      parseFloat(form.volumen),
        arbol_id:     form.arbol_id   || null,
        troza_id:     form.troza_id   || null,
        lote_id:      form.lote_id    || null,
        numero_gtf:   form.numero_gtf || null,
      };
      const res = await api.registrarOperacion(payload);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const colorMap = { Verde: 'green', Amarillo: 'yellow', Rojo: 'red' };

  return (
    <div className="page-wrapper" style={{ maxWidth: 900 }}>

      {/* ── Header ── */}
      <div className="page-header">
        <h1 className="page-title text-gradient">Registro Operativo</h1>
        <p className="page-description">
          Ingreso de datos en la cadena de custodia forestal (Puntos 2, 3 y 4).
          Cada evento queda firmado con SHA-256 en la bitácora de integridad.
        </p>
      </div>

      {/* ── Selección de tipo ── */}
      <div className="card-flat mb-lg">
        <p className="form-label mb-md">Selecciona el tipo de operación a registrar</p>
        <div className="grid-4">
          {Object.entries(PUNTOS).map(([key, val]) => {
            const IconComponent = val.icon;
            return (
              <button
                key={key}
                type="button"
                className={`btn ${form.tipo_operacion === key ? 'btn-primary' : 'btn-outline'}`}
                style={{ flexDirection: 'column', height: 'auto', padding: '1rem', gap: '0.6rem' }}
                onClick={() => handleTipoChange(key)}
              >
                <IconComponent size={28} />
                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{val.label}</span>
              </button>
            );
          })}
        </div>
        <div className="flex gap-sm mt-md" style={{ alignItems: 'flex-start' }}>
          <Info size={16} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: '1px' }} />
          <p className="text-secondary" style={{ margin: 0, fontSize: '0.85rem' }}>
            <strong>Punto {config.punto}: {config.label}</strong> — {config.desc}
            {config.gtfReq && <span className="text-yellow"> GTF obligatoria en este punto.</span>}
          </p>
        </div>
      </div>

      {/* ── Formulario ── */}
      <form onSubmit={handleSubmit}>
        <div className="grid-2">
          {/* Columna izquierda */}
          <div className="card-flat">
            <h3 style={{ margin: '0 0 1.25rem', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <MapPin size={18} style={{ color: 'var(--accent)' }} /> Identificadores de Trazabilidad
            </h3>

            <div className="form-group">
              <label className="form-label">ID Árbol (Censo Forestal)</label>
              <input className="form-input" type="text" name="arbol_id" value={form.arbol_id}
                onChange={handleChange} placeholder="Ej: 1170" />
            </div>

            <div className="form-group">
              <label className="form-label">ID Troza</label>
              <input className="form-input" type="text" name="troza_id" value={form.troza_id}
                onChange={handleChange} placeholder="Ej: 1170-A" />
            </div>

            <div className="form-group">
              <label className="form-label">ID Lote (activa validación)</label>
              <input className="form-input" type="text" name="lote_id" value={form.lote_id}
                onChange={handleChange} placeholder="Ej: LOT-001" />
            </div>

            {config.gtfReq && (
              <div className="form-group">
                <label className="form-label">
                  Número GTF <span className="text-yellow">* Obligatorio</span>
                </label>
                <input className="form-input" type="text" name="numero_gtf" value={form.numero_gtf}
                  onChange={handleChange} required={config.gtfReq} placeholder="Ej: 017-0001271" />
              </div>
            )}
          </div>

          {/* Columna derecha */}
          <div className="card-flat">
            <h3 style={{ margin: '0 0 1.25rem', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Leaf size={18} style={{ color: 'var(--accent)' }} /> Datos del Material
            </h3>

            <div className="form-group">
              <label className="form-label">Parcela de Corta</label>
              <input className="form-input" type="text" name="parcela_corta" value={form.parcela_corta}
                onChange={handleChange} required placeholder="Ej: PC1" />
            </div>

            <div className="form-group">
              <label className="form-label">Especie</label>
              <select className="form-select" name="especie" value={form.especie} onChange={handleChange} required>
                {SPECIES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Volumen (m³)</label>
              <input className="form-input" type="number" step="0.01" min="0.01" name="volumen"
                value={form.volumen} onChange={handleChange} required placeholder="Ej: 4.20" />
            </div>

            <div className="form-group">
              <label className="form-label">Fecha de Operación</label>
              <input className="form-input" type="date" name="fecha" value={form.fecha}
                onChange={handleChange} required />
            </div>
          </div>
        </div>

        {/* Observaciones y actor */}
        <div className="card-flat mt-md">
          <div className="grid-2">
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">ID del Actor Responsable</label>
              <input className="form-input" type="text" name="actor_id" value={form.actor_id}
                onChange={handleChange} required placeholder="Ej: ACTOR-001" />
              <p className="text-muted mt-sm" style={{ fontSize: '0.78rem' }}>
                Rol asignado automáticamente: <strong>{config.actor.replace('_', ' ')}</strong>
              </p>
            </div>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Observaciones</label>
              <textarea className="form-textarea" name="observacion" value={form.observacion}
                onChange={handleChange} placeholder="Detalles adicionales..." rows="3" />
            </div>
          </div>
        </div>

        <div className="flex-between mt-lg" style={{ flexWrap: 'wrap', gap: '1rem' }}>
          <p className="text-muted" style={{ fontSize: '0.82rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Lock size={14} /> El evento será firmado con SHA-256 en la bitácora de integridad.
          </p>
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ minWidth: 200 }}>
            {loading
              ? <><span className="loading-spinner" /> Validando y registrando...</>
              : <><Save size={17} /> Registrar y Validar</>
            }
          </button>
        </div>
      </form>

      {/* ── Error ── */}
      {error && (
        <div className="card mt-lg" style={{ borderLeft: '4px solid var(--red-text)' }}>
          <div className="flex gap-sm">
            <ShieldAlert size={20} style={{ color: 'var(--red-text)', flexShrink: 0 }} />
            <div>
              <strong style={{ color: 'var(--red-text)' }}>Error al registrar</strong>
              <p className="text-secondary mt-sm" style={{ margin: '0.25rem 0 0', fontSize: '0.88rem' }}>{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Resultado ── */}
      {result && (
        <div className="card mt-lg" style={{ borderLeft: '4px solid var(--green-text)' }}>
          <div className="flex gap-sm mb-md">
            <CheckCircle size={22} style={{ color: 'var(--green-text)', flexShrink: 0 }} />
            <div>
              <strong style={{ color: 'var(--green-text)', fontSize: '1.05rem' }}>{result.mensaje}</strong>
              <p className="text-muted mt-sm" style={{ fontSize: '0.82rem', margin: '0.25rem 0 0' }}>
                Operación: <code className="code-text">{result.operacion_id}</code>
              </p>
            </div>
          </div>

          {/* Hash generado */}
          {result.integridad?.hash_actual && (
            <div style={{ marginBottom: '1rem' }}>
              <p className="form-label mb-sm">Hash SHA-256 del evento</p>
              <div className="hash-chip">
                <Lock size={16} /> <code>{result.integridad.hash_actual}</code>
              </div>
            </div>
          )}

          {/* Resultado del semáforo si validó un lote */}
          {result.validacion && (
            <div>
              <div className="divider" />
              <h4 style={{ margin: '0 0 0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldCheck size={18} /> Resultado del Semáforo de Riesgo
              </h4>
              {(() => {
                const c = colorMap[result.validacion.color_semaforo] || 'gray';
                return (
                  <div className={`semaforo semaforo-${c}`}>
                    {c === 'green'  && <CheckCircle size={22} />}
                    {c === 'yellow' && <AlertTriangle size={22} />}
                    {c === 'red'    && <ShieldAlert size={22} />}
                    <div>
                      <strong>Lote {result.validacion.lote_id}: {result.validacion.color_semaforo}</strong>
                      <p style={{ margin: '0.1rem 0 0', fontSize: '0.85rem', fontWeight: 400 }}>
                        {result.validacion.mensaje}
                      </p>
                    </div>
                  </div>
                );
              })()}

              <div className="mt-md">
                <a href={`/trazabilidad/${result.validacion.lote_id}`} className="btn btn-outline" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Globe size={16} /> Ver Pasaporte Digital de este Lote
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
