<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseModal from '@/components/common/BaseModal.vue';
import apiClient, { handleApiError } from '@/api/client';
import type { SoftwareResponse } from '@/api/api';
import { AlertCircle } from 'lucide-vue-next';

interface Props {
  show: boolean;
  software?: SoftwareResponse | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
  success: [];
}>();

const { t } = useI18n();

const form = ref({
  name: '',
  vendor: '',
  category: '',
  description: '',
  website: '',
});

const isSubmitting = ref(false);
const error = ref<string | null>(null);

const isEditMode = computed(() => !!props.software);

// Common categories (can be customized)
const commonCategories = [
  'Development',
  'Design',
  'Productivity',
  'Security',
  'Database',
  'Communication',
  'Education',
  'Utilities',
  'Other',
];

watch(() => props.show, (show) => {
  if (show && props.software) {
    // Edit mode: populate form
    form.value = {
      name: props.software.name,
      vendor: props.software.vendor,
      category: props.software.category,
      description: props.software.description || '',
      website: props.software.website || '',
    };
  } else if (show) {
    // Create mode: reset form
    form.value = {
      name: '',
      vendor: '',
      category: '',
      description: '',
      website: '',
    };
  }
  error.value = null;
});

const handleSubmit = async () => {
  // Validation
  if (!form.value.name || !form.value.vendor || !form.value.category) {
    error.value = 'Name, vendor and category are required';
    return;
  }

  // Validate URL if provided
  if (form.value.website) {
    try {
      new URL(form.value.website);
    } catch {
      error.value = 'Invalid website URL';
      return;
    }
  }

  isSubmitting.value = true;
  error.value = null;

  try {
    if (isEditMode.value && props.software) {
      // Update software
      await apiClient.software.updateSoftware(props.software.id, {
        name: form.value.name,
        vendor: form.value.vendor,
        category: form.value.category,
        description: form.value.description || undefined,
        website: form.value.website || undefined,
      });
    } else {
      // Create software
      await apiClient.software.createSoftware({
        name: form.value.name,
        vendor: form.value.vendor,
        category: form.value.category,
        description: form.value.description || undefined,
        website: form.value.website || undefined,
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
</script>

<template>
  <BaseModal
    :show="show"
    :title="isEditMode ? t('softwareDetail.edit') : t('software.newSoftware')"
    size="md"
    @close="emit('close')"
  >
    <!-- Error message -->
    <div v-if="error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
      <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <p class="text-sm text-red-800">{{ error }}</p>
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Name -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('software.title') }} *
        </label>
        <input
          v-model="form.name"
          type="text"
          required
          maxlength="200"
          class="input-field"
          placeholder="e.g., Adobe Photoshop"
        />
      </div>

      <!-- Vendor -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('software.vendor') }} *
        </label>
        <input
          v-model="form.vendor"
          type="text"
          required
          maxlength="200"
          class="input-field"
          placeholder="e.g., Adobe Inc."
        />
      </div>

      <!-- Category -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('software.category') }} *
        </label>
        <div class="flex gap-2">
          <select
            v-model="form.category"
            required
            class="input-field flex-1"
          >
            <option value="">{{ t('software.allCategories') }}</option>
            <option v-for="cat in commonCategories" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>
          <input
            v-if="form.category === 'Other'"
            v-model="form.category"
            type="text"
            placeholder="Custom category"
            class="input-field flex-1"
          />
        </div>
      </div>

      <!-- Website -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('softwareDetail.overview.website') }}
        </label>
        <input
          v-model="form.website"
          type="url"
          class="input-field"
          placeholder="https://example.com"
        />
      </div>

      <!-- Description -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('softwareDetail.overview.description') }}
        </label>
        <textarea
          v-model="form.description"
          rows="4"
          class="input-field"
          placeholder="Describe the software purpose, features, and requirements..."
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
          {{ t('common.cancel') }}
        </button>
        <button
          type="submit"
          @click="handleSubmit"
          class="btn-primary"
          :disabled="isSubmitting"
        >
          <span v-if="isSubmitting">{{ t('common.loading') }}</span>
          <span v-else>{{ t('common.save') }}</span>
        </button>
      </div>
    </template>
  </BaseModal>
</template>