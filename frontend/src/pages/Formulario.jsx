import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import { Save, CheckCircle, ShieldAlert, AlertTriangle, Info, TreePine, Truck, Factory, Scissors, MapPin, Leaf, Lock, ShieldCheck, Globe, Upload } from 'lucide-react';
import * as XLSX from 'xlsx';

const SPECIES = ['Shihuahuaco', 'Cumala', 'Cedro', 'Tornillo', 'Lupuna', 'Caoba'];

const PUNTOS = {
  Tala:           { punto: 2, actor: 'Titular',      gtfReq: false, icon: TreePine, label: 'Tala de Árbol',       desc: 'Registro de extracción del árbol autorizado.' },
  Trozado:        { punto: 2, actor: 'Titular',      gtfReq: false, icon: Scissors, label: 'Trozado',              desc: 'División del árbol talado en trozas.' },
  Despacho:       { punto: 3, actor: 'Transportista',gtfReq: true,  icon: Truck,    label: 'Despacho / GTF',       desc: 'Movilización hacia el CTP con Guía de Transporte.' },
  Transformacion: { punto: 4, actor: 'Operador_CTP', gtfReq: false, icon: Factory,  label: 'Transformación CTP',   desc: 'Procesamiento en Centro de Transformación Primaria.' },
};

const categoryMap = {
  censo: { label: 'Censo Forestal', color: '#4ade80', bg: 'rgba(74, 222, 128, 0.15)' },
  operaciones: { label: 'Libro de Operaciones', color: '#c084fc', bg: 'rgba(192, 132, 252, 0.15)' },
  lotes: { label: 'Lotes y Guías', color: '#60a5fa', bg: 'rgba(96, 165, 250, 0.15)' },
  balances: { label: 'Balances de Extracción', color: '#fb923c', bg: 'rgba(251, 146, 60, 0.15)' }
};

const traducirError = (errStr) => {
  if (!errStr) return "Ocurrió un error inesperado al procesar el archivo.";
  const errUpper = errStr.toString();
  if (errUpper.includes("KeyError")) {
    return "Estructura de columnas inválida para la categoría seleccionada.";
  }
  if (errUpper.includes("UNIQUE constraint failed")) {
    return "Este registro (árbol o código de operación) ya fue ingresado previamente en el sistema.";
  }
  if (errUpper.includes("OperationalError") || errUpper.includes("locked")) {
    return "El servidor de datos está procesando otra carga masiva, tu archivo se procesará automáticamente en breve.";
  }
  return errUpper;
};

// parseCSV removed since we migrated to Excel (.xlsx) formats using SheetJS (xlsx)

