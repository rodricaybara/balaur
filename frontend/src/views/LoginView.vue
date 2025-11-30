<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { useBranding } from '@/composables/useBranding';
import LanguageSelector from '@/components/common/LanguageSelector.vue';
import { Lock, User, AlertCircle } from 'lucide-vue-next';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const { t } = useI18n();
const { getAppName, getFooterText, getLoginBackground } = useBranding();

const username = ref('');
const password = ref('');
const isSubmitting = ref(false);

const loginBackground = computed(() => getLoginBackground());

const handleLogin = async () => {
  if (!username.value || !password.value) {
    return;
  }

  isSubmitting.value = true;
  authStore.clearError();

  try {
    await authStore.login({
      username: username.value,
      password: password.value,
    });

    const redirect = (route.query.redirect as string) || '/dashboard';
    router.push(redirect);
  } catch (error) {
    console.error('Login failed:', error);
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div 
    :class="[
      'min-h-screen flex items-center justify-center px-4',
      loginBackground.background === 'gradient' ? 'login-gradient-bg' : 'bg-gray-100'
    ]"
  >
    <div class="max-w-md w-full">
      <!-- Language selector (top right) -->
      <div class="flex justify-end mb-4">
        <LanguageSelector />
      </div>

      <!-- Logo y título -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-white rounded-full mb-4 shadow-lg">
          <svg class="w-10 h-10 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
          </svg>
        </div>
        <h1 class="text-3xl font-bold text-white mb-2">
          {{ getAppName() }}
        </h1>
        <p class="text-primary-100">
          {{ t('auth.login.subtitle') }}
        </p>
      </div>

      <!-- Card de login -->
      <div class="card">
        <h2 class="text-2xl font-semibold text-gray-900 mb-6">
          {{ t('auth.login.title') }}
        </h2>

        <!-- Error message -->
        <div
          v-if="authStore.error"
          class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3"
        >
          <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div class="flex-1">
            <p class="text-sm font-medium text-red-800">
              {{ t('auth.login.error') }}
            </p>
            <p class="text-sm text-red-700 mt-1">{{ authStore.error }}</p>
          </div>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleLogin" class="space-y-4">
          <!-- Username -->
          <div>
            <label for="username" class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('auth.login.username') }}
            </label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User class="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="username"
                v-model="username"
                type="text"
                required
                autocomplete="username"
                class="input-field pl-10"
                :placeholder="t('auth.login.usernamePlaceholder')"
                :disabled="isSubmitting"
              />
            </div>
          </div>

          <!-- Password -->
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('auth.login.password') }}
            </label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock class="h-5 w-5 text-gray-400" />
              </div>
              <input
                id="password"
                v-model="password"
                type="password"
                required
                autocomplete="current-password"
                class="input-field pl-10"
                :placeholder="t('auth.login.passwordPlaceholder')"
                :disabled="isSubmitting"
              />
            </div>
          </div>

          <!-- Submit button -->
          <button
            type="submit"
            class="btn-primary w-full flex items-center justify-center gap-2"
            :disabled="isSubmitting || !username || !password"
          >
            <span v-if="isSubmitting">
              <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ t('auth.login.signingIn') }}
            </span>
            <span v-else>{{ t('auth.login.signIn') }}</span>
          </button>
        </form>

        <!-- Info adicional -->
        <div class="mt-6 pt-6 border-t border-gray-200">
          <p class="text-xs text-gray-500 text-center">
            {{ t('auth.login.helpText') }}
          </p>
        </div>
      </div>

      <!-- Footer -->
      <p class="mt-8 text-center text-sm text-primary-100">
        {{ getFooterText() }}
      </p>
    </div>
  </div>
</template>