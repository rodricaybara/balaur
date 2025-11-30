<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { ShieldX } from 'lucide-vue-next';

const router = useRouter();
const { t } = useI18n();
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 px-4">
    <div class="text-center">
      <ShieldX class="w-24 h-24 text-red-500 mx-auto mb-6" />
      <h1 class="text-4xl font-bold text-gray-900 mb-4">{{ t('errors.forbidden.title') }}</h1>
      <p class="text-lg text-gray-600 mb-8">
        {{ t('errors.forbidden.message') }}
      </p>
      <button @click="router.push('/dashboard')" class="btn-primary">
        {{ t('errors.forbidden.backToDashboard') }}
      </button>
    </div>
  </div>
</template>