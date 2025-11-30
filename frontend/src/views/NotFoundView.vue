<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { AlertCircle } from 'lucide-vue-next';

const router = useRouter();
const { t } = useI18n();
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 px-4">
    <div class="text-center">
      <AlertCircle class="w-24 h-24 text-gray-400 mx-auto mb-6" />
      <h1 class="text-6xl font-bold text-gray-900 mb-4">404</h1>
      <h2 class="text-2xl font-semibold text-gray-700 mb-2">{{ t('errors.notFound.title') }}</h2>
      <p class="text-lg text-gray-600 mb-8">
        {{ t('errors.notFound.message') }}
      </p>
      <button @click="router.push('/dashboard')" class="btn-primary">
        {{ t('errors.notFound.backToDashboard') }}
      </button>
    </div>
  </div>
</template>