<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { useInstallersStore } from '@/stores/installers';
import { useSoftwareStore } from '@/stores/software';
import AppLayout from '@/components/layout/AppLayout.vue';
import InstallerRegisterModal from '@/components/common/InstallerRegisterModal.vue';
import DeleteConfirmModal from '@/components/common/DeleteConfirmModal.vue';
import InstallerUploadModal from '@/components/common/InstallerUploadModal.vue';
import type { InstallerResponse } from '@/api/api';
import {
  Upload,
  Download,
  Trash2,
  FolderUp,
  FileCheck,
  Clock,
  Server,
  HardDrive,
  Info,
  Loader2,
  Plus,
  X,
} from 'lucide-vue-next';

const authStore = useAuthStore();
const installersStore = useInstallersStore();
const softwareStore = useSoftwareStore();
const { t } = useI18n();

const activeTab = ref<'pending' | 'processing' | 'repository'>('repository');

// Modal: subida web (managers y admins)
const showUploadModal = ref(false);
// Modal: instrucciones FTP (solo admins, para ficheros > 1 GB)
const showFtpInfoModal = ref(false);

const showRegisterModal = ref(false);
const showDeleteModal = ref(false);
const selectedFile = ref<any | null>(null);
const selectedInstaller = ref<InstallerResponse | null>(null);

// FTP config
const ftpConfig = computed(() => ({
  server: import.meta.env.VITE_FTP_SERVER || '10.227.xxx.yyy',
  path: '/inbox/pending/',
  port: 21,
}));

// ✅ Cargar todos los installers de forma eficiente
const fetchAllInstallers = async () => {
  await softwareStore.fetchSoftwareList();

  const allInstallers: InstallerResponse[] = [];

  for (const software of softwareStore.softwareList) {
    try {
      await softwareStore.fetchSoftwareDetail(software.id);
      if ('installers' in (softwareStore.currentSoftware ?? {})) {
        allInstallers.push(
          ...(('installers' in (softwareStore.currentSoftware ?? {}))
            ? (softwareStore.currentSoftware as any).installers
            : [])
        );
      }
    } catch (err) {
      console.warn(`Failed to fetch installers for software ${software.id}`, err);
    }
  }

  installersStore.installersList = allInstallers;
};

const fetchWatcherStats = async () => {
  await installersStore.fetchWatcherStats();
};

// Cargar datos al cambiar de tab
watch(activeTab, async (newTab) => {
  if (newTab === 'pending') {
    await installersStore.fetchPendingFiles();
  } else if (newTab === 'processing') {
    await installersStore.fetchProcessingFiles();
  } else if (newTab === 'repository') {
    await fetchAllInstallers();
  }
}, { immediate: false });

// Abrir modal de registro con archivo preseleccionado
const openRegisterModal = (file: any) => {
  selectedFile.value = {
    filename: file.filename,
    size: file.size,
    sha256: file.sha256,
  };
  showRegisterModal.value = true;
};

const handleRegisterSuccess = async () => {
  showRegisterModal.value = false;
  selectedFile.value = null;
  await fetchAllInstallers();
  await fetchWatcherStats();
};

const downloadInstaller = async (installerId: number) => {
  try {
    await installersStore.downloadInstaller(installerId);
  } catch (err) {
    console.error('Error downloading installer:', err);
  }
};

const handleDeleteInstaller = (installer: InstallerResponse) => {
  selectedInstaller.value = installer;
  showDeleteModal.value = true;
};

const handleDeleteConfirm = async () => {
  if (!selectedInstaller.value) return;
  try {
    await installersStore.deleteInstaller(
      selectedInstaller.value.id,
      selectedInstaller.value.software_id
    );
    showDeleteModal.value = false;
    selectedInstaller.value = null;
    await fetchAllInstallers();
  } catch (err) {
    console.error('Error deleting installer:', err);
  }
};

// Tras subida web exitosa: ir al tab processing y refrescar
const onFileUploaded = async (result: {
  filename: string;
  sha256: string;
  size: number;
  size_mb: number;
}) => {
  activeTab.value = 'processing';
  await installersStore.fetchProcessingFiles();
  await fetchWatcherStats();
};

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
};

