import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';
import { globalAuthCheck } from './guards';

// ============================================================================
// ROUTE DEFINITIONS
// ============================================================================

const routes: RouteRecordRaw[] = [
  // ========== PUBLIC ROUTES ==========
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: {
      requiresAuth: false,
      layout: 'empty',
    },
  },

  // ========== PROTECTED ROUTES ==========
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Dashboard',
    },
  },

  // ========== SOFTWARE ==========
  {
    path: '/software',
    name: 'software-list',
    component: () => import('@/views/SoftwareListView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Software',
    },
  },
  {
    path: '/software/:id',
    name: 'software-detail',
    component: () => import('@/views/SoftwareDetailView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Detalle de Software',
    },
  },

  // ========== INSTALLERS ==========
  {
    path: '/installers',
    name: 'installers',
    component: () => import('@/views/InstallersView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Instaladores',
      roles: ['admin', 'manager'],
    },
  },

  // ========== LICENSES (Admin only) ==========
  {
    path: '/licenses',
    name: 'licenses',
    component: () => import('@/views/LicensesView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Licencias',
      roles: ['admin'],
    },
  },

  // ========== USERS (Admin only) ==========
  {
    path: '/users',
    name: 'users',
    component: () => import('@/views/UsersView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Usuarios',
      roles: ['admin'],
    },
  },

  // ========== AUDIT LOGS (Admin only) ==========
  {
    path: '/audit',
    name: 'audit-logs',
    component: () => import('@/views/AuditLogsView.vue'),
    meta: {
      requiresAuth: true,
      title: 'Auditoría',
      roles: ['admin'],
    },
  },

  // ========== ERROR PAGES ==========
  {
    path: '/forbidden',
    name: 'forbidden',
    component: () => import('@/views/ForbiddenView.vue'),
    meta: {
      requiresAuth: false,
      title: 'Acceso Denegado',
    },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: {
      requiresAuth: false,
      title: 'Página No Encontrada',
    },
  },
];

// ============================================================================
// ROUTER INSTANCE
// ============================================================================

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    return { top: 0 };
  },
});

// ============================================================================
// GLOBAL NAVIGATION GUARDS
// ============================================================================

router.beforeEach(globalAuthCheck);

// Set page title
router.afterEach((to) => {
  const appName = import.meta.env.VITE_APP_NAME || 'Balaur SMS';
  document.title = to.meta.title 
    ? `${to.meta.title} - ${appName}` 
    : appName;
});

// ============================================================================
// EXPORT
// ============================================================================

export default router;

// TypeScript: Extend RouteMeta
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean;
    roles?: string[];
    title?: string;
    layout?: string;
  }
}