<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseModal from '@/components/common/BaseModal.vue';
import apiClient, { handleApiError } from '@/api/client';
import type { SoftwareResponse } from '@/api/api';
import { AlertCircle, FileCheck } from 'lucide-vue-next';

interface ProcessingFile {
  filename: string;
  size: number;
  sha256: string;
}

interface Props {
  show: boolean;
  file?: ProcessingFile | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
  success: [];
}>();

const { t } = useI18n();

const form = ref({
  software_id: 0,
  version: '',
  filename: '',
  file_size: 0,
  sha256_hash: '',
  architecture: '',
  platform: '',
  notes: '',
});

const softwareList = ref<SoftwareResponse[]>([]);
const isSubmitting = ref(false);
const error = ref<string | null>(null);

const architectures = ['x86', 'x64', 'arm64', 'universal'];
const platforms = ['Windows', 'Linux', 'macOS', 'Cross-platform'];

const fetchSoftwareList = async () => {
  try {
    const response = await apiClient.software.listSoftware(1, 100);
    softwareList.value = response.data.items || [];
  } catch (err) {
    console.error('Error fetching software list:', err);
  }
};

watch(() => props.show, (show) => {
  if (show && props.file) {
    // Populate with file data
    form.value = {
      software_id: 0,
      version: '',
      filename: props.file.filename,
      file_size: props.file.size,
      sha256_hash: props.file.sha256,
      architecture: '',
      platform: '',
      notes: '',
    };
  } else if (show) {
    // Reset form
    form.value = {
      software_id: 0,
      version: '',
      filename: '',
      file_size: 0,
      sha256_hash: '',
      architecture: '',
      platform: '',
      notes: '',
    };
  }
  error.value = null;
});

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
};

const handleSubmit = async () => {
  // Validation
  if (!form.value.software_id || form.value.software_id <= 0) {
    error.value = t('installers.register.selectSoftware');
    return;
  }

  if (!form.value.version || form.value.version.trim().length === 0) {
    error.value = t('installers.register.version') + ' is required';
    return;
  }

  if (!form.value.filename || !form.value.sha256_hash) {
    error.value = 'Invalid file data';
    return;
  }

  isSubmitting.value = true;
  error.value = null;

  try {
    await apiClient.installers.registerInstaller({
      software_id: form.value.software_id,
      version: form.value.version.trim(),
      filename: form.value.filename,
      file_size: form.value.file_size,
      sha256_hash: form.value.sha256_hash,
      architecture: form.value.architecture || undefined,
      platform: form.value.platform || undefined,
      notes: form.value.notes || undefined,
    });

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
    :title="t('installers.register.title')"
    size="lg"
    @close="emit('close')"
  >
    <!-- File info banner -->
    <div v-if="file" class="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-start gap-3">
      <FileCheck class="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-blue-900">{{ file.filename }}</p>
        <p class="text-sm text-blue-700 mt-1">
          Size: {{ formatFileSize(file.size) }} | SHA-256: <code class="text-xs">{{ file.sha256.substring(0, 16) }}...</code>
        </p>
      </div>
    </div>

    <!-- Error message -->
    <div v-if="error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
      <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <p class="text-sm text-red-800">{{ error }}</p>
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Software Selection -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('installers.register.software') }} *
        </label>
        <select
          v-model="form.software_id"
          required
          class="input-field"
        >
          <option :value="0">{{ t('installers.register.selectSoftware') }}</option>
          <option v-for="sw in softwareList" :key="sw.id" :value="sw.id">
            {{ sw.name }} - {{ sw.vendor }}
          </option>
        </select>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Version -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ t('installers.register.version') }} *
          </label>
          <input
            v-model="form.version"
            type="text"
            required
            maxlength="50"
            class="input-field"
            :placeholder="t('installers.register.versionPlaceholder')"
          />
        </div>

        <!-- Architecture -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ t('installers.register.architecture') }}
          </label>
          <select v-model="form.architecture" class="input-field">
            <option value="">Select architecture</option>
            <option v-for="arch in architectures" :key="arch" :value="arch">
              {{ arch }}
            </option>
          </select>
        </div>
      </div>

      <!-- Platform -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('installers.register.platform') }}
        </label>
        <select v-model="form.platform" class="input-field">
          <option value="">Select platform</option>
          <option v-for="plat in platforms" :key="plat" :value="plat">
            {{ plat }}
          </option>
        </select>
      </div>

      <!-- File Details (Read-only) -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ t('installers.register.filename') }}
          </label>
          <input
            v-model="form.filename"
            type="text"
            readonly
            class="input-field bg-gray-100 text-sm"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ t('installers.register.filesize') }}
          </label>
          <input
            :value="formatFileSize(form.file_size)"
            type="text"
            readonly
            class="input-field bg-gray-100"
          />
        </div>
      </div>

      <!-- SHA-256 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('installers.register.sha256') }}
        </label>
        <input
          v-model="form.sha256_hash"
          type="text"
          readonly
          class="input-field bg-gray-100 font-mono text-xs"
        />
      </div>

      <!-- Notes -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('installers.register.notes') }}
        </label>
        <textarea
          v-model="form.notes"
          rows="3"
          class="input-field"
          :placeholder="t('installers.register.notesPlaceholder')"
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
          <span v-if="isSubmitting">{{ t('installers.register.registering') }}</span>
          <span v-else>{{ t('installers.register.register') }}</span>
        </button>
      </div>
    </template>
  </BaseModal>
</template>