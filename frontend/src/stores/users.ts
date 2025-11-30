import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiClient, { handleApiError } from '@/api/client';
import type { UserResponse, UserRole } from '@/api/api';

export const useUsersStore = defineStore('users', () => {
  // ============================================================================
  // STATE
  // ============================================================================
  
  const usersList = ref<UserResponse[]>([]);
  const currentUser = ref<UserResponse | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  
  // Paginación
  const currentPage = ref(1);
  const pageSize = ref(20);
  const totalItems = ref(0);
  
  // Filtros
  const filters = ref({
    search: '',
    role: '' as UserRole | '',
  });
  
  // Cache de usuarios individuales (key: id)
  const usersCache = ref<Map<number, UserResponse>>(new Map());
  
  // ============================================================================
  // GETTERS
  // ============================================================================
  
  const totalPages = computed(() => Math.ceil(totalItems.value / pageSize.value));
  
  const hasFilters = computed(() => {
    return !!(filters.value.search || filters.value.role);
  });
  
  const activeUsers = computed(() => {
    return usersList.value.filter(u => u.is_active);
  });
  
  const inactiveUsers = computed(() => {
    return usersList.value.filter(u => !u.is_active);
  });
  
  // ============================================================================
  // ACTIONS
  // ============================================================================
  
  /**
   * Obtener lista de usuarios con filtros y paginación
   */
  const fetchUsers = async () => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.users.listUsers(
        currentPage.value,
        pageSize.value,
        filters.value.role || undefined,
        filters.value.search || undefined
      );
      
      usersList.value = response.data.items || [];
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
   * Obtener detalle de un usuario específico
   */
  const fetchUser = async (id: number, forceRefresh = false) => {
    // Verificar cache primero
    if (!forceRefresh && usersCache.value.has(id)) {
      currentUser.value = usersCache.value.get(id)!;
      return;
    }
    
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.users.getUser(id);
      const user = response.data;
      
      // Actualizar cache
      usersCache.value.set(id, user);
      currentUser.value = user;
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * Crear nuevo usuario
   */
  const createUser = async (data: {
    username: string;
    email: string;
    full_name?: string;
    role: UserRole;
    password?: string;
  }) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.users.createUser(data);
      
      // Refrescar lista
      await fetchUsers();
      
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
   * Actualizar usuario existente
   */
  const updateUser = async (
    id: number,
    data: {
      email?: string;
      full_name?: string;
      role?: UserRole;
      is_active?: boolean;
    }
  ) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await apiClient.users.updateUser(id, data);
      
      // Invalidar cache
      usersCache.value.delete(id);
      
      // Refrescar lista
      await fetchUsers();
      
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
   * Eliminar usuario (soft delete)
   */
  const deleteUser = async (id: number) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      await apiClient.users.deleteUser(id);
      
      // Limpiar cache
      usersCache.value.delete(id);
      
      // Refrescar lista
      await fetchUsers();
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
      role: '',
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
    usersList.value = [];
    currentUser.value = null;
    isLoading.value = false;
    error.value = null;
    currentPage.value = 1;
    totalItems.value = 0;
    clearFilters();
    usersCache.value.clear();
  };
  
  // ============================================================================
  // RETURN
  // ============================================================================
  
  return {
    // State
    usersList,
    currentUser,
    isLoading,
    error,
    currentPage,
    pageSize,
    totalItems,
    filters,
    
    // Getters
    totalPages,
    hasFilters,
    activeUsers,
    inactiveUsers,
    
    // Actions
    fetchUsers,
    fetchUser,
    createUser,
    updateUser,
    deleteUser,
    setPage,
    setFilters,
    clearFilters,
    clearError,
    reset,
  };
});