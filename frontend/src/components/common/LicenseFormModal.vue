<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseModal from '@/components/common/BaseModal.vue';
import apiClient, { handleApiError } from '@/api/client';
import type { LicenseResponse, SoftwareResponse } from '@/api/api';
import { AlertCircle, Shield } from 'lucide-vue-next';

interface Props {
  show: boolean;
  license?: LicenseResponse | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
  success: [];
}>();

const { t } = useI18n();

const form = ref({
  software_id: 0,
  license_key: '',
  license_type: 'perpetual' as 'perpetual' | 'subscription' | 'volume' | 'oem' | 'educational' | 'trial',
  max_activations: null as number | null,
  expiration_date: '',
  notes: '',
});

const softwareList = ref<SoftwareResponse[]>([]);
const isSubmitting = ref(false);
const error = ref<string | null>(null);

const isEditMode = computed(() => !!props.license);

const licenseTypes = [
  { value: 'perpetual', label: t('licenses.types.perpetual') },
  { value: 'subscription', label: t('licenses.types.subscription') },
  { value: 'volume', label: t('licenses.types.volume') },
  { value: 'oem', label: t('licenses.types.oem') },
  { value: 'educational', label: t('licenses.types.educational') },
  { value: 'trial', label: t('licenses.types.trial') },
];

const fetchSoftwareList = async () => {
  try {
    const response = await apiClient.software.listSoftware(1, 100);
    softwareList.value = response.data.items || [];
  } catch (err) {
    console.error('Error fetching software list:', err);
  }
};

watch(() => props.show, (show) => {
  if (show && props.license) {
    // Edit mode: populate form
    form.value = {
      software_id: props.license.software_id,
      license_key: '', // Don't show existing key for security
      license_type: props.license.license_type as any,
      max_activations: props.license.max_activations,
      expiration_date: props.license.expiration_date || '',
      notes: props.license.notes || '',
    };
  } else if (show) {
    // Create mode: reset form
    form.value = {
      software_id: 0,
      license_key: '',
      license_type: 'perpetual',
      max_activations: null,
      expiration_date: '',
      notes: '',
    };
  }
  error.value = null;
});

const handleSubmit = async () => {
  // Validation
  if (!form.value.software_id || form.value.software_id <= 0) {
    error.value = 'Please select a software';
    return;
  }

  if (!isEditMode.value && !form.value.license_key) {
    error.value = 'License key is required';
    return;
  }

  isSubmitting.value = true;
  error.value = null;

  try {
    if (isEditMode.value && props.license) {
      // Update license
      await apiClient.licenses.updateLicense(props.license.id, {
        license_type: form.value.license_type,
        license_key: form.value.license_key || undefined,
        max_activations: form.value.max_activations || undefined,
        expiration_date: form.value.expiration_date || undefined,
        notes: form.value.notes || undefined,
      });
    } else {
      // Create license
      await apiClient.licenses.createLicense({
        software_id: form.value.software_id,
        license_type: form.value.license_type,
        license_key: form.value.license_key,
        max_activations: form.value.max_activations || undefined,
        expiration_date: form.value.expiration_date || undefined,
        notes: form.value.notes || undefined,
      });
    }

    emit('success');
    emit('close');
  } catch (err) {
    const apiError = handleApiError(err);
    error.value = apiError.message;
  } finally {
    isSubmitting.value = false;
  }
};

onMounted(() => {
  fetchSoftwareList();
});
</script>

<template>
  <BaseModal
    :show="show"
    :title="isEditMode ? t('licenses.form.title') : t('licenses.newLicense')"
    size="md"
    @close="emit('close')"
  >
    <!-- Security warning -->
    <div class="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
      <Shield class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
      <p class="text-sm text-amber-800">{{ t('licenses.security.warning') }}</p>
    </div>

    <!-- Error message -->
    <div v-if="error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
      <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <p class="text-sm text-red-800">{{ error }}</p>
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Software -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('licenses.form.software') }} *
        </label>
        <select
          v-model="form.software_id"
          required
          :disabled="isEditMode"
          class="input-field"
          :class="{ 'bg-gray-100': isEditMode }"
        >
          <option :value="0">{{ t('licenses.form.selectSoftware') }}</option>
          <option v-for="sw in softwareList" :key="sw.id" :value="sw.id">
            {{ sw.name }} ({{ sw.vendor }})
          </option>
        </select>
        <p v-if="isEditMode" class="text-xs text-gray-500 mt-1">
          Software cannot be changed
        </p>
      </div>

      <!-- License Key -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('licenses.form.licenseKey') }} {{ isEditMode ? '' : '*' }}
        </label>
        <textarea
          v-model="form.license_key"
          :required="!isEditMode"
          rows="3"
          class="input-field font-mono text-sm"
          :placeholder="isEditMode ? 'Leave empty to keep current key' : ''"
        />
        <p class="text-xs text-gray-500 mt-1">
          {{ isEditMode ? 'Enter new key only if changing' : 'This key will be encrypted with AES-GCM' }}
        </p>
      </div>

      <!-- License Type -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('licenses.form.licenseType') }} *
        </label>
        <select v-model="form.license_type" required class="input-field">
          <option v-for="type in licenseTypes" :key="type.value" :value="type.value">
            {{ type.label }}
          </option>
        </select>
      </div>

      <!-- Max Activations -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('licenses.form.maxActivations') }}
        </label>
        <input
          v-model.number="form.max_activations"
          type="number"
          min="1"
          class="input-field"
          placeholder="Leave empty for unlimited"
        />
      </div>

      <!-- Expiration Date -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('licenses.form.expirationDate') }}
        </label>
        <input
          v-model="form.expiration_date"
          type="date"
          class="input-field"
        />
      </div>

      <!-- Notes -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('licenses.form.notes') }}
        </label>
        <textarea
          v-model="form.notes"
          rows="3"
          class="input-field"
        />
      </div>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-3">
        <button
          type="button"
          @click="emit('close')"
          class="btn-secondary"
          :disabled="isSubmitting"
        >
          {{ t('licenses.form.cancel') }}
        </button>
        <button
          type="submit"
          @click="handleSubmit"
          class="btn-primary"
          :disabled="isSubmitting"
        >
          <span v-if="isSubmitting">{{ t('common.loading') }}</span>
          <span v-else>{{ t('licenses.form.save') }}</span>
        </button>
      </div>
    </template>
  </BaseModal>
</template>