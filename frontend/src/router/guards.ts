import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import type { UserRoleType } from '@/types/auth';

/**
 * Guard para rutas que requieren autenticación
 */
export const requireAuth = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
): Promise<void> => {
  const authStore = useAuthStore();

  // Si no hay token, verificar si hay sesión activa
  if (!authStore.isAuthenticated) {
    const hasAuth = await authStore.checkAuth();
    
    if (!hasAuth) {
      // Guardar ruta destino para redirigir después del login
      next({
        name: 'login',
        query: { redirect: to.fullPath },
      });
      return;
    }
  }

  next();
};

/**
 * Guard para rutas que requieren roles específicos
 */
export const requireRole = (roles: UserRoleType | UserRoleType[]) => {
  return async (
    to: RouteLocationNormalized,
    from: RouteLocationNormalized,
    next: NavigationGuardNext
  ): Promise<void> => {
    const authStore = useAuthStore();

    // Primero verificar autenticación
    if (!authStore.isAuthenticated) {
      const hasAuth = await authStore.checkAuth();
      
      if (!hasAuth) {
        next({
          name: 'login',
          query: { redirect: to.fullPath },
        });
        return;
      }
    }

    // Verificar rol
    const requiredRoles = Array.isArray(roles) ? roles : [roles];
    const hasRequiredRole = authStore.hasRole(requiredRoles);

    if (!hasRequiredRole) {
      // Redirigir a página de acceso denegado o dashboard
      next({
        name: 'forbidden',
        query: { from: to.fullPath },
      });
      return;
    }

    next();
  };
};

/**
 * Guard para redirigir usuarios autenticados (ej: login page)
 */
export const redirectIfAuthenticated = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
): Promise<void> => {
  const authStore = useAuthStore();

  if (authStore.isAuthenticated) {
    next({ name: 'dashboard' });
    return;
  }

  next();
};

/**
 * Guard global para verificar autenticación en cada navegación
 */
export const globalAuthCheck = async (
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
): Promise<void> => {
  const authStore = useAuthStore();

  // Si la ruta requiere auth (meta.requiresAuth)
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      const hasAuth = await authStore.checkAuth();
      
      if (!hasAuth) {
        next({
          name: 'login',
          query: { redirect: to.fullPath },
        });
        return;
      }
    }

    // Verificar roles si están definidos
    if (to.meta.roles) {
      const requiredRoles = to.meta.roles as UserRoleType[];
      const hasRequiredRole = authStore.hasRole(requiredRoles);

      if (!hasRequiredRole) {
        next({ name: 'forbidden' });
        return;
      }
    }
  }

  next();
};