import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiClient, { handleApiError } from '@/api/client';
import type { LicenseResponse, LicenseDetailResponse, LicenseType } from '@/api/api';

export const useLicensesStore = defineStore('licenses', () => {
  // ============================================================================
  // STATE
  // ============================================================================
  
  const licensesList = ref<LicenseResponse[]>([]);
  const currentLicense = ref<LicenseDetailResponse | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  
  // Paginación
  const currentPage = ref(1);
  const pageSize = ref(20);
  const totalItems = ref(0);
  
  // Filtros
  const filters = ref({
    softwareId: null as number | null,
  });
  
  // Cache de licencias (key: id) - SIN claves descifradas
  const licensesCache = ref<Map<number, LicenseResponse>>(new Map());
  
  // ============================================================================
  // GETTERS
  // ============================================================================
  
  const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value));
  
  const hasFilters = computed(() => {
    return !!filters.value.softwareId;
  });
  
  const activeLicenses = computed(() => {
    return licensesList.value.filter(license => {
      if (!license.expiration_date) return true;
      return new Date(license.expiration_date) > new Date();
    });
  });
  
  const expiredLicenses = computed(() => {
    return licensesList.value.filter(license => {
      if (!license.expiration_date) return false;
      return new Date(license.expiration_date) <= new Date();
    });
  });
  
  // ============================================================================
  // ACTIONS
  // ============================================================================
  
  /**
   * Obtener lista de licencias con filtros y paginación
   */
  const fetchLicenses = async () => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.licenses.listLicenses(
        currentPage.value,
        pageSize.value,
        filters.value.softwareId || undefined
      );
      
      licensesList.value = response.data.items || [];
      totalItems.value = response.data.total || 0;
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * Obtener detalle de una licencia CON CLAVE DESCIFRADA
   * IMPORTANTE: Este acceso queda registrado en audit logs
   */
  const fetchLicenseWithKey = async (id: number) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.licenses.getLicense(id);
      const license = response.data;
      
      // NO cachear licencias con claves descifradas por seguridad
      currentLicense.value = license;
      
      return license;
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * Crear nueva licencia
   */
  const createLicense = async (data: {
    software_id: number;
    license_type: LicenseType;
    license_key: string;
    max_activations?: number;
    expiration_date?: string;
    notes?: string;
  }) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.licenses.createLicense(data);
      
      // Refrescar lista
      await fetchLicenses();
      
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
   * Actualizar licencia existente
   */
  const updateLicense = async (
    id: number,
    data: {
      license_type?: LicenseType;
      license_key?: string;
      max_activations?: number;
      expiration_date?: string;
      notes?: string;
    }
  ) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.licenses.updateLicense(id, data);
      
      // Invalidar cache
      licensesCache.value.delete(id);
      currentLicense.value = null;
      
      // Refrescar lista
      await fetchLicenses();
      
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
   * Eliminar licencia
   */
  const deleteLicense = async (id: number) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      await apiClient.licenses.deleteLicense(id);
      
      // Limpiar cache
      licensesCache.value.delete(id);
      currentLicense.value = null;
      
      // Refrescar lista
      await fetchLicenses();
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * Cambiar página
   */
  const setPage = (page: number) => {
    if (page >= 1 && page <= totalPages.value) {
      currentPage.value = page;
    }
  };
  
  /**
   * Actualizar filtros
   */
  const setFilters = (newFilters: Partial<typeof filters.value>) => {
    filters.value = { ...filters.value, ...newFilters };
    currentPage.value = 1; // Reset a primera página al filtrar
  };
  
  /**
   * Limpiar filtros
   */
  const clearFilters = () => {
    filters.value = {
      softwareId: null,
    };
    currentPage.value = 1;
  };
  
  /**
   * Limpiar error
   */
  const clearError = () => {
    error.value = null;
  };
  
  /**
   * Limpiar licencia actual (importante para seguridad)
   */
  const clearCurrentLicense = () => {
    currentLicense.value = null;
  };
  
  /**
   * Reset store
   */
  const reset = () => {
    licensesList.value = [];
    currentLicense.value = null;
    isLoading.value = false;
    error.value = null;
    currentPage.value = 1;
    totalItems.value = 0;
    clearFilters();
    licensesCache.value.clear();
  };
  
  // ============================================================================
  // RETURN
  // ============================================================================
  
  return {
    // State
    licensesList,
    currentLicense,
    isLoading,
    error,
    currentPage,
    pageSize,
    totalItems,
    filters,
    
    // Getters
    totalPages,
    hasFilters,
    activeLicenses,
    expiredLicenses,
    
    // Actions
    fetchLicenses,
    fetchLicenseWithKey,
    createLicense,
    updateLicense,
    deleteLicense,
    setPage,
    setFilters,
    clearFilters,
    clearError,
    clearCurrentLicense,
    reset,
  };
});