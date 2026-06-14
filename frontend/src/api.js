const API_BASE_URL = 'http://localhost:8000/api/v1';

const getPideHeaders = () => {
  const headers = {};
  const rol = localStorage.getItem('pide_rol');
  const ruc = localStorage.getItem('pide_ruc');
  const serfor = localStorage.getItem('pide_serfor');
  const dni = localStorage.getItem('pide_dni');
  const placa = localStorage.getItem('pide_placa');

  if (rol) headers['X-PIDE-Rol'] = rol;
  if (ruc) headers['X-PIDE-RUC'] = ruc;
  if (serfor) headers['X-PIDE-Serfor'] = serfor;
  if (dni) headers['X-PIDE-DNI'] = dni;
  if (placa) headers['X-PIDE-Placa'] = placa;

  // Inyectar X-PIDE-Sesion como JSON string
  const sessionObj = {
    rol,
    ruc,
    serfor,
    dni,
    placa
  };
  headers['X-PIDE-Sesion'] = JSON.stringify(sessionObj);

  return headers;
};

export const api = {
  // Registrar nueva operación (Puntos 2, 3, 4)
  registrarOperacion: async (payload) => {
    try {
      const response = await fetch(`${API_BASE_URL}/operaciones/registrar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getPideHeaders(),
        },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error en el servidor');
      }
      
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  // Consultar línea de tiempo
  obtenerTimeline: async (loteId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/trazabilidad/timeline/${loteId}`, {
        headers: {
          ...getPideHeaders(),
        }
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Lote no encontrado');
      }
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  // Consultar fallas (Semáforo Rojo/Amarillo)
  obtenerFallas: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/reportes/fallas`, {
        headers: {
          ...getPideHeaders(),
        }
      });
      if (!response.ok) {
        throw new Error('Error al cargar reportes');
      }
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  // Cargar archivo plano (Censo, Operaciones, Lotes, Balances)
  cargarArchivo: async (file, tipoArchivo) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE_URL}/trazabilidad/cargar-archivo?tipo_archivo=${tipoArchivo}`, {
        method: 'POST',
        headers: {
          ...getPideHeaders(),
        },
        body: formData,
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error en la subida del archivo');
      }
      
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  // Obtener estado del job de carga
  obtenerEstadoCarga: async (jobId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/trazabilidad/estado/${jobId}`, {
        headers: {
          ...getPideHeaders(),
        }
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al obtener estado');
      }
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  // Obtener títulos habilitantes del usuario
  obtenerTitulos: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/titulos`, {
        headers: {
          ...getPideHeaders(),
        }
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al obtener títulos');
      }
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  // Obtener árboles del censo asociados a un título habilitante
  obtenerArbolesTitulo: async (idTitulo) => {
    try {
      const response = await fetch(`${API_BASE_URL}/titulos/${idTitulo}/arboles`, {
        headers: {
          ...getPideHeaders(),
        }
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al obtener árboles del título');
      }
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  // Subir plan de aprovechamiento
  subirPlan: async (file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`${API_BASE_URL}/planes/subir`, {
        method: 'POST',
        headers: {
          ...getPideHeaders(),
        },
        body: formData,
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al subir plan');
      }
      
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  // Buscar trazabilidad forestal por criterio y valor
  buscarLote: async (criterio, valor = null) => {
    try {
      let url = `${API_BASE_URL}/trazabilidad/buscar?criterio=${encodeURIComponent(criterio)}`;
      if (valor) {
        url += `&valor=${encodeURIComponent(valor)}`;
      }
      const response = await fetch(url, {
        headers: {
          ...getPideHeaders()
        }
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'No se encontró información');
      }
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }
};
