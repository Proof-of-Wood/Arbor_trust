import { useState, useEffect, useCallback } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import {
  Search, TreePine, Truck, Factory, CheckCircle,
  AlertTriangle, ShieldAlert, Fingerprint, ChevronDown,
  ChevronUp, Activity, ClipboardList, Scissors, Package, Settings, FileText, XCircle, FolderSearch, ArrowLeft
} from 'lucide-react';

/* ── Helpers ─────────────────────────────────────────────── */
const puntoInfo = {
  2: { label: 'Aprovechamiento', icon: <TreePine size={20} />, color: 'green' },
  3: { label: 'Transporte Primario', icon: <Truck size={20} />, color: 'yellow' },
  4: { label: 'Transformación CTP', icon: <Factory size={20} />, color: 'green' },
  1: { label: 'Planificación', icon: <ClipboardList size={20} />, color: 'gray' },
};

const tipoIcon = {
  Tala:           { icon: <TreePine size={18} />, label: 'Tala' },
  Trozado:        { icon: <Scissors size={18} />, label: 'Trozado' },
  Despacho:       { icon: <Package size={18} />, label: 'Despacho' },
  Transformacion: { icon: <Settings size={18} />, label: 'Transformación' },
  Registro_Lote:  { icon: <FileText size={18} />, label: 'Registro de Lote' },
};

const actorRoles = {
  Titular:      'Titular del Título Habilitante',
  Regente:      'Regente Forestal',
  Transportista:'Transportista',
  Operador_CTP: 'Operador CTP',
  ARFFS:        'ARFFS (Autoridad Regional)',
  SERFOR:       'SERFOR',
  OSINFOR:      'OSINFOR (Supervisión)',
  Sistema:      'Sistema ArborTrust',
};

const colorMap = {
  Verde:   'green',
  Amarillo: 'yellow',
  Rojo:    'red',
};

