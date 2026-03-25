<!-- Fichero: frontend/src/components/common/InstallerUploadModal.vue -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import BaseModal from '@/components/common/BaseModal.vue'
import { useInstallersStore } from '@/stores/installers'
import { handleApiError } from '@/api/client'
import { UploadCloud, FileCheck, AlertCircle, X } from 'lucide-vue-next'

interface Props {
  show: boolean
}
const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  uploaded: [result: { filename: string; sha256: string; size: number; size_mb: number }]
}>()

const { t } = useI18n()
const store = useInstallersStore()

const ALLOWED_EXTENSIONS = ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm', '.AppImage', '.zip', '.tar.gz']
const MAX_SIZE_BYTES = 1073741824  // 1 GB — debe coincidir con web_upload_max_size del backend

const isDragging = ref(false)
const selectedFile = ref<File | null>(null)
const uploadProgress = ref(0)
const isUploading = ref(false)
const error = ref<string | null>(null)

const fileIsValid = computed(() => {
  if (!selectedFile.value) return false
  const name = selectedFile.value.name
  const hasValidExt = ALLOWED_EXTENSIONS.some(ext => name.toLowerCase().endsWith(ext))
  const hasValidSize = selectedFile.value.size <= MAX_SIZE_BYTES
  return hasValidExt && hasValidSize
})

const fileSizeMb = computed(() =>
  selectedFile.value ? (selectedFile.value.size / (1024 * 1024)).toFixed(1) : '0'
)

const validationError = computed(() => {
  if (!selectedFile.value) return null
  const name = selectedFile.value.name
  if (!ALLOWED_EXTENSIONS.some(ext => name.toLowerCase().endsWith(ext))) {
    return t('installers.upload.errorExtension', { exts: ALLOWED_EXTENSIONS.join(', ') })
  }
  if (selectedFile.value.size > MAX_SIZE_BYTES) {
    return t('installers.upload.errorSize')
  }
  return null
})

const onDragOver = (e: DragEvent) => { e.preventDefault(); isDragging.value = true }
const onDragLeave = () => { isDragging.value = false }
const onDrop = (e: DragEvent) => {
  e.preventDefault()
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) selectFile(file)
}
const onFileInput = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) selectFile(file)
}
const selectFile = (file: File) => {
  selectedFile.value = file
  error.value = null
  uploadProgress.value = 0
}
const clearFile = () => {
  selectedFile.value = null
  error.value = null
  uploadProgress.value = 0
}

const handleUpload = async () => {
  if (!selectedFile.value || !fileIsValid.value) return
  isUploading.value = true
  error.value = null
  uploadProgress.value = 0

  try {
    const result = await store.uploadFile(selectedFile.value, (pct) => {
      uploadProgress.value = pct
    })
    emit('uploaded', result)
    emit('close')
    clearFile()
  } catch (err) {
    error.value = handleApiError(err).message
  } finally {
    isUploading.value = false
  }
}

const handleClose = () => {
  if (isUploading.value) return  // no cerrar durante la subida
  clearFile()
  emit('close')
}
</script>

<template>
  <BaseModal :show="show" :title="t('installers.upload.title')" @close="handleClose">

    <!-- Error banner -->
    <div v-if="error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
      <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <p class="text-sm text-red-800">{{ error }}</p>
    </div>

    <!-- Drop zone -->
    <div
      v-if="!selectedFile"
      class="border-2 border-dashed rounded-lg p-10 text-center transition-colors cursor-pointer"
      :class="isDragging
        ? 'border-primary-500 bg-primary-50'
        : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
      @click="($refs.fileInput as HTMLInputElement).click()"
    >
      <UploadCloud class="w-12 h-12 mx-auto mb-3 text-gray-400" />
      <p class="text-sm font-medium text-gray-700">{{ t('installers.upload.dropZoneTitle') }}</p>
      <p class="text-xs text-gray-500 mt-1">{{ t('installers.upload.dropZoneHint') }}</p>
      <p class="text-xs text-gray-400 mt-2">{{ ALLOWED_EXTENSIONS.join('  ') }}</p>
      <input ref="fileInput" type="file" class="hidden" @change="onFileInput" />
    </div>

    <!-- Fichero seleccionado -->
    <div v-else class="space-y-4">
      <div class="flex items-start gap-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <FileCheck class="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-gray-900 truncate">{{ selectedFile.name }}</p>
          <p class="text-xs text-gray-500">{{ fileSizeMb }} MB</p>
        </div>
        <button
          v-if="!isUploading"
          @click="clearFile"
          class="text-gray-400 hover:text-gray-600"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <!-- Error de validación local -->
      <div v-if="validationError" class="p-3 bg-amber-50 border border-amber-200 rounded-lg">
        <p class="text-sm text-amber-800">{{ validationError }}</p>
      </div>

      <!-- Barra de progreso -->
      <div v-if="isUploading" class="space-y-1">
        <div class="flex justify-between text-xs text-gray-600">
          <span>{{ t('installers.upload.uploading') }}</span>
          <span>{{ uploadProgress }}%</span>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div
            class="bg-primary-600 h-2 rounded-full transition-all duration-200"
            :style="{ width: `${uploadProgress}%` }"
          />
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-end gap-3">
        <button
          type="button"
          @click="handleClose"
          class="btn-secondary"
          :disabled="isUploading"
        >
          {{ t('common.cancel') }}
        </button>
        <button
          type="button"
          @click="handleUpload"
          class="btn-primary"
          :disabled="!fileIsValid || isUploading"
        >
          <span v-if="isUploading">{{ t('installers.upload.uploading') }}…</span>
          <span v-else>{{ t('installers.upload.submit') }}</span>
        </button>
      </div>
    </template>

  </BaseModal>
</template>