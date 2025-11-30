import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiClient, { handleApiError } from '@/api/client';
import type { AuditLogResponse, AuditAction } from '@/api/api';

export const useAuditStore = defineStore('audit', () => {
  // ============================================================================
  // STATE
  // ============================================================================
  
  const auditLogs = ref<AuditLogResponse[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  
  // Paginación
  const currentPage = ref(1);
  const pageSize = ref(50);
  const totalItems = ref(0);
  
  // Filtros
  const filters = ref({
    userId: null as number | null,
    action: '' as AuditAction | '',
    resourceType: '',
    dateFrom: null as string | null,
    dateTo: null as string | null,
  });
  
  // ============================================================================
  // GETTERS
  // ============================================================================
  
  const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value));
  
  const hasFilters = computed(() => {
    return !!(
      filters.value.userId ||
      filters.value.action ||
      filters.value.resourceType ||
      filters.value.dateFrom ||
      filters.value.dateTo
    );
  });
  
  // Agrupar logs por acción
  const logsByAction = computed(() => {
    const grouped: Record<string, number> = {};
    auditLogs.value.forEach(log => {
      grouped[log.action] = (grouped[log.action] || 0) + 1;
    });
    return grouped;
  });
  
  // Agrupar logs por usuario
  const logsByUser = computed(() => {
    const grouped: Record<string, number> = {};
    auditLogs.value.forEach(log => {
      const username = log.username || 'Unknown';
      grouped[username] = (grouped[username] || 0) + 1;
    });
    return grouped;
  });
  
  // Logs recientes (últimos 20)
  const recentLogs = computed(() => {
    return auditLogs.value.slice(0, 20);
  });
  
  // ============================================================================
  // ACTIONS
  // ============================================================================
  
  /**
   * Obtener logs de auditoría con filtros y paginación
   */
  const fetchAuditLogs = async () => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.audit.getAuditLogs(
        currentPage.value,
        pageSize.value,
        filters.value.userId || undefined,
        filters.value.action || undefined,
        filters.value.resourceType || undefined,
        filters.value.dateFrom || undefined,
        filters.value.dateTo || undefined
      );
      
      auditLogs.value = response.data.items || [];
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
      userId: null,
      action: '',
      resourceType: '',
      dateFrom: null,
      dateTo: null,
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
    auditLogs.value = [];
    isLoading.value = false;
    error.value = null;
    currentPage.value = 1;
    totalItems.value = 0;
    clearFilters();
  };
  
  /**
   * Exportar logs a CSV
   */
  const exportToCSV = () => {
    if (auditLogs.value.length === 0) {
      return;
    }
    
    // Crear CSV
    const headers = ['Timestamp', 'User', 'Action', 'Resource Type', 'Resource ID', 'IP Address'];
    const rows = auditLogs.value.map(log => [
      log.timestamp,
      log.username || 'Unknown',
      log.action,
      log.resource_type || '-',
      log.resource_id || '-',
      log.ip_address || '-',
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    // Descargar
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `audit_logs_${new Date().toISOString()}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  // ============================================================================
  // RETURN
  // ============================================================================
  
  return {
    // State
    auditLogs,
    isLoading,
    error,
    currentPage,
    pageSize,
    totalItems,
    filters,
    
    // Getters
    totalPages,
    hasFilters,
    logsByAction,
    logsByUser,
    recentLogs,
    
    // Actions
    fetchAuditLogs,
    setPage,
    setFilters,
    clearFilters,
    clearError,
    reset,
    exportToCSV,
  };
});