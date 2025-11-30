<script setup lang="ts">
import { useNotificationsStore } from '@/stores/notifications';
import type { ToastType } from '@/stores/notifications';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-vue-next';

const notificationsStore = useNotificationsStore();

const getToastIcon = (type: ToastType) => {
  const icons = {
    success: CheckCircle,
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
  };
  return icons[type];
};

const getToastColors = (type: ToastType) => {
  const colors = {
    success: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: 'text-green-600',
      text: 'text-green-800',
    },
    error: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: 'text-red-600',
      text: 'text-red-800',
    },
    warning: {
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
      icon: 'text-yellow-600',
      text: 'text-yellow-800',
    },
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'text-blue-600',
      text: 'text-blue-800',
    },
  };
  return colors[type];
};
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed top-4 right-4 z-50 flex flex-col gap-3 max-w-md"
      role="region"
      aria-label="Notifications"
    >
      <TransitionGroup
        enter-active-class="transition ease-out duration-300"
        enter-from-class="transform translate-x-full opacity-0"
        enter-to-class="transform translate-x-0 opacity-100"
        leave-active-class="transition ease-in duration-200"
        leave-from-class="transform translate-x-0 opacity-100"
        leave-to-class="transform translate-x-full opacity-0"
      >
        <div
          v-for="toast in notificationsStore.toasts"
          :key="toast.id"
          :class="[
            'flex items-start gap-3 p-4 rounded-lg border shadow-lg',
            getToastColors(toast.type).bg,
            getToastColors(toast.type).border,
          ]"
          role="alert"
        >
          <component
            :is="getToastIcon(toast.type)"
            :class="['w-5 h-5 flex-shrink-0 mt-0.5', getToastColors(toast.type).icon]"
          />
          
          <p
            :class="['flex-1 text-sm font-medium', getToastColors(toast.type).text]"
          >
            {{ toast.message }}
          </p>

          <button
            @click="notificationsStore.removeToast(toast.id)"
            :class="[
              'flex-shrink-0 p-0.5 rounded hover:bg-black hover:bg-opacity-10 transition-colors',
              getToastColors(toast.type).icon,
            ]"
            aria-label="Close notification"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>