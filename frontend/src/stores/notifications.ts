import { defineStore } from 'pinia';
import { ref } from 'vue';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

export const useNotificationsStore = defineStore('notifications', () => {
  // ============================================================================
  // STATE
  // ============================================================================
  
  const toasts = ref<Toast[]>([]);
  let toastIdCounter = 0;

  // ============================================================================
  // ACTIONS
  // ============================================================================

  /**
   * Mostrar un toast
   */
  const showToast = (
    type: ToastType,
    message: string,
    duration: number = 5000
  ): string => {
    const id = `toast-${++toastIdCounter}`;
    
    const toast: Toast = {
      id,
      type,
      message,
      duration,
    };

    toasts.value.push(toast);

    // Auto-remover después de duration
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  };

  /**
   * Remover un toast específico
   */
  const removeToast = (id: string): void => {
    const index = toasts.value.findIndex(t => t.id === id);
    if (index !== -1) {
      toasts.value.splice(index, 1);
    }
  };

  /**
   * Limpiar todos los toasts
   */
  const clearAll = (): void => {
    toasts.value = [];
  };

  // Shortcuts para tipos comunes
  const success = (message: string, duration?: number) => {
    return showToast('success', message, duration);
  };

  const error = (message: string, duration?: number) => {
    return showToast('error', message, duration);
  };

  const warning = (message: string, duration?: number) => {
    return showToast('warning', message, duration);
  };

  const info = (message: string, duration?: number) => {
    return showToast('info', message, duration);
  };

  // ============================================================================
  // RETURN
  // ============================================================================

  return {
    // State
    toasts,

    // Actions
    showToast,
    removeToast,
    clearAll,
    success,
    error,
    warning,
    info,
  };
});