export default function Timeline() {
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();

  const queryTituloId = searchParams.get('titulo_id') || '';
  const queryLoteId = searchParams.get('lote_id') || '';

  const [loteId, setLoteId]   = useState(id || queryLoteId || '');
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [expandedIdx, setExpandedIdx] = useState(null);

  // Estados para el Censo Forestal del Título
  const [arboles, setArboles] = useState([]);
  const [loadingArboles, setLoadingArboles] = useState(false);
  const [errorArboles, setErrorArboles] = useState(null);
  const [titulosDisponibles, setTitulosDisponibles] = useState([]);

  // Cargar lista de títulos para el selector
  useEffect(() => {
    const fetchAllTitulos = async () => {
      try {
        const data = await api.obtenerTitulos();
        setTitulosDisponibles(data || []);
      } catch (err) {
        console.error("Error fetching titles in timeline:", err);
      }
    };
    fetchAllTitulos();
  }, []);

  const buscarLote = useCallback(async (targetId) => {
    const query = targetId || loteId;
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setData(null);
    try {
      let resolvedId = query.trim();
      try {
        const searchResult = await api.buscarLote(query.trim());
        if (searchResult && searchResult.lote_id) {
          resolvedId = searchResult.lote_id;
        }
      } catch (searchErr) {
        // Fallback: si falla la búsqueda semántica, intentamos cargar directo con la query ingresada
      }
      const res = await api.obtenerTimeline(resolvedId);
      setData(res);
      setSearchParams({ lote_id: resolvedId });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [loteId, setSearchParams]);

  // Cargar censo forestal si hay titulo_id
  const cargarCenso = useCallback(async (tituloId) => {
    if (!tituloId) return;
    setLoadingArboles(true);
    setErrorArboles(null);
    try {
      const res = await api.obtenerArbolesTitulo(tituloId);
      setArboles(res || []);
    } catch (err) {
      setErrorArboles(err.message || "Error al obtener árboles del título.");
    } finally {
      setLoadingArboles(false);
    }
  }, []);

  useEffect(() => {
    if (queryTituloId) {
      cargarCenso(queryTituloId);
    }
  }, [queryTituloId, cargarCenso]);

  useEffect(() => {
    if (id) {
      buscarLote(id);
    } else if (queryLoteId) {
      buscarLote(queryLoteId);
    }
  }, [id, queryLoteId, buscarLote]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (loteId.trim()) {
      setSearchParams({ lote_id: loteId.trim() });
    }
  };

  const handleTituloFilterChange = (e) => {
    const val = e.target.value;
    if (val) {
      setSearchParams({ titulo_id: val });
      setData(null);
      setError(null);
    } else {
      setSearchParams({});
    }
  };

  const clearFilters = () => {
    setSearchParams({});
    setLoteId('');
    setData(null);
    setError(null);
    setArboles([]);
  };

  const colorClass = data ? colorMap[data.color_semaforo] || 'gray' : 'gray';

  // Cálculos del desglose de árboles
  const totalArboles = arboles.length;
  const totalTalados = arboles.filter(a => a.talado).length;
  const totalEnPie   = totalArboles - totalTalados;
  const volumenTotal = arboles.reduce((acc, a) => acc + (a.volumen_autorizado || 0), 0);

  return (
    <div className="page-wrapper" style={{ maxWidth: 860 }}>
      {/* ── Header ── */}
      <div className="page-header">
        <h1 className="page-title text-gradient">Pasaporte Digital Forestal</h1>
        <p className="page-description">
          Verificador de trazabilidad legal de la madera. Consulta el flujo completo:
          árbol autorizado → aprovechamiento → transporte → transformación primaria.
        </p>
      </div>

      {/* ── Selectores y Filtros en Barra Superior ── */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap', alignItems: 'end' }}>
        <div style={{ flex: 1, minWidth: '240px' }}>
          <label className="form-label" style={{ fontSize: '0.78rem', marginBottom: '0.25rem' }}>
            Consultar por Título Habilitante (Censo)
          </label>
          <select 
            className="form-select" 
            style={{ width: '100%', padding: '0.45rem', fontSize: '0.85rem' }}
            value={queryTituloId}
            onChange={handleTituloFilterChange}
          >
            <option value="">-- Seleccionar Título Habilitante --</option>
            {titulosDisponibles.map(t => (
              <option key={t.id_titulo} value={t.id_titulo}>
                {t.id_titulo} - {t.nombre_concesion}
              </option>
            ))}
          </select>
        </div>

        {queryTituloId && (
          <button 
            type="button" 
            className="btn btn-outline" 
            onClick={clearFilters}
            style={{ height: '36px', fontSize: '0.82rem' }}
          >
            <ArrowLeft size={14} /> Volver a Consulta de Lotes
          </button>
        )}
      </div>

      {/* Vista de Censo Forestal de Título */}
      {queryTituloId ? (
        <>
          <div className="card-flat mb-lg" style={{ borderLeft: '4px solid var(--green-text)' }}>
            <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.4rem' }}>
              Censo Forestal: <span className="text-gradient">{queryTituloId}</span>
            </h2>
            <p className="text-secondary" style={{ margin: 0, fontSize: '0.88rem' }}>
              Seguimiento del inventario de árboles autorizados y estado de aprovechamiento ex-ante y ex-post.
            </p>
          </div>

          {loadingArboles ? (
            <div className="loading-state">
              <span className="loading-spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
              <p>Cargando censo forestal y estado de árboles...</p>
            </div>
          ) : errorArboles ? (
            <div className="card" style={{ borderLeft: '4px solid var(--red-text)' }}>
              <p style={{ margin: 0, color: 'var(--red-text)' }}>{errorArboles}</p>
            </div>
          ) : totalArboles === 0 ? (
            <div className="empty-state card-flat">
              <div className="empty-state-icon" style={{ color: 'var(--text-muted)' }}>
                <TreePine size={48} />
              </div>
              <h3 style={{ margin: 0, marginTop: '1rem' }}>Sin Datos del Censo</h3>
              <p style={{ maxWidth: 380, textAlign: 'center', margin: 0 }}>
                Este título habilitante no tiene un Plan de Aprovechamiento cargado o aprobado en el sistema.
              </p>
            </div>
          ) : (
            <>
              {/* Stats del Censo */}
              <div className="stats-grid" style={{ marginBottom: '2rem' }}>
                <div className="stat-card" style={{ borderTop: '3px solid var(--accent)' }}>
                  <div className="flex-between">
                    <span className="stat-label">Total Árboles</span>
                    <TreePine size={20} className="text-accent" />
                  </div>
                  <div className="stat-number text-accent">{totalArboles}</div>
                  <p className="text-muted" style={{ fontSize: '0.78rem', margin: 0 }}>Inventario censado</p>
                </div>

                <div className="stat-card" style={{ borderTop: '3px solid var(--orange-text)' }}>
                  <div className="flex-between">
                    <span className="stat-label">Aprovechados</span>
                    <Scissors size={20} style={{ color: 'var(--orange-text)' }} />
                  </div>
                  <div className="stat-number text-orange">{totalTalados}</div>
                  <p className="text-muted" style={{ fontSize: '0.78rem', margin: 0 }}>Árboles talados</p>
                </div>

                <div className="stat-card" style={{ borderTop: '3px solid var(--green-text)' }}>
                  <div className="flex-between">
                    <span className="stat-label">En Pie (Standing)</span>
                    <CheckCircle size={20} style={{ color: 'var(--green-text)' }} />
                  </div>
                  <div className="stat-number text-green">{totalEnPie}</div>
                  <p className="text-muted" style={{ fontSize: '0.78rem', margin: 0 }}>Listos para aprovechamiento</p>
                </div>

                <div className="stat-card">
                  <div className="flex-between">
                    <span className="stat-label">Volumen Total</span>
                    <Activity size={20} style={{ color: 'var(--secondary)' }} />
                  </div>
                  <div className="stat-number text-secondary">{volumenTotal.toFixed(2)} m³</div>
                  <p className="text-muted" style={{ fontSize: '0.78rem', margin: 0 }}>Volumen autorizado</p>
                </div>
              </div>

              {/* Listado de Árboles */}
              <div className="card">
                <h3 style={{ margin: '0 0 1.25rem', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ClipboardList size={18} style={{ color: 'var(--accent)' }} /> Desglose Detallado del Censo Forestal
                </h3>
                
                <div style={{ overflowX: 'auto' }}>
                  <table className="table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.88rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--border)', textAlign: 'left' }}>
                        <th style={{ padding: '0.75rem 0.5rem' }}>ID del Árbol</th>
                        <th style={{ padding: '0.75rem 0.5rem' }}>Especie</th>
                        <th style={{ padding: '0.75rem 0.5rem' }}>Volumen Autorizado</th>
                        <th style={{ padding: '0.75rem 0.5rem' }}>Estado en Censo</th>
                        <th style={{ padding: '0.75rem 0.5rem', textAlign: 'center' }}>Estado Físico</th>
                      </tr>
                    </thead>
                    <tbody>
                      {arboles.map((arbol) => (
                        <tr key={arbol.id_arbol} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>{arbol.id_arbol}</td>
                          <td style={{ padding: '0.75rem 0.5rem' }}>{arbol.id_especie}</td>
                          <td style={{ padding: '0.75rem 0.5rem' }}>{arbol.volumen_autorizado.toFixed(2)} m³</td>
                          <td style={{ padding: '0.75rem 0.5rem' }}>
                            <span style={{ fontSize: '0.75rem', opacity: 0.85 }}>{arbol.censo_estado}</span>
                          </td>
                          <td style={{ padding: '0.75rem 0.5rem', textAlign: 'center' }}>
                            {arbol.talado ? (
                              <span 
                                style={{ 
                                  background: 'rgba(251, 146, 60, 0.15)', 
                                  color: '#fb923c', 
                                  padding: '0.15rem 0.5rem', 
                                  borderRadius: '20px', 
                                  fontSize: '0.72rem', 
                                  fontWeight: 600,
                                  display: 'inline-block' 
                                }}
                              >
                                Aprovechado
                              </span>
                            ) : (
                              <span 
                                style={{ 
                                  background: 'rgba(74, 222, 128, 0.15)', 
                                  color: '#4ade80', 
                                  padding: '0.15rem 0.5rem', 
                                  borderRadius: '20px', 
                                  fontSize: '0.72rem', 
                                  fontWeight: 600,
                                  display: 'inline-block' 
                                }}
                              >
                                En Pie
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </>
      ) : (
        <>
          {/* ── Búsqueda de Lote ── */}
          <div className="search-panel">
            <div className="search-panel-main">
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Código de Lote / GTF / Placa Vehicular</label>
                <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.75rem' }}>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Ej: LOT-001, placa (ABC-123) o GTF (GTF-001)"
                    value={loteId}
                    onChange={e => setLoteId(e.target.value)}
                    style={{ flex: 1 }}
                  />
                  <button type="submit" className="btn btn-primary" style={{ flexShrink: 0 }} disabled={loading}>
                    {loading
                      ? <><span className="loading-spinner" /> Verificando...</>
                      : <><Search size={17} /> Verificar Origen</>
                    }
                  </button>
                </form>
              </div>
            </div>
          </div>

          {/* ── Atajos rápidos ── */}
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
            <span className="text-muted" style={{ fontSize: '0.82rem', alignSelf: 'center' }}>Cargar ejemplo:</span>
            {['LOT-001', 'LOT-002'].map(id => (
              <button
                key={id}
                className="btn btn-outline"
                style={{ padding: '0.3rem 0.75rem', fontSize: '0.82rem' }}
                onClick={() => { setLoteId(id); setSearchParams({ lote_id: id }); }}
              >
                {id}
              </button>
            ))}
          </div>

          {/* ── Error ── */}
          {error && (
            <div className="card" style={{ borderLeft: '4px solid var(--red-text)', marginBottom: '2rem' }}>
              <div className="flex gap-sm">
                <ShieldAlert size={20} style={{ color: 'var(--red-text)', flexShrink: 0 }} />
                <div>
                  <strong style={{ color: 'var(--red-text)' }}>Lote no encontrado</strong>
                  <p style={{ margin: '0.25rem 0 0', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* ── Resultado del Lote ── */}
          {data && (
            <>
              {/* Encabezado del Pasaporte */}
              <div className="card-flat mb-lg" style={{ borderTop: `3px solid var(--${colorClass}-text)` }}>
                <div className="flex-between" style={{ flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
                  <div>
                    <p className="text-muted" style={{ fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 0.25rem' }}>
                      Pasaporte Digital — ID Verificado
                    </p>
                    <h2 style={{ margin: 0, fontSize: '1.9rem', fontWeight: 800 }}>{data.lote_id}</h2>
                  </div>
                  <div className={`semaforo semaforo-${colorClass}`}>
                    {colorClass === 'green' && <CheckCircle size={22} />}
                    {colorClass === 'yellow' && <AlertTriangle size={22} />}
                    {colorClass === 'red' && <ShieldAlert size={22} />}
                    <span>
                      {data.color_semaforo === 'Verde' ? 'ORIGEN LEGAL VERIFICADO' :
                       data.color_semaforo === 'Amarillo' ? 'ALERTA — REVISAR' :
                       'FALLA CRÍTICA — POSIBLE FRAUDE'}
                    </span>
                  </div>
                </div>

                <p style={{ margin: '0 0 1.25rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  {data.mensaje}
                </p>

                {/* Hash de integridad */}
                {data.hash_ultimo_evento && (
                  <div>
                    <p className="form-label mb-sm">Hash de Integridad SHA-256 (Cadena de Custodia)</p>
                    <div className="hash-chip">
                      <Fingerprint size={18} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                      <code>{data.hash_ultimo_evento}</code>
                    </div>
                  </div>
                )}
              </div>

              {/* ── Línea de tiempo vertical ── */}
              <div style={{ marginBottom: '1.5rem' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  <Activity size={20} style={{ color: 'var(--accent)' }} />
                  Línea de Tiempo de la Cadena
                </h3>
                <p className="text-secondary" style={{ margin: '0 0 1.5rem', fontSize: '0.88rem' }}>
                  Flujo cronológico verificado del material desde el bosque hasta el destino final.
                </p>
              </div>

              <div className="timeline-wrapper">
                {data.timeline.length === 0 && (
                  <div className="empty-state">
                    <div className="empty-state-icon" style={{ color: 'var(--text-muted)' }}>
                      <FolderSearch size={48} />
                    </div>
                    <p>No hay eventos registrados para este lote.</p>
                  </div>
                )}

                {data.timeline.map((nodo, idx) => {
                  const punto   = puntoInfo[nodo.punto] || puntoInfo[1];
                  const tipo    = tipoIcon[nodo.tipo]   || { icon: '📌', label: nodo.tipo };
                  const isExpanded = expandedIdx === idx;
                  let dotColor  = (nodo.punto === 3 && data.color_semaforo === 'Rojo') ? 'red'
                                : (nodo.punto === 3) ? 'yellow' : punto.color;
                  let cardColor = dotColor;

                  return (
                    <div className="timeline-node" key={idx}>
                      <div className="timeline-indicator">
                        <div className={`timeline-dot timeline-dot-${dotColor}`}>
                          {tipo.icon}
                        </div>
                        <span className="timeline-point-label">P{nodo.punto}</span>
                      </div>

                      <div className={`timeline-card timeline-card-${cardColor}`}>
                        <div className="timeline-card-header">
                          <div>
                            <h4 className="timeline-card-title">{tipo.label}</h4>
                            <div className="flex gap-sm mt-sm" style={{ flexWrap: 'wrap' }}>
                              <span className={`badge badge-${cardColor}`}>{punto.label}</span>
                              {nodo.tipo === 'Despacho' && (
                                <span className="badge badge-gray">🚛 Movilización</span>
                              )}
                            </div>
                          </div>
                          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start', flexDirection: 'column' }}>
                            <span className="timeline-card-date">
                              {new Date(nodo.fecha).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })}
                            </span>
                            <button
                              className="btn btn-outline"
                              style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                              onClick={() => setExpandedIdx(isExpanded ? null : idx)}
                            >
                              {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                              {isExpanded ? 'Menos' : 'Detalle'}
                            </button>
                          </div>
                        </div>

                        <div className="timeline-meta">
                          <div className="timeline-meta-item">
                            <span className="timeline-meta-label">Actor Responsable</span>
                            <span className="timeline-meta-value">{actorRoles[nodo.actor_id] || nodo.actor_id}</span>
                          </div>
                          <div className="timeline-meta-item">
                            <span className="timeline-meta-label">Punto Cadena</span>
                            <span className="timeline-meta-value">{punto.label}</span>
                          </div>
                        </div>

                        {isExpanded && (
                          <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--bg-surface)', borderRadius: '8px', fontSize: '0.85rem' }}>
                            <p className="text-secondary" style={{ margin: 0 }}>{nodo.detalle}</p>
                          </div>
                        )}

                        {nodo.punto === 3 && data.color_semaforo === 'Rojo' && (
                          <div className="fraud-alert">
                            <ShieldAlert size={18} style={{ flexShrink: 0, marginTop: '0.1rem' }} />
                            <div>
                              <strong>⚠️ Alerta de Verificación</strong>
                              <p style={{ margin: '0.2rem 0 0' }}>
                                El transporte asociado a este GTF presenta inconsistencias críticas.
                                Se recomienda retención y verificación documental.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {data && (
                  <div className="timeline-node">
                    <div className="timeline-indicator">
                      <div className={`timeline-dot timeline-dot-${colorClass}`}>
                        {colorClass === 'green' ? <CheckCircle size={20} /> : colorClass === 'yellow' ? <AlertTriangle size={20} /> : <XCircle size={20} />}
                      </div>
                      <span className="timeline-point-label">FINAL</span>
                    </div>
                    <div className={`timeline-card timeline-card-${colorClass}`} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      <div>
                        <h4 className="timeline-card-title">Resultado Final de Trazabilidad</h4>
                        <p className="text-secondary" style={{ margin: '0.25rem 0 0', fontSize: '0.88rem' }}>
                          {data.mensaje}
                        </p>
                      </div>
                      <span className={`badge badge-${colorClass}`} style={{ flexShrink: 0 }}>
                        {data.color_semaforo}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* ── Estado inicial vacío ── */}
          {!data && !loading && !error && (
            <div className="empty-state">
              <div className="empty-state-icon" style={{ color: 'var(--text-muted)' }}>
                <TreePine size={48} />
              </div>
              <h3 style={{ margin: 0, marginTop: '1rem' }}>Consulta el origen de un lote</h3>
              <p style={{ maxWidth: 380, textAlign: 'center', margin: 0 }}>
                Ingresa un Código de Lote, Guía de Transporte Forestal (GTF) o Placa del Vehículo para ver su línea de tiempo completa y verificar
                la legalidad de la madera desde el árbol hasta el producto final.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
