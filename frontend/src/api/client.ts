import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { Configuration } from './configuration';
import {
  AuthenticationApi,
  UsersApi,
  SoftwareApi,
  InstallersApi,
  LicensesApi,
  AuditApi,
  SystemApi,
} from './api';

// ============================================================================
// TYPES
// ============================================================================

interface TokenStorage {
  accessToken: string | null;
  refreshToken: string | null;
}

interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ============================================================================
// TOKEN MANAGEMENT
// ============================================================================

const TOKEN_KEY = 'balaur_access_token';
const REFRESH_TOKEN_KEY = 'balaur_refresh_token';

export const tokenStorage = {
  getAccessToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  
  setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },
  
  clearTokens(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
  
  hasValidToken(): boolean {
    return !!this.getAccessToken();
  },
};

// ============================================================================
// AXIOS INSTANCE
// ============================================================================

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://158.227.4.135:8000/api/v1';

export const axiosInstance: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// REQUEST INTERCEPTOR - Añadir token JWT
// ============================================================================

axiosInstance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.getAccessToken();
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ============================================================================
// RESPONSE INTERCEPTOR - Manejo de errores y refresh token
// ============================================================================

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  
  failedQueue = [];
};

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Si el error es 401 y no es la ruta de login/refresh
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      if (isRefreshing) {
        // Si ya estamos refrescando, encolar la petición
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return axiosInstance(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = tokenStorage.getRefreshToken();

      if (!refreshToken) {
        // No hay refresh token, redirigir a login
        tokenStorage.clearTokens();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        // Intentar refrescar el token
        const response = await axios.post<RefreshTokenResponse>(
          `${baseURL}/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token } = response.data;

        // Guardar nuevos tokens
        tokenStorage.setTokens(access_token, refresh_token);

        // Actualizar header de la petición original
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        // Procesar la cola de peticiones pendientes
        processQueue(null, access_token);

        // Reintentar la petición original
        return axiosInstance(originalRequest);
      } catch (refreshError) {
        // Refresh token inválido, limpiar y redirigir a login
        processQueue(refreshError as Error, null);
        tokenStorage.clearTokens();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Para otros errores, rechazar directamente
    return Promise.reject(error);
  }
);

// ============================================================================
// API CONFIGURATION
// ============================================================================

const apiConfig = new Configuration({
  basePath: baseURL,
  baseOptions: {
    withCredentials: false,
  },
});

// ============================================================================
// API CLIENTS - Instancias de cada API
// ============================================================================

export const authApi = new AuthenticationApi(apiConfig, baseURL, axiosInstance);
export const usersApi = new UsersApi(apiConfig, baseURL, axiosInstance);
export const softwareApi = new SoftwareApi(apiConfig, baseURL, axiosInstance);
export const installersApi = new InstallersApi(apiConfig, baseURL, axiosInstance);
export const licensesApi = new LicensesApi(apiConfig, baseURL, axiosInstance);
export const auditApi = new AuditApi(apiConfig, baseURL, axiosInstance);
export const systemApi = new SystemApi(apiConfig, baseURL, axiosInstance);

// ============================================================================
// ERROR HELPER
// ============================================================================

export interface ApiError {
  message: string;
  statusCode?: number;
  errorCode?: string;
  details?: unknown;
}

export const handleApiError = (error: unknown): ApiError => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail: string; error_code?: string }>;
    
    return {
      message: axiosError.response?.data?.detail || axiosError.message || 'Error desconocido',
      statusCode: axiosError.response?.status,
      errorCode: axiosError.response?.data?.error_code,
      details: axiosError.response?.data,
    };
  }
  
  if (error instanceof Error) {
    return {
      message: error.message,
    };
  }
  
  return {
    message: 'Error desconocido',
  };
};

// ============================================================================
// SYSTEM API - PENDING/PROCESSING FILES TYPES
// ============================================================================

export interface PendingFile {
  filename: string;
  size: number;
  size_mb: number;
  size_gb: number;
  upload_date: string;
}

export interface ProcessingFile {
  filename: string;
  size: number;
  size_mb: number;
  size_gb: number;
  sha256: string;
  validated_date: string;
}

// ============================================================================
// EXPORTS
// ============================================================================

export default {
  auth: authApi,
  users: usersApi,
  software: softwareApi,
  installers: installersApi,
  licenses: licensesApi,
  audit: auditApi,
  system: systemApi,
  axios: axiosInstance,
};