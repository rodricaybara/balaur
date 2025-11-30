import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiClient, { handleApiError } from '@/api/client';
import type { SoftwareResponse, SoftwareDetailResponse } from '@/api/api';

export const useSoftwareStore = defineStore('software', () => {
  // ============================================================================
  // STATE
  // ============================================================================
  
  const softwareList = ref<SoftwareResponse[]>([]);
  const currentSoftware = ref<SoftwareDetailResponse | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  
  // Paginación
  const currentPage = ref(1);
  const pageSize = ref(12);
  const totalItems = ref(0);
  
  // Filtros
  const filters = ref({
    search: '',
    category: '',
    vendor: '',
  });
  
  // Cache de software individual (key: id)
  const softwareCache = ref<Map<number, SoftwareDetailResponse>>(new Map());

  // ============================================================================
  // GETTERS
  // ============================================================================
  
  const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value));
  
  const hasFilters = computed(() => {
    return !!(filters.value.search || filters.value.category || filters.value.vendor);
  });

  const categories = computed(() => {
    const uniqueCategories = [...new Set(softwareList.value.map(s => s.category))];
    return uniqueCategories.sort();
  });

  const vendors = computed(() => {
    const uniqueVendors = [...new Set(softwareList.value.map(s => s.vendor))];
    return uniqueVendors.sort();
  });

  // ============================================================================
  // ACTIONS
  // ============================================================================

  /**
   * Obtener lista de software con filtros y paginación
   */
  const fetchSoftwareList = async () => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await apiClient.software.listSoftware(
        currentPage.value,
        pageSize.value,
        filters.value.category || undefined,
        filters.value.search || undefined,
        filters.value.vendor || undefined
      );

      softwareList.value = response.data.items || [];
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
   * Obtener detalle de un software específico
   */
  const fetchSoftwareDetail = async (id: number, forceRefresh = false) => {
    // Verificar cache primero
    if (!forceRefresh && softwareCache.value.has(id)) {
      currentSoftware.value = softwareCache.value.get(id)!;
      return;
    }

    isLoading.value = true;
    error.value = null;

    try {
      const response = await apiClient.software.getSoftware(id);
      const software = response.data;
      
      // Actualizar cache
      softwareCache.value.set(id, software);
      currentSoftware.value = software;
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Crear nuevo software
   */
  const createSoftware = async (data: {
    name: string;
    vendor: string;
    category: string;
    description?: string;
    website?: string;
  }) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await apiClient.software.createSoftware(data);
      
      // Refrescar lista
      await fetchSoftwareList();
      
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
   * Actualizar software existente
   */
  const updateSoftware = async (
    id: number,
    data: {
      name?: string;
      vendor?: string;
      category?: string;
      description?: string;
      website?: string;
    }
  ) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await apiClient.software.updateSoftware(id, data);
      
      // Invalidar cache
      softwareCache.value.delete(id);
      
      // Refrescar lista
      await fetchSoftwareList();
      
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
   * Eliminar software
   */
  const deleteSoftware = async (id: number) => {
    isLoading.value = true;
    error.value = null;

    try {
      await apiClient.software.deleteSoftware(id);
      
      // Limpiar cache
      softwareCache.value.delete(id);
      
      // Refrescar lista
      await fetchSoftwareList();
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
      search: '',
      category: '',
      vendor: '',
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
   * Reset store
   */
  const reset = () => {
    softwareList.value = [];
    currentSoftware.value = null;
    isLoading.value = false;
    error.value = null;
    currentPage.value = 1;
    totalItems.value = 0;
    clearFilters();
    softwareCache.value.clear();
  };

  // ============================================================================
  // RETURN
  // ============================================================================

  return {
    // State
    softwareList,
    currentSoftware,
    isLoading,
    error,
    currentPage,
    pageSize,
    totalItems,
    filters,

    // Getters
    totalPages,
    hasFilters,
    categories,
    vendors,

    // Actions
    fetchSoftwareList,
    fetchSoftwareDetail,
    createSoftware,
    updateSoftware,
    deleteSoftware,
    setPage,
    setFilters,
    clearFilters,
    clearError,
    reset,
  };
});