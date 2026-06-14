import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { api } from '../api';
import {
  ShieldAlert, AlertTriangle, RefreshCw, CheckCircle,
  FileSearch, Clock, TrendingUp, Zap, TreePine, MapPin, User, ShieldCheck, ArrowRight,
  Search, ArrowLeft, XCircle, Calendar, FileText, Activity,
  Truck, Factory, Scissors, Package, Settings, ChevronDown, ChevronUp, ClipboardList, Fingerprint
} from 'lucide-react';

const colorMap = { Rojo: 'red', Amarillo: 'yellow', Verde: 'green' };

const reglaLabel = {
  gtf_asociada:            'GTF Asociada',
  existencia_arbol:        'Existencia del Árbol',
  volumen_disponible:      'Volumen vs. Saldo',
  cronologia_operaciones:  'Cronología de Operaciones',
};

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

export default function Dashboard() {
  const navigate = useNavigate();
  const { auth } = useAuth();
  const rol = auth?.rol || 'OSINFOR';
  const [alertas, setAlertas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [filter, setFilter]   = useState('all');

  // Estados para Titular/Regente
  const [titulos, setTitulos] = useState([]);
  const [loadingTitulos, setLoadingTitulos] = useState(false);
  const [errorTitulos, setErrorTitulos] = useState(null);

  // Estados del Buscador Semántico
  const [criterioBusqueda, setCriterioBusqueda] = useState('arbol_id');
  const [valorBusqueda, setValorBusqueda] = useState('');
  const [buscando, setBuscando] = useState(false);
  const [resultadoBusqueda, setResultadoBusqueda] = useState(null);
  const [errorBusqueda, setErrorBusqueda] = useState(null);
  const [expandedTlIdx, setExpandedTlIdx] = useState(null);

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

  const cargarTitulos = useCallback(async () => {
    try {
      setLoadingTitulos(true);
      setErrorTitulos(null);
      const data = await api.obtenerTitulos();
      setTitulos(data || []);
    } catch (err) {
      console.error("Error cargando títulos:", err);
      setErrorTitulos(err.message || "Error al obtener los títulos habilitantes.");
    } finally {
      setLoadingTitulos(false);
    }
  }, []);

  useEffect(() => {
    if (rol === 'OSINFOR') {
      cargarFallas();
      const interval = setInterval(cargarFallas, 15000);
      return () => clearInterval(interval);
    } else {
      cargarTitulos();
      // Limpiar búsqueda si cambia el rol
      setResultadoBusqueda(null);
      setErrorBusqueda(null);
      setValorBusqueda('');
    }
  }, [rol, cargarFallas, cargarTitulos]);

  // handleRolChange removed since authentication is managed globally via AuthContext

  const ejecutarBusqueda = async (e) => {
    e.preventDefault();
    if (!valorBusqueda.trim()) return;
    setBuscando(true);
    setErrorBusqueda(null);
    setResultadoBusqueda(null);
    setExpandedTlIdx(null);
    try {
      const res = await api.buscarLote(criterioBusqueda, valorBusqueda.trim());
      if (res && res.tipo === 'gtf' && res.lote_id) {
        try {
          const tl = await api.obtenerTimeline(res.lote_id);
          res.timeline = tl.timeline;
          res.color_semaforo = tl.color_semaforo;
          res.mensaje_validacion = tl.mensaje;
        } catch (tlErr) {
          console.error("Error fetching timeline for searched lote:", tlErr);
        }
      }
      setResultadoBusqueda(res);
    } catch (err) {
      console.error("Error en búsqueda semántica:", err);
      setErrorBusqueda(err.message || "No se encontró ningún registro con las credenciales activas.");
    } finally {
      setBuscando(false);
    }
  };

  const limpiarBusqueda = () => {
    setResultadoBusqueda(null);
    setErrorBusqueda(null);
    setValorBusqueda('');
  };

  const totalRojos    = alertas.filter(a => a.color_semaforo === 'Rojo').length;
  const totalAmarillos = alertas.filter(a => a.color_semaforo === 'Amarillo').length;
  const totalVerdes   = alertas.filter(a => a.color_semaforo === 'Verde').length;

  const filtered = filter === 'all'
    ? alertas
    : alertas.filter(a => a.color_semaforo === filter);

  // Visibilidad del buscador (OSINFOR, Regentes)
  const tienePermisosBuscador = rol === 'OSINFOR' || rol === 'Regente';

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <h1 className="page-title text-gradient">Panel de Fiscalización y Control</h1>
        <p className="page-description">
          Supervisión ex-post de OSINFOR sobre censo forestal, operaciones y validaciones de alertas de riesgo en ruta.
        </p>
      </div>

      {/* ── 1. BUSCADOR SEMÁNTICO INSTITUCIONAL (OSINFOR, Regentes, ARFFS, SERFOR) ── */}
      {tienePermisosBuscador && (
        <div className="card mb-lg" style={{ border: '1px solid var(--border)', padding: '1.25rem', borderRadius: '12px' }}>
          <h3 style={{ margin: '0 0 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.05rem' }}>
            <Search size={19} style={{ color: 'var(--accent)' }} /> Buscador Semántico Institucional
          </h3>
          <p className="text-secondary mb-md" style={{ fontSize: '0.85rem', margin: '0 0 1rem' }}>
            Consulta la huella origen y trazabilidad del recurso forestal a nivel nacional de forma polimórfica.
          </p>

          <form onSubmit={ejecutarBusqueda} style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div style={{ width: '220px' }}>
              <select 
                className="form-select" 
                style={{ width: '100%', padding: '0.45rem', fontSize: '0.85rem' }}
                value={criterioBusqueda}
                onChange={e => setCriterioBusqueda(e.target.value)}
              >
                <option value="arbol_id">ID del Árbol (Censo)</option>
                <option value="gtf">GTF / Código de Lote</option>
                <option value="titulo_habilitante">Número de Título Habilitante</option>
              </select>
            </div>
            <div style={{ flex: 1, minWidth: '200px' }}>
              <input
                type="text"
                className="form-input"
                style={{ width: '100%', padding: '0.45rem', fontSize: '0.85rem' }}
                placeholder={
                  criterioBusqueda === 'arbol_id' ? 'Ej: ARB-DEMO-001 o ARB-A-0-0' :
                  criterioBusqueda === 'gtf' ? 'Ej: GTF-DEMO-001, LOT-001, ABC-123' :
                  'Ej: TH-001'
                }
                value={valorBusqueda}
                onChange={e => setValorBusqueda(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary" style={{ padding: '0.45rem 1.2rem', fontSize: '0.85rem' }} disabled={buscando}>
              {buscando ? <span className="loading-spinner" /> : <Search size={16} />}
              <span>Consultar</span>
            </button>
          </form>

          {/* Error de búsqueda */}
          {errorBusqueda && (
            <div style={{ marginTop: '1rem', padding: '0.75rem', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.08)', borderLeft: '3px solid var(--red-text)', display: 'flex', alignItems: 'center', justifyBetween: 'center', gap: '0.5rem' }}>
              <XCircle size={16} style={{ color: 'var(--red-text)' }} />
              <span style={{ fontSize: '0.82rem', color: 'var(--red-text)' }}>{errorBusqueda}</span>
            </div>
          )}
        </div>
      )}

      {/* ── 2. VISUALIZADOR DE TRAZABILIDAD DINÁMICO (RESULTADO BUSCADOR) ── */}
      {resultadoBusqueda && (
        <div className="card mb-lg" style={{ border: '2px solid var(--accent)', padding: '1.5rem', borderRadius: '12px', background: 'rgba(59, 130, 246, 0.02)' }}>
          <div className="flex-between" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem', marginBottom: '1.25rem' }}>
            <div>
              <span className="badge badge-green" style={{ textTransform: 'uppercase', fontSize: '0.7rem' }}>
                Búsqueda Resuelta: {resultadoBusqueda.tipo}
              </span>
              <h2 style={{ margin: '0.25rem 0 0', fontSize: '1.5rem' }}>
                Huella Digital: <span className="text-gradient">{resultadoBusqueda.id || resultadoBusqueda.lote_id || resultadoBusqueda.id_titulo}</span>
              </h2>
            </div>
            <button className="btn btn-outline" style={{ fontSize: '0.8rem', padding: '0.3rem 0.75rem' }} onClick={limpiarBusqueda}>
              <ArrowLeft size={14} /> Volver a Dashboard
            </button>
          </div>

          {/* CASO A: Búsqueda de Árbol */}
          {resultadoBusqueda.tipo === 'arbol' && (
            <div>
              {/* Info del Árbol */}
              <div className="grid-2" style={{ gap: '1rem', marginBottom: '1.5rem' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Ficha de Planificación</h4>
                  <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <span>Especie Autorizada: <strong>{resultadoBusqueda.arbol.id_especie}</strong></span>
                    <span>Volumen Autorizado: <strong>{resultadoBusqueda.arbol.volumen_autorizado} m³</strong></span>
                    <span>Condición Silvicultural: <strong>{resultadoBusqueda.arbol.condicion}</strong></span>
                    <span>Estado en Censo: <strong>{resultadoBusqueda.arbol.censo_estado}</strong></span>
                  </div>
                </div>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Título Habilitante</h4>
                  <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <span>Nombre Concesión: <strong>{resultadoBusqueda.arbol.nombre_concesion}</strong></span>
                    <span>Titular (RUC): <strong>{resultadoBusqueda.arbol.id_titular}</strong></span>
                    <span>Ubicación: <strong>{resultadoBusqueda.arbol.ubicacion_geografica}</strong></span>
                    <span>Plan ID: <strong>{resultadoBusqueda.arbol.id_plan} (Versión {resultadoBusqueda.arbol.version})</strong></span>
                  </div>
                </div>
              </div>

              {/* Trazabilidad Física (Timeline) */}
              <h4 className="mb-sm" style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Activity size={16} className="text-accent" /> Flujo Cronológico de Aprovechamiento</h4>
              <div style={{ position: 'relative', paddingLeft: '1.5rem', borderLeft: '2px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '1rem' }}>
                
                {/* Paso 1: Censo */}
                <div style={{ position: 'relative' }}>
                  <div style={{ position: 'absolute', left: '-2.05rem', top: '2px', width: '12px', height: '12px', borderRadius: '50%', background: 'var(--green-text)' }} />
                  <strong style={{ fontSize: '0.88rem', display: 'block' }}>P1. Planificación (Censo Forestal Aprobado)</strong>
                  <span className="text-secondary" style={{ fontSize: '0.8rem' }}>
                    Aprobado el {resultadoBusqueda.arbol.fecha_aprobacion} bajo la versión {resultadoBusqueda.arbol.version}. Volumen de pie: {resultadoBusqueda.arbol.volumen_autorizado} m³.
                  </span>
                </div>

                {/* Paso 2: Tala */}
                <div style={{ position: 'relative' }}>
                  {resultadoBusqueda.operaciones.tala.length > 0 ? (
                    <>
                      <div style={{ position: 'absolute', left: '-2.05rem', top: '2px', width: '12px', height: '12px', borderRadius: '50%', background: 'var(--green-text)' }} />
                      <strong style={{ fontSize: '0.88rem', display: 'block' }}>P2. Tala de Árbol</strong>
                      {resultadoBusqueda.operaciones.tala.map((o) => (
                        <span key={o.operacion_id} className="text-secondary" style={{ fontSize: '0.8rem', display: 'block' }}>
                          Operación {o.operacion_id} registrada el {o.fecha}. Volumen talado: {o.volumen} m³. Autor: {o.actor_id} ({o.ruc_institucion}).
                        </span>
                      ))}
                    </>
                  ) : (
                    <>
                      <div style={{ position: 'absolute', left: '-2.05rem', top: '2px', width: '12px', height: '12px', borderRadius: '50%', background: 'var(--border)' }} />
                      <strong style={{ fontSize: '0.88rem', display: 'block', color: 'var(--text-secondary)' }}>P2. Tala de Árbol</strong>
                      <span className="text-muted" style={{ fontSize: '0.8rem' }}>Árbol en pie. No se registran operaciones de tala.</span>
                    </>
                  )}
                </div>

                {/* Paso 3: Trozado */}
                <div style={{ position: 'relative' }}>
                  {resultadoBusqueda.operaciones.trozado.length > 0 ? (
                    <>
                      <div style={{ position: 'absolute', left: '-2.05rem', top: '2px', width: '12px', height: '12px', borderRadius: '50%', background: 'var(--green-text)' }} />
                      <strong style={{ fontSize: '0.88rem', display: 'block' }}>P3. División en Trozas (Libro de Operaciones)</strong>
                      {resultadoBusqueda.operaciones.trozado.map((o) => (
                        <span key={o.operacion_id} className="text-secondary" style={{ fontSize: '0.8rem', display: 'block' }}>
                          Troza: <strong>{o.troza_id}</strong> | Volumen: {o.volumen} m³ | Fecha: {o.fecha}.
                        </span>
                      ))}
                    </>
                  ) : (
                    <>
                      <div style={{ position: 'absolute', left: '-2.05rem', top: '2px', width: '12px', height: '12px', borderRadius: '50%', background: 'var(--border)' }} />
                      <strong style={{ fontSize: '0.88rem', display: 'block', color: 'var(--text-secondary)' }}>P3. División en Trozas</strong>
                      <span className="text-muted" style={{ fontSize: '0.8rem' }}>Sin trozas generadas.</span>
                    </>
                  )}
                </div>

                {/* Paso 4: Despacho */}
                <div style={{ position: 'relative' }}>
                  {resultadoBusqueda.operaciones.despacho.length > 0 ? (
                    <>
                      <div style={{ position: 'absolute', left: '-2.05rem', top: '2px', width: '12px', height: '12px', borderRadius: '50%', background: 'var(--yellow-text)' }} />
                      <strong style={{ fontSize: '0.88rem', display: 'block' }}>P4. Transporte Primario (Guía de Transporte Forestal - GTF)</strong>
                      {resultadoBusqueda.operaciones.despacho.map((o) => (
                        <span key={o.operacion_id} className="text-secondary" style={{ fontSize: '0.8rem', display: 'block', marginTop: '0.15rem' }}>
                          Guía: <strong>{o.numero_gtf}</strong> | Lote: {o.lote_id} | Troza: {o.troza_id} | Placa: {o.placa_vehiculo} | DNI Chofer: {o.dni_chofer} | Fecha: {o.fecha}.
                        </span>
                      ))}
                    </>
                  ) : (
                    <>
                      <div style={{ position: 'absolute', left: '-2.05rem', top: '2px', width: '12px', height: '12px', borderRadius: '50%', background: 'var(--border)' }} />
                      <strong style={{ fontSize: '0.88rem', display: 'block', color: 'var(--text-secondary)' }}>P4. Transporte Primario</strong>
                      <span className="text-muted" style={{ fontSize: '0.8rem' }}>Aún en bosque. No movilizado.</span>
                    </>
                  )}
                </div>

                {/* Paso 5: Transformación CTP */}
                <div style={{ position: 'relative' }}>
                  {(resultadoBusqueda.operaciones.transformacion.length > 0 || resultadoBusqueda.transformaciones_ctp.length > 0) ? (
                    <>
                      <div style={{ position: 'absolute', left: '-2.05rem', top: '2px', width: '12px', height: '12px', borderRadius: '50%', background: 'var(--green-text)' }} />
                      <strong style={{ fontSize: '0.88rem', display: 'block' }}>P5. Ingreso y Procesamiento en Planta CTP</strong>
                      {resultadoBusqueda.transformaciones_ctp.map((t) => {
                        const rend = t.volumen_salida ? ((t.volumen_salida / t.volumen_ingreso) * 100).toFixed(1) : 0;
                        return (
                          <span key={t.transformacion_id} className="text-secondary" style={{ fontSize: '0.8rem', display: 'block', marginTop: '0.15rem' }}>
                            Aserradero: {t.operador_ctp} | Producto: <strong>{t.tipo_producto}</strong> | Ingreso: {t.volumen_ingreso} m³ | Salida: {t.volumen_salida} m³ (Rendimiento: {rend}%) | Fecha: {t.fecha_ingreso}.
                          </span>
                        );
                      })}
                      {resultadoBusqueda.operaciones.transformacion.map((o) => (
                        <span key={o.operacion_id} className="text-secondary" style={{ fontSize: '0.8rem', display: 'block', marginTop: '0.15rem' }}>
                          Operación Planta {o.operacion_id} | Lote: {o.lote_id} | Volumen: {o.volumen} m³ | CTP RUC: {o.ruc_institucion}.
                        </span>
                      ))}
                    </>
                  ) : (
                    <>
                      <div style={{ position: 'absolute', left: '-2.05rem', top: '2px', width: '12px', height: '12px', borderRadius: '50%', background: 'var(--border)' }} />
                      <strong style={{ fontSize: '0.88rem', display: 'block', color: 'var(--text-secondary)' }}>P5. Procesamiento en Planta CTP</strong>
                      <span className="text-muted" style={{ fontSize: '0.8rem' }}>Materia prima no ingresada a centro de transformación.</span>
                    </>
                  )}
                </div>

              </div>
            </div>
          )}

          {/* CASO B: Búsqueda de GTF / Lote */}
          {resultadoBusqueda.tipo === 'gtf' && (
            <div>
              <div className="grid-2" style={{ gap: '1rem', marginBottom: '1.5rem' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Detalle del Lote / GTF</h4>
                  <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <span>ID de Lote: <strong>{resultadoBusqueda.lote.lote_id}</strong></span>
                    <span>Guía de Transporte (GTF): <strong>{resultadoBusqueda.lote.numero_gtf}</strong></span>
                    <span>Especie: <strong>{resultadoBusqueda.lote.especie}</strong></span>
                    <span>Volumen Total Movilizado: <strong>{resultadoBusqueda.lote.volumen_total} m³</strong></span>
                  </div>
                </div>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Estado de Control en Ruta</h4>
                  <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <span>Titular Autorizado: <strong>{resultadoBusqueda.lote.titular}</strong></span>
                    <span>Código de Título: <strong>{resultadoBusqueda.lote.titulo_habilitante_id}</strong></span>
                    <span>Parcela de Corta: <strong>{resultadoBusqueda.lote.parcela_corta}</strong></span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      Semáforo OSINFOR:
                      <span className={`badge badge-${colorMap[resultadoBusqueda.lote.color_semaforo] || 'gray'}`}>
                        {resultadoBusqueda.lote.color_semaforo}
                      </span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Mensajes de Validación */}
              {resultadoBusqueda.validaciones.length > 0 ? (
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border)', marginBottom: '1.5rem' }}>
                  <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}><ShieldAlert size={16} className="text-yellow" /> Auditoría del Semáforo de Riesgo (OSINFOR)</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {resultadoBusqueda.validaciones.map((v) => (
                      <div key={v.validacion_id} className={`semaforo semaforo-${colorMap[v.color_semaforo] || 'gray'}`} style={{ padding: '0.5rem 0.75rem', margin: 0, borderRadius: '6px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {v.color_semaforo === 'Rojo' ? <ShieldAlert size={16} /> : <AlertTriangle size={16} />}
                        <span><strong>{v.regla}</strong> ({v.severidad}): {v.mensaje}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div style={{ background: 'rgba(34, 197, 94, 0.05)', padding: '0.85rem', borderRadius: '8px', borderLeft: '4px solid var(--green-text)', color: 'var(--green-text)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
                  <CheckCircle size={16} />
                  <span>Todos los controles ex-ante aprobados. Origen del recurso forestal plenamente conforme.</span>
                </div>
              )}

              {/* Línea de Tiempo de la Cadena */}
              {resultadoBusqueda.timeline && resultadoBusqueda.timeline.length > 0 && (
                <div style={{ marginBottom: '2rem' }}>
                  <h4 className="mb-md" style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '1.5rem' }}>
                    <Activity size={16} className="text-accent" /> Línea de Tiempo de la Cadena de Custodia
                  </h4>
                  <div className="timeline-wrapper" style={{ marginTop: '1rem' }}>
                    {resultadoBusqueda.timeline.map((nodo, idx) => {
                      const punto   = puntoInfo[nodo.punto] || puntoInfo[1];
                      const tipo    = tipoIcon[nodo.tipo]   || { icon: '📌', label: nodo.tipo };
                      const isExpanded = expandedTlIdx === idx;
                      let dotColor  = (nodo.punto === 3 && resultadoBusqueda.color_semaforo === 'Rojo') ? 'red'
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
                                  type="button"
                                  className="btn btn-outline"
                                  style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                                  onClick={() => setExpandedTlIdx(isExpanded ? null : idx)}
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

                            {nodo.punto === 3 && resultadoBusqueda.color_semaforo === 'Rojo' && (
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
                  </div>
                </div>
              )}

              {/* Árboles Origen del Recurso */}
              <h4 className="mb-sm" style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><TreePine size={16} className="text-green" /> Árboles Origen del Recurso</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.75rem', marginTop: '0.5rem' }}>
                {resultadoBusqueda.arboles_origen.map((a) => (
                  <div key={a.id_arbol} className="card-flat" style={{ border: '1px solid var(--border)', padding: '0.75rem', borderRadius: '8px', background: 'var(--bg-surface)' }}>
                    <strong style={{ fontSize: '0.88rem', display: 'block' }}>🌳 {a.id_arbol}</strong>
                    <span className="text-secondary" style={{ fontSize: '0.8rem', display: 'block', marginTop: '0.2rem' }}>
                      Especie: {a.id_especie} | Vol. Autorizado: {a.volumen_autorizado} m³ | Concesión: {a.nombre_concesion} ({a.id_titulo}).
                    </span>
                  </div>
                ))}
                {resultadoBusqueda.arboles_origen.length === 0 && (
                  <p className="text-muted" style={{ fontSize: '0.85rem', gridColumn: '1/-1' }}>No se encontraron registros de los árboles origen en el censo.</p>
                )}
              </div>
            </div>
          )}

          {/* CASO C: Búsqueda de Título */}
          {resultadoBusqueda.tipo === 'titulo' && (
            <div>
              <div className="grid-2" style={{ gap: '1rem', marginBottom: '1.5rem' }}>
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Ficha de Concesión</h4>
                  <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                    <span>Nombre: <strong>{resultadoBusqueda.titulo.nombre_concesion}</strong></span>
                    <span>Código Título: <strong>{resultadoBusqueda.titulo.id_titulo}</strong></span>
                    <span>Titular Civil: <strong>{resultadoBusqueda.titulo.nombre_titular}</strong></span>
                    <span>RUC del Titular: <strong>{resultadoBusqueda.titulo.id_titular}</strong></span>
                    {resultadoBusqueda.titulo.ubicacion_geografica && (
                      <span>Ubicación: <strong>{resultadoBusqueda.titulo.ubicacion_geografica}</strong></span>
                    )}
                  </div>
                </div>
                
                <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Plan de Aprovechamiento Vigente</h4>
                  {resultadoBusqueda.plan ? (
                    <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      <span>Plan ID: <strong>{resultadoBusqueda.plan.id_plan}</strong></span>
                      <span>Versión Activa: <strong>V{resultadoBusqueda.plan.version}</strong></span>
                      <span>Fecha Aprobación: <strong>{resultadoBusqueda.plan.fecha_aprobacion}</strong></span>
                      <span>Estado Legal: <strong>{resultadoBusqueda.plan.estado}</strong></span>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      <AlertTriangle size={16} className="text-yellow" />
                      <span>No se registra un Plan de Aprovechamiento aprobado para este título.</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Resumen del Censo */}
              {resultadoBusqueda.resumen_censo && (
                <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
                  <div className="stat-card" style={{ padding: '0.85rem', borderTop: '3px solid var(--green-text)' }}>
                    <span className="stat-label">Árboles Autorizados</span>
                    <div className="stat-number" style={{ fontSize: '1.5rem', margin: '0.25rem 0' }}>{resultadoBusqueda.resumen_censo.total_arboles}</div>
                    <span className="text-muted" style={{ fontSize: '0.75rem' }}>Registrados en el censo</span>
                  </div>
                  <div className="stat-card" style={{ padding: '0.85rem', borderTop: '3px solid var(--accent)' }}>
                    <span className="stat-label">Volumen Total Autorizado</span>
                    <div className="stat-number" style={{ fontSize: '1.5rem', margin: '0.25rem 0' }}>{resultadoBusqueda.resumen_censo.volumen_total?.toFixed(2) || 0} m³</div>
                    <span className="text-muted" style={{ fontSize: '0.75rem' }}>Suma de cuota forestal</span>
                  </div>
                </div>
              )}

              {/* Botón para ver censo completo */}
              <button 
                onClick={() => navigate(`/trazabilidad?titulo_id=${encodeURIComponent(resultadoBusqueda.id_titulo)}`)} 
                className="btn btn-primary w-full"
                style={{ justifyContent: 'center', gap: '0.5rem' }}
              >
                <span>Inspeccionar Censo Completo</span>
                <ArrowRight size={16} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* Vista Principal Normal */}
      {!resultadoBusqueda && (
        rol === 'OSINFOR' ? (
          <>
            {/* ── Header ── */}
            <div className="page-header flex-between" style={{ flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <h1 className="page-title text-gradient">Control en Ruta</h1>
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
                      <button
                        onClick={() => navigate(`/trazabilidad?lote_id=${encodeURIComponent(alerta.lote_id)}`)}
                        className="btn btn-outline w-full"
                        style={{ justifyContent: 'center', gap: '0.5rem' }}
                      >
                        <FileSearch size={16} />
                        <span>Inspeccionar Cadena de Custodia</span>
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        ) : (
          <>
            {/* ── Header Titular/Regente ── */}
            <div className="page-header flex-between" style={{ flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <h1 className="page-title text-gradient">Títulos Habilitantes</h1>
                <p className="page-description">
                  Visualice los títulos habilitantes (concesiones, predios) asociados a sus credenciales forestales y consulte su estado de aprovechamiento actual.
                </p>
              </div>
              <button className="btn btn-outline" onClick={cargarTitulos} disabled={loadingTitulos}>
                <RefreshCw size={16} className={loadingTitulos ? 'spin-icon' : ''} />
                {loadingTitulos ? 'Actualizando...' : 'Actualizar'}
              </button>
            </div>

            {loadingTitulos && titulos.length === 0 ? (
              <div className="loading-state">
                <span className="loading-spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
                <p>Consultando títulos habilitantes registrados...</p>
              </div>
            ) : errorTitulos ? (
              <div className="card-flat" style={{ borderLeft: '4px solid var(--red-text)', padding: '1.25rem', borderRadius: '12px' }}>
                <p style={{ margin: 0, color: 'var(--red-text)', fontWeight: 600 }}>Error al cargar títulos</p>
                <p style={{ margin: '0.25rem 0 0', fontSize: '0.88rem' }}>{errorTitulos}</p>
              </div>
            ) : titulos.length === 0 ? (
              <div className="empty-state card-flat">
                <div className="empty-state-icon" style={{ color: 'var(--text-muted)' }}>
                  <TreePine size={48} />
                </div>
                <h3 style={{ margin: 0, marginTop: '1rem' }}>Sin Títulos Asignados</h3>
                <p style={{ maxWidth: 420, textAlign: 'center', margin: '0.5rem 0 0' }}>
                  No se encontraron títulos habilitantes asociados al RUC o registro configurado. Modifica tus credenciales en el panel PIDE superior para consultar otros registros.
                </p>
              </div>
            ) : (
              <div className="grid-2" style={{ alignItems: 'start' }}>
                {titulos.map((titulo) => (
                  <div key={titulo.id_titulo} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                      <span 
                        style={{ 
                          background: 'rgba(74, 222, 128, 0.15)', 
                          color: '#4ade80', 
                          padding: '0.2rem 0.6rem', 
                          borderRadius: '4px', 
                          fontSize: '0.72rem', 
                          fontWeight: 600,
                          textTransform: 'uppercase',
                          display: 'inline-block',
                          marginBottom: '0.5rem'
                        }}
                      >
                        Título Habilitante Activo
                      </span>
                      <h3 style={{ margin: 0, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <TreePine size={20} style={{ color: 'var(--green-text)' }} />
                        {titulo.nombre_concesion}
                      </h3>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', background: 'rgba(255, 255, 255, 0.02)', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                        <Zap size={14} className="text-accent" />
                        <span>Código de Título: <strong>{titulo.id_titulo}</strong></span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                        <User size={14} className="text-secondary" />
                        <span>Titular RUC: <strong>{titulo.id_titular}</strong></span>
                      </div>
                      {titulo.ubicacion_geografica && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
                          <MapPin size={14} style={{ color: 'var(--red-text)' }} />
                          <span>Ubicación: <strong className="text-secondary">{titulo.ubicacion_geografica}</strong></span>
                        </div>
                      )}
                    </div>

                    <button
                      onClick={() => navigate(`/trazabilidad?titulo_id=${encodeURIComponent(titulo.id_titulo)}`)}
                      className="btn btn-primary w-full"
                      style={{ justifyContent: 'center', gap: '0.5rem' }}
                    >
                      <span>Ver Censo y Trazabilidad</span>
                      <ArrowRight size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        )
      )}
    </div>
  );
}
