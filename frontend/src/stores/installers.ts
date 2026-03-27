import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiClient, { handleApiError } from '@/api/client';
import type { InstallerResponse } from '@/api/api';
import type { PendingFile, ProcessingFile } from '@/api/client';

interface WebUploadResult {
  filename: string
  sha256: string
  size: number
  size_mb: number
}

export const useInstallersStore = defineStore('installers', () => {
  // ============================================================================
  // STATE
  // ============================================================================
  
  const installersList = ref<InstallerResponse[]>([]);
  const currentInstaller = ref<InstallerResponse | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const pendingFiles = ref<PendingFile[]>([]);
  const processingFiles = ref<ProcessingFile[]>([]);
  const isLoadingFiles = ref(false);

  
  // Watcher stats
  const watcherStats = ref({
    pending: 0,
    processing: 0,
    quarantine: 0,
    is_running: false,
    interval_seconds: 0,
  });
  
  const isLoadingWatcher = ref(false);
  
  // Cache de installers (key: id)
  const installersCache = ref<Map<number, InstallerResponse>>(new Map());
  
  // ============================================================================
  // GETTERS
  // ============================================================================
  
  const installersBySoftware = computed(() => {
    return (softwareId: number) => {
      return installersList.value.filter(i => i.software_id === softwareId);
    };
  });
  
  const totalSize = computed(() => {
    return installersList.value.reduce((sum, installer) => sum + installer.file_size, 0);
  });
  
  const totalSizeGB = computed(() => {
    return (totalSize.value / (1024 ** 3)).toFixed(2);
  });
  
  // ============================================================================
  // ACTIONS
  // ============================================================================
  /**
   * Obtener todos los instaladores (sin filtrar por software)
   */
  const fetchAllInstallers = async () => {
    isLoading.value = true;
    try {
      const { data } = await apiClient.installers.listInstallers();
      installersList.value = data.items ?? [];
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Obtener lista de archivos pending
   */
  const fetchPendingFiles = async () => {
    isLoadingFiles.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.system.listPendingFiles();
      pendingFiles.value = response.data;
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      console.error('Error fetching pending files:', err);
    } finally {
      isLoadingFiles.value = false;
    }
  };

  /**
   * Obtener lista de archivos processing
   */
  const fetchProcessingFiles = async () => {
    isLoadingFiles.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.system.listProcessingFiles();
      processingFiles.value = response.data;
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      console.error('Error fetching processing files:', err);
    } finally {
      isLoadingFiles.value = false;
    }
  };
  

  /**
   * Obtener lista de instaladores de un software
   */
  const fetchInstallersBySoftware = async (softwareId: number) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.software.listSoftwareInstallers(softwareId);
      
      installersList.value = response.data.items || [];
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * Obtener detalle de un instalador específico
   */
  const fetchInstaller = async (id: number, forceRefresh = false) => {
    // Verificar cache primero
    if (!forceRefresh && installersCache.value.has(id)) {
      currentInstaller.value = installersCache.value.get(id)!;
      return;
    }
    
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.installers.getInstaller(id);
      const installer = response.data;
      
      // Actualizar cache
      installersCache.value.set(id, installer);
      currentInstaller.value = installer;
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * Registrar nuevo instalador
   */
  const registerInstaller = async (data: {
    software_id: number;
    version: string;
    filename: string;
    file_size: number;
    sha256_hash: string;
    architecture?: string;
    platform?: string;
    notes?: string;
  }) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.installers.registerInstaller(data);
      
      // Refrescar lista del software
      await fetchInstallersBySoftware(data.software_id);
      
      return response.data;
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * Descargar instalador
   * Nota: La descarga real se maneja en el componente con window.open o axios con responseType: 'blob'
   */
  const downloadInstaller = async (id: number) => {
    try {
      // Obtener info del instalador para el nombre del archivo
      const installer = installersList.value.find(i => i.id === id);
      const filename = installer?.filename || `installer_${id}.exe`;
      
      // Descargar con apiClient (envía token automáticamente)
      const response = await apiClient.axios.get(`/installers/${id}/download`, {
        responseType: 'blob'
      });
      
      // Crear blob URL y descargar
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      // Refrescar contador
      await fetchInstaller(id, true);
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    }
  };
  
  /**
   * Eliminar instalador
   */
  const deleteInstaller = async (id: number, softwareId: number) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      await apiClient.installers.deleteInstaller(id);
      
      // Limpiar cache
      installersCache.value.delete(id);
      
      // Refrescar lista del software
      await fetchInstallersBySoftware(softwareId);
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * Obtener estadísticas del FTP Watcher
   */
  const fetchWatcherStats = async () => {
    isLoadingWatcher.value = true;
    
    try {
      const response = await apiClient.system.getWatcherStats();
      
      watcherStats.value = {
        pending: response.data.pending || 0,
        processing: response.data.processing || 0,
        quarantine: response.data.quarantine || 0,
        is_running: response.data.is_running || false,
        interval_seconds: response.data.interval_seconds || 0,
      };
    } catch (err) {
      const apiError = handleApiError(err);
      console.error('Error fetching watcher stats:', apiError.message);
      // No lanzar error, solo log
    } finally {
      isLoadingWatcher.value = false;
    }
  };
  
  /**
   * Limpiar error
   */
  const clearError = () => {
    error.value = null;
  };
  
  /**
   * Reset store
   */
  const reset = () => {
    installersList.value = [];
    currentInstaller.value = null;
    isLoading.value = false;
    error.value = null;
    watcherStats.value = {
      pending: 0,
      processing: 0,
      quarantine: 0,
      is_running: false,
      interval_seconds: 0,
    };
    installersCache.value.clear();
  };
  
// CAMBIAR el tipo de retorno:
  const uploadFile = async (
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<WebUploadResult> => {   // ← WebUploadResult en lugar de WebUploadResponse
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.axios.post<WebUploadResult>(
      '/system/upload-installer',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (event) => {
          if (onProgress && event.total) {
            onProgress(Math.round((event.loaded * 100) / event.total))
          }
        },
      }
    )
    return response.data
  }

  // ============================================================================
  // RETURN
  // ============================================================================
  
  return {
    // State
    installersList,
    currentInstaller,
    isLoading,
    error,
    watcherStats,
    isLoadingWatcher,
    pendingFiles,
    processingFiles,
    isLoadingFiles,   
    
    // Getters
    installersBySoftware,
    totalSize,
    totalSizeGB,
    
    // Actions
    fetchInstallersBySoftware,
    fetchInstaller,
    fetchAllInstallers,
    registerInstaller,
    downloadInstaller,
    deleteInstaller,
    fetchWatcherStats,
    fetchPendingFiles,
    fetchProcessingFiles,
    clearError,
    reset,
    uploadFile,
  };
});