const formatDate = (dateString: string | null): string => {
  if (!dateString) return '—';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

let watcherIntervalId: number | null = null;

onMounted(async () => {
  await fetchAllInstallers();
  await fetchWatcherStats();
  watcherIntervalId = window.setInterval(fetchWatcherStats, 30000);
});

onBeforeUnmount(() => {
  if (watcherIntervalId !== null) {
    clearInterval(watcherIntervalId);
    watcherIntervalId = null;
  }
});
</script>

<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto">

      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">{{ t('installers.title') }}</h1>
          <p class="text-gray-600 mt-1">{{ t('installers.subtitle') }}</p>
        </div>

        <!-- Botones de acción -->
        <div class="flex items-center gap-3">
          <!-- Botón FTP — solo admins, ficheros > 1 GB -->
          <button
            v-if="authStore.isAdmin"
            @click="showFtpInfoModal = true"
            class="btn-secondary flex items-center gap-2"
            :title="t('installers.ftp.buttonTitle')"
          >
            <Server class="w-4 h-4" />
            <span>{{ t('installers.ftp.button') }}</span>
          </button>

          <!-- Botón subida web — managers y admins -->
          <button
            v-if="authStore.canManageSoftware"
            @click="showUploadModal = true"
            class="btn-primary flex items-center gap-2"
          >
            <Upload class="w-4 h-4" />
            <span>{{ t('installers.upload.button') }}</span>
          </button>
        </div>
      </div>

      <!-- Watcher Status Card -->
      <div class="card mb-6 bg-blue-50 border-blue-200">
        <div class="flex items-start gap-4">
          <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
            <Server class="w-6 h-6 text-blue-600" />
          </div>
          <div class="flex-1">
            <h3 class="font-semibold text-gray-900 mb-2">{{ t('installers.watcher.title') }}</h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p class="text-gray-600">{{ t('common.status') }}</p>
                <p
                  class="font-medium"
                  :class="installersStore.watcherStats.is_running ? 'text-green-600' : 'text-red-600'"
                >
                  {{ installersStore.watcherStats.is_running
                    ? t('installers.watcher.running')
                    : t('installers.watcher.stopped') }}
                </p>
              </div>
              <div>
                <p class="text-gray-600">{{ t('installers.tabs.pending').replace(' ({count})', '') }}</p>
                <p class="font-medium text-gray-900">{{ installersStore.watcherStats.pending }}</p>
              </div>
              <div>
                <p class="text-gray-600">{{ t('installers.tabs.processing').replace(' ({count})', '') }}</p>
                <p class="font-medium text-gray-900">{{ installersStore.watcherStats.processing }}</p>
              </div>
              <div>
                <p class="text-gray-600">Interval</p>
                <p class="font-medium text-gray-900">{{ installersStore.watcherStats.interval_seconds }}s</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="border-b border-gray-200 mb-6">
        <nav class="-mb-px flex gap-6">
          <button
            @click="activeTab = 'repository'"
            :class="[
              'py-3 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'repository'
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            ]"
          >
            <div class="flex items-center gap-2">
              <HardDrive class="w-4 h-4" />
              <span>{{ t('installers.tabs.repository') }}</span>
              <span class="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-700">
                {{ installersStore.installersList.length }}
              </span>
            </div>
          </button>

          <button
            @click="activeTab = 'processing'"
            :class="[
              'py-3 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'processing'
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            ]"
          >
            <div class="flex items-center gap-2">
              <FileCheck class="w-4 h-4" />
              <span>{{ t('installers.tabs.processing', { count: installersStore.watcherStats.processing }) }}</span>
            </div>
          </button>

          <button
            @click="activeTab = 'pending'"
            :class="[
              'py-3 px-1 border-b-2 font-medium text-sm transition-colors',
              activeTab === 'pending'
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            ]"
          >
            <div class="flex items-center gap-2">
              <Clock class="w-4 h-4" />
              <span>{{ t('installers.tabs.pending', { count: installersStore.watcherStats.pending }) }}</span>
            </div>
          </button>
        </nav>
      </div>

      <!-- ==================== TAB: REPOSITORY ==================== -->
      <div v-if="activeTab === 'repository'">

        <!-- Loading -->
        <div v-if="installersStore.isLoading" class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>

        <!-- Empty state -->
        <div v-else-if="installersStore.installersList.length === 0" class="card text-center py-12">
          <Download class="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 class="text-lg font-medium text-gray-900 mb-2">
            {{ t('installers.list.noInstallers') }}
          </h3>
          <p class="text-gray-600 mb-4">
            {{ t('installers.list.uploadFirst') }}
          </p>
          <button
            v-if="authStore.canManageSoftware"
            @click="showUploadModal = true"
            class="btn-primary"
          >
            {{ t('installers.upload.button') }}
          </button>
        </div>

        <!-- Tabla -->
        <div v-else class="table-container">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {{ t('installers.list.name') }}
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {{ t('installers.list.version') }}
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {{ t('installers.list.size') }}
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {{ t('installers.list.platform') }}
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {{ t('installers.list.downloads') }}
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  {{ t('installers.list.actions') }}
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr
                v-for="installer in installersStore.installersList"
                :key="installer.id"
                class="hover:bg-gray-50"
              >
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm font-medium text-gray-900">{{ installer.filename }}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ installer.version }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ formatFileSize(installer.file_size) }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  <span v-if="installer.platform" class="px-2 py-1 bg-gray-100 rounded text-xs">
                    {{ installer.platform }}
                  </span>
                  <span v-else class="text-gray-400">—</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {{ installer.download_count || 0 }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                  <div class="flex items-center gap-2">
                    <button
                      @click="downloadInstaller(installer.id)"
                      class="text-primary-600 hover:text-primary-700"
                      :title="t('installers.list.download')"
                    >
                      <Download class="w-4 h-4" />
                    </button>
                    <button
                      v-if="authStore.isAdmin"
                      @click="handleDeleteInstaller(installer)"
                      class="text-red-600 hover:text-red-700"
                      :title="t('installers.list.delete')"
                    >
                      <Trash2 class="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ==================== TAB: PROCESSING ==================== -->
      <div v-if="activeTab === 'processing'" class="space-y-4">
        <div class="flex items-start gap-4 mb-6">
          <FileCheck class="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
          <div>
            <h3 class="font-semibold text-gray-900 mb-1">{{ t('installers.processing.title') }}</h3>
            <p class="text-sm text-gray-600">{{ t('installers.processing.description') }}</p>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="installersStore.isLoadingFiles" class="flex items-center justify-center py-8">
          <Loader2 class="w-8 h-8 text-primary-600 animate-spin" />
        </div>

        <!-- Empty state -->
        <div v-else-if="installersStore.processingFiles.length === 0" class="text-center py-8">
          <Info class="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p class="text-gray-600 text-sm">{{ t('installers.processing.noFiles') }}</p>
          <p class="text-gray-500 text-xs mt-2">{{ t('installers.processing.waitingFiles') }}</p>
        </div>

        <!-- Lista de ficheros -->
        <div v-else class="space-y-3">
          <div
            v-for="file in installersStore.processingFiles"
            :key="file.filename"
            class="card p-4 hover:shadow-md transition-shadow"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex items-start gap-3 flex-1 min-w-0">
                <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileCheck class="w-6 h-6 text-green-600" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="font-medium text-gray-900 truncate mb-2">{{ file.filename }}</p>
                  <div class="flex items-center gap-4 text-sm text-gray-500 mb-2">
                    <span>{{ formatFileSize(file.size) }}</span>
                    <span>•</span>
                    <span>{{ formatDate(file.validated_date) }}</span>
                  </div>
                  <div class="flex items-start gap-2">
                    <span class="text-xs text-gray-500 flex-shrink-0">SHA-256:</span>
                    <code class="text-xs text-gray-600 font-mono break-all">
                      {{ file.sha256.substring(0, 32) }}…
                    </code>
                  </div>
                </div>
              </div>
              <div class="flex-shrink-0">
                <button
                  @click="openRegisterModal(file)"
                  class="btn-primary flex items-center gap-2"
                >
                  <Plus class="w-4 h-4" />
                  <span>{{ t('installers.register.register') }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ==================== TAB: PENDING ==================== -->
      <div v-if="activeTab === 'pending'" class="space-y-4">
        <div class="flex items-start gap-4 mb-6">
          <Clock class="w-6 h-6 text-yellow-600 flex-shrink-0 mt-1" />
          <div>
            <h3 class="font-semibold text-gray-900 mb-1">{{ t('installers.pending.title') }}</h3>
            <p class="text-sm text-gray-600">{{ t('installers.pending.description') }}</p>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="installersStore.isLoadingFiles" class="flex items-center justify-center py-8">
          <Loader2 class="w-8 h-8 text-primary-600 animate-spin" />
        </div>

        <!-- Empty state -->
        <div v-else-if="installersStore.pendingFiles.length === 0" class="text-center py-8">
          <Info class="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p class="text-gray-600 text-sm">{{ t('installers.pending.noFiles') }}</p>
          <p class="text-gray-500 text-xs mt-2">
            {{ t('installers.pending.uploadInfo', { path: ftpConfig.path }) }}
          </p>
        </div>

        <!-- Lista de ficheros -->
        <div v-else class="space-y-3">
          <div
            v-for="file in installersStore.pendingFiles"
            :key="file.filename"
            class="card p-4 hover:shadow-md transition-shadow"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3 flex-1 min-w-0">
                <div class="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Clock class="w-6 h-6 text-yellow-600" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="font-medium text-gray-900 truncate">{{ file.filename }}</p>
                  <div class="flex items-center gap-4 text-sm text-gray-500 mt-1">
                    <span>{{ formatFileSize(file.size) }}</span>
                    <span>•</span>
                    <span>{{ formatDate(file.upload_date) }}</span>
                  </div>
                </div>
              </div>
              <div class="flex-shrink-0 ml-4">
                <span class="px-3 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded-full">
                  {{ t('installers.pending.waitingValidation') }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- ==================== MODALS ==================== -->

    <!-- Subida web (managers y admins) -->
    <InstallerUploadModal
      :show="showUploadModal"
      @close="showUploadModal = false"
      @uploaded="onFileUploaded"
    />

    <!-- Instrucciones FTP (solo admins) -->
    <div
      v-if="showFtpInfoModal"
      class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
      @click.self="showFtpInfoModal = false"
    >
      <div class="bg-white rounded-lg max-w-lg w-full p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900">
            {{ t('installers.ftp.title') }}
          </h2>
          <button
            @click="showFtpInfoModal = false"
            class="text-gray-400 hover:text-gray-600"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <p class="text-sm text-gray-600 mb-4">
          {{ t('installers.ftp.description') }}
        </p>

        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
          <div class="flex items-center gap-2 text-sm">
            <Server class="w-4 h-4 text-blue-600 flex-shrink-0" />
            <span class="text-gray-700">{{ t('installers.ftp.server') }}:</span>
            <code class="bg-white px-2 py-0.5 rounded text-blue-900 font-mono text-xs">
              {{ ftpConfig.server }}
            </code>
          </div>
          <div class="flex items-center gap-2 text-sm">
            <FolderUp class="w-4 h-4 text-blue-600 flex-shrink-0" />
            <span class="text-gray-700">{{ t('installers.ftp.path') }}:</span>
            <code class="bg-white px-2 py-0.5 rounded text-blue-900 font-mono text-xs">
              {{ ftpConfig.path }}
            </code>
          </div>
          <div class="flex items-start gap-2 text-sm">
            <Info class="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
            <span class="text-gray-600">{{ t('installers.ftp.credentials') }}</span>
          </div>
        </div>

        <div class="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <p class="text-xs text-amber-800">
            {{ t('installers.ftp.watcherNote', { interval: installersStore.watcherStats.interval_seconds }) }}
          </p>
        </div>

        <div class="flex justify-end mt-5">
          <button @click="showFtpInfoModal = false" class="btn-secondary">
            {{ t('common.close') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Registro de instalador -->
    <InstallerRegisterModal
      :show="showRegisterModal"
      :file="selectedFile"
      @close="showRegisterModal = false; selectedFile = null"
      @success="handleRegisterSuccess"
    />

    <!-- Confirmación de borrado -->
    <DeleteConfirmModal
      :show="showDeleteModal"
      :title="t('installers.list.delete')"
      :message="t('installers.list.deleteConfirm')"
      @close="showDeleteModal = false; selectedInstaller = null"
      @confirm="handleDeleteConfirm"
    />

  </AppLayout>
</template>