<script setup lang="ts">
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseModal from '@/components/common/BaseModal.vue';
import apiClient, { handleApiError } from '@/api/client';
import { AlertTriangle, Copy, Check, Eye, EyeOff } from 'lucide-vue-next';

interface Props {
  show: boolean;
  licenseId: number | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n();

const licenseKey = ref('');
const isLoading = ref(false);
const error = ref<string | null>(null);
const isCopied = ref(false);
const showKey = ref(false);

watch(() => props.show, async (show) => {
  if (show && props.licenseId) {
    await fetchLicenseKey();
  } else {
    // Reset state
    licenseKey.value = '';
    error.value = null;
    showKey.value = false;
    isCopied.value = false;
  }
});

const fetchLicenseKey = async () => {
  if (!props.licenseId) return;

  isLoading.value = true;
  error.value = null;

  try {
    const response = await apiClient.licenses.getLicense(props.licenseId);
    // The license_key is only returned in the detail endpoint (decrypted)
    licenseKey.value = (response.data as any).license_key || '';
  } catch (err) {
    const apiError = handleApiError(err);
    error.value = apiError.message;
  } finally {
    isLoading.value = false;
  }
};

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(licenseKey.value);
    isCopied.value = true;
    setTimeout(() => {
      isCopied.value = false;
    }, 2000);
  } catch (err) {
    console.error('Failed to copy:', err);
  }
};

const toggleShowKey = () => {
  showKey.value = !showKey.value;
};

const maskedKey = (key: string): string => {
  if (key.length <= 8) return '••••••••';
  const start = key.substring(0, 4);
  const end = key.substring(key.length - 4);
  return `${start}${'•'.repeat(key.length - 8)}${end}`;
};
</script>

<template>
  <BaseModal
    :show="show"
    :title="t('licenses.view.title')"
    size="md"
    @close="emit('close')"
  >
    <!-- Security warning -->
    <div class="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
      <AlertTriangle class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
      <div>
        <p class="text-sm font-medium text-amber-900">{{ t('licenses.view.warning') }}</p>
        <p class="text-xs text-amber-800 mt-1">
          This access will be logged in the audit system with your user ID and IP address.
        </p>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="flex items-center justify-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
      <p class="text-sm text-red-800">{{ error }}</p>
    </div>

    <!-- License key display -->
    <div v-else-if="licenseKey">
      <div>
        <div class="flex items-center justify-between mb-2">
          <label class="block text-sm font-medium text-gray-700">
            {{ t('licenses.view.licenseKey') }}
          </label>
          <button
            @click="toggleShowKey"
            class="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
          >
            <component :is="showKey ? EyeOff : Eye" class="w-4 h-4" />
            <span>{{ showKey ? 'Hide' : 'Show' }}</span>
          </button>
        </div>

        <div class="relative">
          <textarea
            :value="showKey ? licenseKey : maskedKey(licenseKey)"
            readonly
            rows="4"
            class="input-field font-mono text-sm resize-none"
            :class="{ 'tracking-widest': !showKey }"
          />
          
          <button
            @click="copyToClipboard"
            class="absolute top-2 right-2 p-2 rounded-md hover:bg-gray-100 transition-colors"
            :title="t('licenses.view.copy')"
          >
            <Check v-if="isCopied" class="w-5 h-5 text-green-600" />
            <Copy v-else class="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <p v-if="isCopied" class="text-sm text-green-600 mt-2">
          ✓ {{ t('licenses.view.copied') }}
        </p>
      </div>

      <!-- Additional info -->
      <div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p class="text-xs text-blue-900">
          <strong>Security Note:</strong> This license key is stored encrypted with AES-GCM. 
          It has been decrypted temporarily for viewing.
        </p>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-end">
        <button
          @click="emit('close')"
          class="btn-secondary"
        >
          {{ t('licenses.view.close') }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>