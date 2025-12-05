import type { UserResponse } from '@/api/api';

// Exportar tipos desde la API generada
export type { 
  UserRole,
  UserResponse,
  LoginRequest,
  TokenResponse,
} from '@/api/api';

// Tipos adicionales para el frontend
export interface AuthState {
  user: UserResponse | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

// Helper para verificar roles
export const USER_ROLES = {
  ADMIN: 'admin' as const,
  MANAGER: 'manager' as const,
  USER: 'user' as const,
  GUEST: 'guest' as const,
};

export type UserRoleType = typeof USER_ROLES[keyof typeof USER_ROLES];

// Permisos por rol
export const ROLE_PERMISSIONS = {
  admin: ['*'], // Acceso total
  manager: ['software.create', 'software.update', 'installer.create', 'installer.delete'],
  user: ['software.read', 'installer.download'],
  guest: ['software.read'],
};

export const hasPermission = (userRole: UserRoleType, permission: string): boolean => {
  const permissions = ROLE_PERMISSIONS[userRole] || [];
  return permissions.includes('*') || permissions.includes(permission);
};

export const canManageSoftware = (role: UserRoleType): boolean => {
  return role === 'admin' || role === 'manager';
};

export const canManageUsers = (role: UserRoleType): boolean => {
  return role === 'admin';
};

export const canViewLicenses = (role: UserRoleType): boolean => {
  return role === 'admin';
};

export const canDownloadInstallers = (role: UserRoleType): boolean => {
  return role !== 'guest';
};