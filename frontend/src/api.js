const API_BASE_URL = 'http://localhost:8000/api/v1';

export const api = {
  // Registrar nueva operación (Puntos 2, 3, 4)
  registrarOperacion: async (payload) => {
    try {
      const response = await fetch(`${API_BASE_URL}/operaciones/registrar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
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
      const response = await fetch(`${API_BASE_URL}/trazabilidad/timeline/${loteId}`);
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
      const response = await fetch(`${API_BASE_URL}/reportes/fallas`);
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
      const response = await fetch(`${API_BASE_URL}/trazabilidad/estado/${jobId}`);
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al obtener estado');
      }
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }
};
