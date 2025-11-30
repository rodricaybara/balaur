<script setup lang="ts">
import { onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import AppToast from '@/components/common/AppToast.vue';

const authStore = useAuthStore();
const router = useRouter();

onMounted(async () => {
  // Verificar autenticación al iniciar la app
  if (authStore.accessToken) {
    await authStore.checkAuth();
  }
});
</script>

<template>
  <div id="app" class="min-h-screen bg-gray-50">
    <RouterView />
    <AppToast />
  </div>
</template>