export default function Formulario() {
  // Estado para Tabs
  const [activeTab, setActiveTab] = useState('individual'); // 'individual' o 'masiva'
  
  // Estado para Formulario Individual
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

  // Estado para Carga Masiva
  const [tipoArchivo, setTipoArchivo] = useState('operaciones');
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [trabajosActivos, setTrabajosActivos] = useState([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

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

  // Short-polling para actualizar el estado de los trabajos activos en paralelo
  useEffect(() => {
    const enProgreso = trabajosActivos.filter(t => t.id && (t.estado === 'EN_COLA' || t.estado === 'PROCESANDO' || t.estado === 'SUBIENDO'));
    
    if (enProgreso.length === 0) return;
    
    const timer = setInterval(async () => {
      // Disparar las consultas de estado en paralelo (concurrencia)
      const promesas = enProgreso.map(async (trabajo) => {
        // Ignorar si aún no tiene un id del backend (sigue subiendo en POST)
        if (!trabajo.id) return;
        
        try {
          const statusRes = await api.obtenerEstadoCarga(trabajo.id);
          
          // Solo actualizar el estado si cambió para evitar re-renders innecesarios
          if (statusRes.estado !== trabajo.estado || JSON.stringify(statusRes.resultado) !== JSON.stringify(trabajo.resultado)) {
            setTrabajosActivos(prev => prev.map(t => {
              if (t.id === trabajo.id) {
                return {
                  ...t,
                  estado: statusRes.estado,
                  progress: statusRes.estado === 'COMPLETADO' ? 100 : (statusRes.estado === 'PROCESANDO' ? 60 : 30),
                  resultado: statusRes.resultado
                };
              }
              return t;
            }));
          }
        } catch (pollErr) {
          console.error("Error consultando estado de carga", pollErr);
        }
      });
      
      await Promise.all(promesas);
    }, 1500);
    
    return () => clearInterval(timer);
  }, [trabajosActivos]);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const detectType = (filename) => {
    const name = filename.toLowerCase();
    if (!name.endsWith('.xlsx')) return 'no_detectado';
    if (name.includes('censo')) return 'censo';
    if (name.includes('operaciones') || name.includes('libro')) return 'operaciones';
    if (name.includes('gtf') || name.includes('guia') || name.includes('lote')) return 'lotes';
    if (name.includes('balance')) return 'balances';
    return 'no_detectado';
  };

  const handleFilesSelection = (files) => {
    const newSelections = files.map(file => ({
      fileObject: file,
      tipo: detectType(file.name)
    }));
    setSelectedFiles(prev => [...prev, ...newSelections]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelection(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (selectedFiles.length === 0) {
      setError('Por favor selecciona al menos un archivo primero');
      return;
    }

    if (selectedFiles.some(f => f.tipo === 'no_detectado')) {
      setError('Por favor, selecciona la categoría para todos los archivos antes de continuar.');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    // Sniff headers of all selected files
    for (const f of selectedFiles) {
      const file = f.fileObject;
      const tipo = f.tipo;
      try {
        const headers = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = (event) => {
            try {
              const data = new Uint8Array(event.target.result);
              const workbook = XLSX.read(data, { type: 'array' });
              const firstSheetName = workbook.SheetNames[0];
              const worksheet = workbook.Sheets[firstSheetName];
              
              const range = XLSX.utils.decode_range(worksheet['!ref'] || "A1:A1");
              const R = range.s.r; // first row
              const headersList = [];
              for (let C = range.s.c; C <= range.e.c; ++C) {
                const cell = worksheet[XLSX.utils.encode_cell({ r: R, c: C })];
                let val = "";
                if (cell && cell.v !== undefined) {
                  val = String(cell.v).trim().replace(/['"]/g, '');
                }
                headersList.push(val);
              }
              resolve(headersList);
            } catch (err) {
              reject(err);
            }
          };
          reader.onerror = () => reject(new Error("No se pudo leer el archivo."));
          reader.readAsArrayBuffer(file);
        });
        
        if (tipo === 'operaciones' && !headers.includes('operacion_id')) {
          setError(`Error: El archivo "${file.name}" no corresponde al formato de Libro de Operaciones. Por favor, verifica la categoría o el documento antes de volver a intentar.`);
          setLoading(false);
          return;
        }
        
        if (tipo === 'censo' && !headers.includes('arbol_id')) {
          setError(`Error: El archivo "${file.name}" no corresponde al formato de Censo Forestal. Por favor, verifica la categoría o el documento antes de volver a intentar.`);
          setLoading(false);
          return;
        }
        
        if (tipo === 'lotes' && !headers.includes('lote_id')) {
          setError(`Error: El archivo "${file.name}" no corresponde al formato de Lotes y Guías. Por favor, verifica la categoría o el documento antes de volver a intentar.`);
          setLoading(false);
          return;
        }
        
        if (tipo === 'balances' && !headers.includes('balance_id')) {
          setError(`Error: El archivo "${file.name}" no corresponde al formato de Balances de Extracción. Por favor, verifica la categoría o el documento antes de volver a intentar.`);
          setLoading(false);
          return;
        }
      } catch (err) {
        setError(`Error al leer el archivo "${file.name}": ${err.message}`);
        setLoading(false);
        return;
      }
    }
    
    // Generar la lista de nuevos trabajos de forma local en la UI
    const nuevosTrabajos = selectedFiles.map(f => ({
      tempId: `temp-${Math.random().toString(36).substring(2, 9)}`,
      filename: f.fileObject.name,
      tipo: f.tipo,
      estado: 'SUBIENDO',
      progress: 10,
      resultado: null,
      fileObject: f.fileObject
    }));
    
    setTrabajosActivos(prev => [...prev, ...nuevosTrabajos]);
    setSelectedFiles([]); // Limpiar los archivos seleccionados en la UI
    
    // Disparar la subida de todos los archivos en paralelo sin bloquear el bucle (concurrente)
    nuevosTrabajos.forEach(async (trabajo) => {
      try {
        const res = await api.cargarArchivo(trabajo.fileObject, trabajo.tipo);
        
        setTrabajosActivos(prev => prev.map(t => {
          if (t.tempId === trabajo.tempId) {
            return {
              ...t,
              id: res.job_id,
              estado: res.estado,
              progress: res.estado === 'COMPLETADO' ? 100 : 30,
              resultado: res.resultado
            };
          }
          return t;
        }));
      } catch (err) {
        setTrabajosActivos(prev => prev.map(t => {
          if (t.tempId === trabajo.tempId) {
            return {
              ...t,
              estado: 'FALLIDO',
              progress: 100,
              resultado: { error: err.message || 'Error al conectar con el servidor' }
            };
          }
          return t;
        }));
      }
    });
    
    setLoading(false);
  };

  // Carga asíncrona de los resultados del semáforo para cargas completadas
  useEffect(() => {
    const jobsParaCargarSemas = trabajosActivos.filter(
      t => t.estado === 'COMPLETADO' && t.fileObject && !t.semasCargados && !t.cargandoSemas
    );
    
    if (jobsParaCargarSemas.length === 0) return;
    
    jobsParaCargarSemas.forEach(async (trabajo) => {
      setTrabajosActivos(prev => prev.map(t => t.tempId === trabajo.tempId ? { ...t, cargandoSemas: true } : t));
      
      try {
        const records = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = (e) => {
            try {
              const data = new Uint8Array(e.target.result);
              const workbook = XLSX.read(data, { type: 'array' });
              const firstSheetName = workbook.SheetNames[0];
              const worksheet = workbook.Sheets[firstSheetName];
              const jsonData = XLSX.utils.sheet_to_json(worksheet);
              resolve(jsonData);
            } catch (err) {
              reject(err);
            }
          };
          reader.onerror = (e) => reject(new Error("Error leyendo archivo"));
          reader.readAsArrayBuffer(trabajo.fileObject);
        });
        
        const loteIds = new Set();
        records.forEach(r => {
          if (r.lote_id) loteIds.add(String(r.lote_id).trim());
        });
        
        const semas = [];
        for (const loteId of loteIds) {
          try {
            const res = await api.obtenerTimeline(loteId);
            semas.push({
              lote_id: loteId,
              color_semaforo: res.color_semaforo,
              mensaje: res.mensaje
            });
          } catch (e) {
            console.error("Error cargando semáforo para lote", loteId, e);
          }
        }
        
        setTrabajosActivos(prev => prev.map(t => {
          if (t.tempId === trabajo.tempId) {
            return {
              ...t,
              semasCargados: true,
              cargandoSemas: false,
              semaforos: semas
            };
          }
          return t;
        }));
      } catch (err) {
        console.error("Error en parsing de semáforos", err);
        setTrabajosActivos(prev => prev.map(t => t.tempId === trabajo.tempId ? { ...t, semasCargados: true, cargandoSemas: false } : t));
      }
    });
  }, [trabajosActivos]);

  const colorMap = { Verde: 'green', Amarillo: 'yellow', Rojo: 'red' };

  return (
    <div className="page-wrapper" style={{ maxWidth: 900 }}>

      {/* ── Header ── */}
      <div className="page-header">
        <h1 className="page-title text-gradient">Registro y Carga de Datos</h1>
        <p className="page-description">
          Registra operaciones individuales o carga archivos planos en lote para la trazabilidad y pasaporte forestal.
        </p>
      </div>

      {/* ── Tabs Selector ── */}
      <div className="flex gap-sm mb-lg" style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.75rem' }}>
        <button
          type="button"
          className={`btn ${activeTab === 'individual' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => { setActiveTab('individual'); setResult(null); setError(null); }}
        >
          <Scissors size={16} /> Registro Individual
        </button>
        <button
          type="button"
          className={`btn ${activeTab === 'masiva' ? 'btn-primary' : 'btn-outline'}`}
          onClick={() => { setActiveTab('masiva'); setResult(null); setError(null); }}
        >
          <Upload size={16} /> Carga Masiva (Excel / XLSX)
        </button>
      </div>

      {/* ── VISTA REGISTRO INDIVIDUAL ── */}
      {activeTab === 'individual' && (
        <form onSubmit={handleSubmit}>
          {/* Selección de tipo */}
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
      )}

      {/* Styles for shimmer and animations */}
      <style>{`
        @keyframes shimmer-animation {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .shimmer-bar {
          background: linear-gradient(90deg, var(--border) 25%, var(--accent) 50%, var(--border) 75%);
          background-size: 200% 100%;
          animation: shimmer-animation 1.5s infinite linear;
        }
        .dropzone-area:focus-visible {
          border-color: var(--accent) !important;
          box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.3) !important;
        }
        .btn-remove-file:hover {
          background: rgba(239, 68, 68, 0.1) !important;
        }
      `}</style>

      {/* ── VISTA CARGA MASIVA ── */}
      {activeTab === 'masiva' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Bloque de Recursos y Plantillas Oficiales (OSINFOR) */}
          <div className="card-flat" style={{ borderLeft: '4px solid var(--accent)', background: 'var(--bg-surface)' }}>
            <h4 style={{ margin: '0 0 0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.95rem' }}>
              <Info size={18} style={{ color: 'var(--accent)' }} /> Plantillas Oficiales de Carga Masiva (OSINFOR)
            </h4>
            <p className="text-secondary" style={{ margin: '0 0 1rem', fontSize: '0.82rem' }}>
              Descarga los formatos Excel / XLSX oficiales de muestra para estructurar tus datos correctamente y evitar incidentes en la carga masiva.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
              <a 
                href="/arboles_sample.xlsx" 
                download="arboles_template.xlsx" 
                className="btn btn-outline" 
                style={{ fontSize: '0.8rem', justifyContent: 'center', height: 'auto', padding: '0.5rem 0.75rem', gap: '0.4rem' }}
              >
                Descargar Plantilla Censo
              </a>
              <a 
                href="/operaciones_sample.xlsx" 
                download="operaciones_template.xlsx" 
                className="btn btn-outline" 
                style={{ fontSize: '0.8rem', justifyContent: 'center', height: 'auto', padding: '0.5rem 0.75rem', gap: '0.4rem' }}
              >
                Descargar Plantilla Operaciones
              </a>
              <a 
                href="/lotes_sample.xlsx" 
                download="lotes_template.xlsx" 
                className="btn btn-outline" 
                style={{ fontSize: '0.8rem', justifyContent: 'center', height: 'auto', padding: '0.5rem 0.75rem', gap: '0.4rem' }}
              >
                Descargar Plantilla Lotes
              </a>
              <a 
                href="/balances_sample.xlsx" 
                download="balances_template.xlsx" 
                className="btn btn-outline" 
                style={{ fontSize: '0.8rem', justifyContent: 'center', height: 'auto', padding: '0.5rem 0.75rem', gap: '0.4rem' }}
              >
                Descargar Plantilla Balances
              </a>
            </div>
          </div>

          <div className="card-flat">
            <h3 style={{ margin: '0 0 1.25rem', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Upload size={18} style={{ color: 'var(--accent)' }} /> Carga de Archivos de Datos (Excel / XLSX)
            </h3>
            <form onSubmit={handleFileUpload}>
              <div className="form-group">
                <label className="form-label" id="file-upload-label">
                  Arrastrar o Seleccionar Archivos Excel / XLSX
                </label>
                
                {/* Accessible Dropzone Area */}
                <div
                  tabIndex={0}
                  role="button"
                  aria-labelledby="file-upload-label"
                  aria-describedby="file-upload-desc"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      fileInputRef.current.click();
                    }
                  }}
                  onClick={() => fileInputRef.current.click()}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  style={{
                    border: isDragOver ? '2px dashed var(--accent)' : '2px dashed var(--border)',
                    borderRadius: '8px',
                    padding: '2rem 1.5rem',
                    textAlign: 'center',
                    background: isDragOver ? 'rgba(99, 102, 241, 0.05)' : 'var(--bg-surface)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    outline: 'none',
                    position: 'relative'
                  }}
                  className={`dropzone-area ${isDragOver ? 'drag-active' : ''}`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".xlsx"
                    multiple
                    onChange={(e) => handleFilesSelection(Array.from(e.target.files))}
                    disabled={loading}
                    style={{ display: 'none' }}
                  />
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem' }}>
                    <Upload size={24} style={{ color: isDragOver ? 'var(--accent)' : 'var(--text-secondary)', transition: 'color 0.2s' }} />
                    <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                      {isDragOver ? '¡Suelta los archivos aquí!' : 'Arrastra archivos aquí o haz clic para seleccionar'}
                    </span>
                    <span id="file-upload-desc" style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                      Solo archivos .xlsx | Se auto-detectará el tipo según el nombre
                    </span>
                  </div>
                </div>

                {/* List of selected files with auto-detected/selectable category */}
                {selectedFiles.length > 0 && (
                  <div style={{ marginTop: '1rem', fontSize: '0.82rem', background: 'var(--bg-surface)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                    <strong style={{ display: 'block', marginBottom: '0.75rem' }}>Archivos seleccionados ({selectedFiles.length}):</strong>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {selectedFiles.map((item, idx) => {
                        const isNoDetectado = item.tipo === 'no_detectado';
                        return (
                          <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.4rem 0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', border: '1px solid var(--border)', flexWrap: 'wrap', gap: '0.5rem' }}>
                            <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', flexGrow: 1, fontSize: '0.8rem', fontWeight: 500 }}>
                              {item.fileObject.name}
                            </span>
                            
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                              <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Categoría:</span>
                              <select
                                className="form-select"
                                style={{ 
                                  padding: '0.2rem 0.5rem', 
                                  fontSize: '0.78rem', 
                                  width: 'auto', 
                                  margin: 0,
                                  background: isNoDetectado ? 'rgba(239, 68, 68, 0.1)' : 'var(--bg-surface)',
                                  borderColor: isNoDetectado ? 'var(--red-text)' : 'var(--border)',
                                  color: isNoDetectado ? 'var(--red-text)' : 'var(--text-primary)',
                                  borderRadius: '4px'
                                }}
                                value={item.tipo}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setSelectedFiles(prev => prev.map((f, i) => i === idx ? { ...f, tipo: val } : f));
                                }}
                              >
                                <option value="no_detectado">⚠️ No detectado - Selecciona tipo</option>
                                <option value="operaciones">Libro de Operaciones</option>
                                <option value="censo">Censo Forestal</option>
                                <option value="lotes">Lotes y Guías</option>
                                <option value="balances">Balances de Extracción</option>
                              </select>
                              
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedFiles(prev => prev.filter((_, i) => i !== idx));
                                }}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  color: 'var(--red-text)',
                                  cursor: 'pointer',
                                  padding: '2px 6px',
                                  fontSize: '1.2rem',
                                  fontWeight: 'bold',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center'
                                }}
                                className="btn-remove-file"
                                title="Remover de la lista"
                              >
                                ×
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* Contextual Alert for local errors inside Carga Masiva tab */}
              {error && (
                <div className="card mt-md" style={{ borderLeft: '4px solid var(--red-text)', background: 'rgba(239, 68, 68, 0.05)', padding: '0.75rem 1rem' }}>
                  <div className="flex gap-sm">
                    <ShieldAlert size={18} style={{ color: 'var(--red-text)', flexShrink: 0 }} />
                    <div>
                      <strong style={{ color: 'var(--red-text)', fontSize: '0.85rem' }}>Fallo de Validación</strong>
                      <p className="text-secondary mt-sm" style={{ margin: '0.15rem 0 0', fontSize: '0.8rem' }}>{error}</p>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex-between mt-lg" style={{ flexWrap: 'wrap', gap: '1rem' }}>
                <p className="text-muted" style={{ fontSize: '0.82rem', margin: 0 }}>
                  Se validará la idempotencia mediante hash del archivo para evitar cargas repetidas.
                </p>
                <button type="submit" className="btn btn-primary" disabled={selectedFiles.length === 0} style={{ minWidth: 200 }}>
                  <Upload size={17} /> Cargar Archivos
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── PANEL DE PROGRESO DE TRABAJOS CONCURRENTES (SOLO EN CARGA MASIVA) ── */}
      {activeTab === 'masiva' && trabajosActivos.length > 0 && (
        <div className="card mt-lg">
          <h3 style={{ margin: '0 0 1.25rem', fontSize: '1.05rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Upload size={18} style={{ color: 'var(--accent)' }} /> Panel de Subidas y Procesamiento Asíncrono
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {trabajosActivos.map((trabajo) => {
              let badgeColor = 'var(--text-secondary)';
              let badgeBg = 'var(--border)';
              let badgeText = trabajo.estado;
              let showSpinner = false;
              let rowBorder = '1px solid var(--border)';

              if (trabajo.estado === 'SUBIENDO') {
                badgeBg = 'rgba(168, 85, 247, 0.15)';
                badgeColor = '#c084fc';
                badgeText = 'Subiendo...';
                showSpinner = true;
              } else if (trabajo.estado === 'EN_COLA') {
                badgeBg = 'rgba(234, 179, 8, 0.15)';
                badgeColor = '#facc15';
                badgeText = 'En Cola';
              } else if (trabajo.estado === 'PROCESANDO') {
                badgeBg = 'rgba(59, 130, 246, 0.15)';
                badgeColor = '#60a5fa';
                badgeText = 'Procesando';
                showSpinner = true;
              } else if (trabajo.estado === 'COMPLETADO') {
                badgeBg = 'rgba(34, 197, 94, 0.15)';
                badgeColor = '#4ade80';
                badgeText = 'Completado';
                rowBorder = '1px solid rgba(34, 197, 94, 0.3)';
              } else if (trabajo.estado === 'FALLIDO') {
                badgeBg = 'rgba(239, 68, 68, 0.15)';
                badgeColor = '#f87171';
                badgeText = 'Fallido';
                rowBorder = '1px solid rgba(239, 68, 68, 0.3)';
              }

              let lifecycleText = '';
              if (trabajo.estado === 'SUBIENDO') {
                lifecycleText = 'Subiendo archivo al servidor...';
              } else if (trabajo.estado === 'EN_COLA') {
                lifecycleText = 'En cola de espera en el servidor...';
              } else if (trabajo.estado === 'PROCESANDO') {
                lifecycleText = 'Procesando registros en base de datos...';
              } else if (trabajo.estado === 'COMPLETADO') {
                lifecycleText = 'Procesamiento completado con éxito.';
              } else if (trabajo.estado === 'FALLIDO') {
                lifecycleText = 'El procesamiento falló.';
              }

              const cat = categoryMap[trabajo.tipo] || { label: trabajo.tipo, color: 'var(--text-secondary)', bg: 'var(--border)' };

              return (
                <div 
                  key={trabajo.tempId} 
                  className="card-flat" 
                  style={{ 
                    border: rowBorder, 
                    padding: '1.25rem', 
                    borderRadius: '12px',
                    background: 'var(--bg-surface)'
                  }}
                  aria-live="polite"
                  role="status"
                >
                  <div className="flex-between" style={{ flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.75rem' }}>
                    <div>
                      <strong style={{ fontSize: '0.95rem', display: 'block' }}>{trabajo.filename}</strong>
                      <span className="text-muted" style={{ fontSize: '0.78rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.2rem' }}>
                        <span>Categoría:</span>
                        <span 
                          style={{ 
                            background: cat.bg, 
                            color: cat.color, 
                            padding: '0.1rem 0.4rem', 
                            borderRadius: '4px', 
                            fontSize: '0.72rem', 
                            fontWeight: 600,
                            textTransform: 'uppercase',
                            display: 'inline-block'
                          }}
                        >
                          {cat.label}
                        </span>
                        {trabajo.id && ` | Job ID: ${trabajo.id}`}
                      </span>
                      <p style={{ margin: '0.25rem 0 0', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                        {lifecycleText}
                      </p>
                    </div>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span 
                        style={{ 
                          background: badgeBg, 
                          color: badgeColor, 
                          padding: '0.25rem 0.75rem', 
                          borderRadius: '20px', 
                          fontSize: '0.78rem', 
                          fontWeight: 600,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.4rem'
                        }}
                      >
                        {showSpinner && <span className="loading-spinner" style={{ width: '12px', height: '12px', borderWidth: '2px' }} />}
                        {badgeText}
                      </span>
                      {trabajo.estado === 'COMPLETADO' || trabajo.estado === 'FALLIDO' ? (
                        <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>100%</span>
                      ) : (
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, opacity: 0.7 }} className="pulse-progress">...</span>
                      )}
                    </div>
                  </div>

                  <div 
                    role="progressbar" 
                    aria-valuemin="0" 
                    aria-valuemax="100" 
                    aria-valuenow={trabajo.estado === 'COMPLETADO' || trabajo.estado === 'FALLIDO' ? 100 : undefined}
                    aria-label={`Progreso de ${trabajo.filename}`}
                    style={{ background: 'var(--border)', height: '6px', borderRadius: '3px', overflow: 'hidden', marginBottom: '0.5rem' }}
                  >
                    {trabajo.estado === 'COMPLETADO' || trabajo.estado === 'FALLIDO' ? (
                      <div 
                        style={{ 
                          background: trabajo.estado === 'FALLIDO' ? 'var(--red-text)' : 'var(--green-text)', 
                          height: '100%', 
                          width: '100%', 
                          transition: 'width 0.4s ease' 
                        }} 
                      />
                    ) : (
                      <div 
                        className="shimmer-bar"
                        style={{ 
                          height: '100%', 
                          width: '100%'
                        }} 
                      />
                    )}
                  </div>

                  {trabajo.estado === 'COMPLETADO' && (
                    <div style={{ marginTop: '0.75rem', padding: '0.75rem', borderRadius: '8px', background: 'rgba(34, 197, 94, 0.05)', borderLeft: '3px solid var(--green-text)' }}>
                      <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                        <strong>Subida Exitosa:</strong> {trabajo.resultado?.mensaje || 'Se han procesado todos los registros.'}
                      </p>
                      {trabajo.resultado?.registros_procesados !== undefined && (
                        <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          Registros procesados: <strong>{trabajo.resultado.registros_procesados}</strong>
                        </p>
                      )}

                      {/* Semáforos de riesgo de OSINFOR */}
                      {trabajo.semaforos && trabajo.semaforos.length > 0 && (
                        <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', color: 'var(--text-secondary)' }}>
                            Resultado del Semáforo de Riesgo (OSINFOR):
                          </span>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                            {trabajo.semaforos.map((sema, sIdx) => {
                              let c = 'gray';
                              if (sema.color_semaforo === 'Verde') c = 'green';
                              else if (sema.color_semaforo === 'Amarillo' || sema.color_semaforo === 'Ámbar') c = 'yellow';
                              else if (sema.color_semaforo === 'Rojo') c = 'red';
                              
                              const IconComponent = sema.color_semaforo === 'Verde' ? CheckCircle : (sema.color_semaforo === 'Rojo' ? ShieldAlert : AlertTriangle);
                              
                              return (
                                <div key={sIdx} className={`semaforo semaforo-${c}`} style={{ padding: '0.5rem', margin: 0, borderRadius: '6px', fontSize: '0.8rem' }}>
                                  <IconComponent size={16} />
                                  <div>
                                    <strong>Lote {sema.lote_id}: {sema.color_semaforo}</strong>
                                    <p style={{ margin: '0.1rem 0 0', fontSize: '0.75rem', fontWeight: 400 }}>
                                      {sema.mensaje}
                                    </p>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {trabajo.estado === 'FALLIDO' && trabajo.resultado && (
                    <div style={{ marginTop: '0.75rem', padding: '0.75rem', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.05)', borderLeft: '3px solid var(--red-text)' }}>
                      <strong style={{ color: 'var(--red-text)', fontSize: '0.82rem', display: 'block' }}>Error de procesamiento</strong>
                      <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        {traducirError(trabajo.resultado.error)}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Error (Solo Formulario Individual) ── */}
      {activeTab === 'individual' && error && (
        <div className="card mt-lg" style={{ borderLeft: '4px solid var(--red-text)' }}>
          <div className="flex gap-sm">
            <ShieldAlert size={20} style={{ color: 'var(--red-text)', flexShrink: 0 }} />
            <div>
              <strong style={{ color: 'var(--red-text)' }}>Error en el Proceso</strong>
              <p className="text-secondary mt-sm" style={{ margin: '0.25rem 0 0', fontSize: '0.88rem' }}>{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Resultado (Solo Formulario Individual) ── */}
      {activeTab === 'individual' && result && (
        <div className="card mt-lg" style={{ borderLeft: '4px solid var(--green-text)' }}>
          <div className="flex gap-sm mb-md">
            <CheckCircle size={22} style={{ color: 'var(--green-text)', flexShrink: 0 }} />
            <div>
              <strong style={{ color: 'var(--green-text)', fontSize: '1.05rem' }}>{result.mensaje}</strong>
              <p className="text-muted mt-sm" style={{ fontSize: '0.82rem', margin: '0.25rem 0 0' }}>
                ID del Trabajo (Job/Operación): <code className="code-text">{result.operacion_id}</code>
              </p>
            </div>
          </div>

          {/* Hash generado (Solo Formulario Individual) */}
          {result.integridad?.hash_actual && (
            <div style={{ marginBottom: '1rem' }}>
              <p className="form-label mb-sm">Hash SHA-256 del evento</p>
              <div className="hash-chip">
                <Lock size={16} /> <code>{result.integridad.hash_actual}</code>
              </div>
            </div>
          )}

          {/* Resultado del semáforo si validó un lote (Formulario Individual) */}
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
