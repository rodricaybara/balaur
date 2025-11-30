import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import apiClient, { tokenStorage, handleApiError } from '@/api/client';
import type { UserResponse, LoginRequest } from '@/api/api';
import type { UserRoleType } from '@/types/auth';

export const useAuthStore = defineStore('auth', () => {
  // ============================================================================
  // STATE
  // ============================================================================
  
  const user = ref<UserResponse | null>(null);
  const accessToken = ref<string | null>(tokenStorage.getAccessToken());
  const refreshToken = ref<string | null>(tokenStorage.getRefreshToken());
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  // ============================================================================
  // GETTERS
  // ============================================================================
  
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value);
  
  const userRole = computed((): UserRoleType | null => {
    return user.value?.role as UserRoleType || null;
  });

  const isAdmin = computed(() => userRole.value === 'admin');
  const isManager = computed(() => userRole.value === 'manager');
  const isUser = computed(() => userRole.value === 'user');
  const isGuest = computed(() => userRole.value === 'guest');

  const canManageSoftware = computed(() => {
    return userRole.value === 'admin' || userRole.value === 'manager';
  });

  const canManageUsers = computed(() => {
    return userRole.value === 'admin';
  });

  const canViewLicenses = computed(() => {
    return userRole.value === 'admin';
  });

  const canDownload = computed(() => {
    return userRole.value !== 'guest';
  });

  const hasRole = (role: UserRoleType | UserRoleType[]): boolean => {
    if (!userRole.value) return false;
    
    if (Array.isArray(role)) {
      return role.includes(userRole.value);
    }
    
    return userRole.value === role;
  };

  // ============================================================================
  // ACTIONS
  // ============================================================================

  /**
   * Iniciar sesión
   */
  const login = async (credentials: LoginRequest): Promise<void> => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await apiClient.auth.login(credentials);
      const { access_token, refresh_token } = response.data;

      // Guardar tokens
      accessToken.value = access_token;
      refreshToken.value = refresh_token;
      tokenStorage.setTokens(access_token, refresh_token);

      // Obtener datos del usuario
      await fetchCurrentUser();
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Obtener información del usuario actual
   */
  const fetchCurrentUser = async (): Promise<void> => {
    try {
      const response = await apiClient.auth.getCurrentUser();
      user.value = response.data;
    } catch (err) {
      const apiError = handleApiError(err);
      error.value = apiError.message;
      
      // Si falla obtener el usuario, limpiar sesión
      logout();
      throw err;
    }
  };

  /**
   * Cerrar sesión
   */
  const logout = (): void => {
    user.value = null;
    accessToken.value = null;
    refreshToken.value = null;
    tokenStorage.clearTokens();
    error.value = null;
  };

  /**
   * Verificar si hay sesión activa al cargar la app
   */
  const checkAuth = async (): Promise<boolean> => {
    if (!tokenStorage.hasValidToken()) {
      logout();
      return false;
    }

    try {
      await fetchCurrentUser();
      return true;
    } catch (err) {
      logout();
      return false;
    }
  };

  /**
   * Limpiar error
   */
  const clearError = (): void => {
    error.value = null;
  };

  // ============================================================================
  // RETURN
  // ============================================================================

  return {
    // State
    user,
    accessToken,
    refreshToken,
    isLoading,
    error,

    // Getters
    isAuthenticated,
    userRole,
    isAdmin,
    isManager,
    isUser,
    isGuest,
    canManageSoftware,
    canManageUsers,
    canViewLicenses,
    canDownload,

    // Actions
    login,
    logout,
    checkAuth,
    fetchCurrentUser,
    clearError,
    hasRole,
  };
});