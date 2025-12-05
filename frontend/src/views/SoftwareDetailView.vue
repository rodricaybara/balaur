<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { useSoftwareStore } from '@/stores/software';
import { useInstallersStore } from '@/stores/installers';
import { useLicensesStore } from '@/stores/licenses';
import { useNotificationsStore } from '@/stores/notifications';
import AppLayout from '@/components/layout/AppLayout.vue';
import SoftwareFormModal from '@/components/common/SoftwareFormModal.vue';
import DeleteConfirmModal from '@/components/common/DeleteConfirmModal.vue';
import LicenseFormModal from '@/components/common/LicenseFormModal.vue';
import ViewLicenseKeyModal from '@/components/common/ViewLicenseKeyModal.vue';
import type { LicenseResponse } from '@/api/api';
import {
  ArrowLeft,
  Package,
  ExternalLink,
  Download,
  Key,
  Edit,
  Trash2,
  Plus,
  Eye,
  Loader2,
} from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const authStore = useAuthStore();
const softwareStore = useSoftwareStore();
const installersStore = useInstallersStore();
const licensesStore = useLicensesStore();
const notificationsStore = useNotificationsStore();

const softwareId = parseInt(route.params.id as string);
const activeTab = ref<'overview' | 'installers' | 'licenses'>('overview');

// Modals state
const showEditModal = ref(false);
const showDeleteModal = ref(false);
const showLicenseModal = ref(false);
const showViewKeyModal = ref(false);
const showDeleteLicenseModal = ref(false);
const selectedLicense = ref<LicenseResponse | null>(null);

const software = computed(() => softwareStore.currentSoftware);
const isLoading = computed(() => softwareStore.isLoading);
const error = computed(() => softwareStore.error);

const installers = computed(() => {
  return ('installers' in (software.value ?? {}))
    ? (software.value as any).installers
    : [];
});

const licenses = computed(() => {
  return ('licenses' in (software.value ?? {}))
    ? (software.value as any).licenses
    : [];
});

const fetchSoftware = async () => {
  await softwareStore.fetchSoftwareDetail(softwareId, true);
};

const handleEdit = () => {
  showEditModal.value = true;
};

const handleEditSuccess = async () => {
  await fetchSoftware();
  showEditModal.value = false;
  notificationsStore.success(t('common.success'));
};

const handleDelete = () => {
  showDeleteModal.value = true;
};

const handleDeleteConfirm = async () => {
  try {
    await softwareStore.deleteSoftware(softwareId);
    notificationsStore.success('Software deleted successfully');
    showDeleteModal.value = false;
    router.push('/software');
  } catch (err) {
    notificationsStore.error('Failed to delete software');
    showDeleteModal.value = false;
  }
};

const downloadInstaller = async (installerId: number) => {
  try {
    await installersStore.downloadInstaller(installerId);
    notificationsStore.success('Download started');
    // Refresh para actualizar download count
    await fetchSoftware();
  } catch (err) {
    notificationsStore.error('Failed to download installer');
  }
};

const handleCreateLicense = () => {
  selectedLicense.value = null;
  showLicenseModal.value = true;
};

const handleViewLicenseKey = (license: LicenseResponse) => {
  selectedLicense.value = license;
  showViewKeyModal.value = true;
};

const handleEditLicense = (license: LicenseResponse) => {
  selectedLicense.value = license;
  showLicenseModal.value = true;
};

const handleDeleteLicense = (license: LicenseResponse) => {
  selectedLicense.value = license;
  showDeleteLicenseModal.value = true;
};

const handleDeleteLicenseConfirm = async () => {
  if (!selectedLicense.value) return;
  
  try {
    await licensesStore.deleteLicense(selectedLicense.value.id);
    notificationsStore.success('License deleted successfully');
    showDeleteLicenseModal.value = false;
    selectedLicense.value = null;
    await fetchSoftware();
  } catch (err) {
    notificationsStore.error('Failed to delete license');
    showDeleteLicenseModal.value = false;
  }
};

const handleLicenseSuccess = async () => {
  await fetchSoftware();
  showLicenseModal.value = false;
  selectedLicense.value = null;
  notificationsStore.success(t('common.success'));
};

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
};

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString();
};

const getLicenseTypeBadgeColor = (type: string) => {
  const colors: Record<string, string> = {
    perpetual: 'bg-blue-100 text-blue-800',
    subscription: 'bg-green-100 text-green-800',
    volume: 'bg-purple-100 text-purple-800',
    oem: 'bg-yellow-100 text-yellow-800',
    educational: 'bg-indigo-100 text-indigo-800',
    trial: 'bg-orange-100 text-orange-800',
  };
  return colors[type] || 'bg-gray-100 text-gray-800';
};

onMounted(() => {
  fetchSoftware();
});
</script>

<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-4">
          <button
            @click="router.push('/software')"
            class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft class="w-5 h-5 text-gray-600" />
          </button>
          <div>
            <h1 class="text-2xl font-bold text-gray-900">
              {{ software?.name || t('softwareDetail.title') }}
            </h1>
            <p v-if="software" class="text-gray-600 mt-1">{{ software.vendor }}</p>
          </div>
        </div>

        <div v-if="authStore.canManageSoftware && software" class="flex items-center gap-2">
          <button @click="handleEdit" class="btn-secondary flex items-center gap-2">
            <Edit class="w-4 h-4" />
            <span>{{ t('softwareDetail.edit') }}</span>
          </button>
          <button v-if="authStore.isAdmin" @click="handleDelete" class="btn-danger flex items-center gap-2">
            <Trash2 class="w-4 h-4" />
            <span>{{ t('softwareDetail.delete') }}</span>
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="flex items-center justify-center py-12">
        <Loader2 class="w-8 h-8 text-primary-600 animate-spin" />
      </div>

      <!-- Error -->
      <div v-else-if="error" class="card bg-red-50 border-red-200">
        <p class="text-red-800">{{ error }}</p>
        <button @click="fetchSoftware" class="mt-3 text-sm text-red-700 underline">
          {{ t('common.retry') }}
        </button>
      </div>

      <!-- Content -->
      <div v-else-if="software">
        <!-- Tabs -->
        <div class="border-b border-gray-200 mb-6">
          <nav class="-mb-px flex gap-6">
            <button
              @click="activeTab = 'overview'"
              :class="[
                'py-3 px-1 border-b-2 font-medium text-sm',
                activeTab === 'overview'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              ]"
            >
              {{ t('softwareDetail.tabs.overview') }}
            </button>
            <button
              @click="activeTab = 'installers'"
              :class="[
                'py-3 px-1 border-b-2 font-medium text-sm',
                activeTab === 'installers'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              ]"
            >
              {{ t('softwareDetail.tabs.installers') }}
              <span class="ml-2 px-2 py-0.5 rounded-full text-xs bg-gray-100">
                {{ installers.length }}
              </span>
            </button>
            <button
              v-if="authStore.isAdmin"
              @click="activeTab = 'licenses'"
              :class="[
                'py-3 px-1 border-b-2 font-medium text-sm',
                activeTab === 'licenses'
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              ]"
            >
              {{ t('softwareDetail.tabs.licenses') }}
              <span class="ml-2 px-2 py-0.5 rounded-full text-xs bg-gray-100">
                {{ licenses.length }}
              </span>
            </button>
          </nav>
        </div>

        <!-- Overview Tab -->
        <div v-if="activeTab === 'overview'" class="card">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 class="text-sm font-medium text-gray-500 mb-1">{{ t('softwareDetail.overview.vendor') }}</h3>
              <p class="text-gray-900">{{ software.vendor }}</p>
            </div>
            <div>
              <h3 class="text-sm font-medium text-gray-500 mb-1">{{ t('softwareDetail.overview.category') }}</h3>
              <p class="text-gray-900">{{ software.category }}</p>
            </div>
            <div v-if="software.website">
              <h3 class="text-sm font-medium text-gray-500 mb-1">{{ t('softwareDetail.overview.website') }}</h3>
              <a :href="software.website" target="_blank" class="text-primary-600 hover:text-primary-700 flex items-center gap-2">
                {{ software.website }}
                <ExternalLink class="w-4 h-4" />
              </a>
            </div>
            <div v-if="software.created_at">
              <h3 class="text-sm font-medium text-gray-500 mb-1">{{ t('softwareDetail.overview.createdAt') }}</h3>
              <p class="text-gray-900">{{ formatDate(software.created_at) }}</p>
            </div>
          </div>
          
          <div v-if="software.description" class="mt-6 pt-6 border-t border-gray-200">
            <h3 class="text-sm font-medium text-gray-500 mb-2">{{ t('softwareDetail.overview.description') }}</h3>
            <p class="text-gray-900">{{ software.description }}</p>
          </div>
          <div v-else class="mt-6 pt-6 border-t border-gray-200 text-center text-gray-500">
            {{ t('softwareDetail.overview.noDescription') }}
          </div>
        </div>

        <!-- Installers Tab -->
        <div v-if="activeTab === 'installers'">
          <div v-if="installers.length === 0" class="card text-center py-12">
            <Download class="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 class="text-lg font-medium text-gray-900 mb-2">
              {{ t('softwareDetail.installers.noInstallers') }}
            </h3>
            <p class="text-gray-600 mb-4">
              {{ t('softwareDetail.installers.uploadFirst') }}
            </p>
            <button
              v-if="authStore.canManageSoftware"
              @click="router.push('/installers')"
              class="btn-primary"
            >
              {{ t('installers.uploadNew') }}
            </button>
          </div>
          
          <div v-else class="table-container">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {{ t('softwareDetail.installers.version') }}
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {{ t('softwareDetail.installers.size') }}
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {{ t('softwareDetail.installers.platform') }}
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {{ t('softwareDetail.installers.downloads') }}
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {{ t('softwareDetail.installers.uploadDate') }}
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {{ t('common.actions') }}
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="installer in installers" :key="installer.id" class="hover:bg-gray-50">
                  <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
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
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {{ installer.created_at ? formatDate(installer.created_at) : '—' }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      v-if="authStore.canDownload"
                      @click="downloadInstaller(installer.id)"
                      class="text-primary-600 hover:text-primary-700"
                      :title="t('softwareDetail.installers.download')"
                    >
                      <Download class="w-4 h-4" />
                    </button>
                    <span v-else class="text-gray-400" :title="t('dashboard.roleInfo.guestNote')">
                      <Download class="w-4 h-4" />
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Licenses Tab -->
        <div v-if="activeTab === 'licenses' && authStore.isAdmin">
          <!-- Header con botón -->
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-gray-900">
              {{ t('softwareDetail.licenses.title') }}
            </h2>
            <button @click="handleCreateLicense" class="btn-primary flex items-center gap-2">
              <Plus class="w-4 h-4" />
              <span>{{ t('softwareDetail.licenses.addLicense') }}</span>
            </button>
          </div>

          <div v-if="licenses.length === 0" class="card text-center py-12">
            <Key class="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 class="text-lg font-medium text-gray-900 mb-2">
              {{ t('softwareDetail.licenses.noLicenses') }}
            </h3>
            <button @click="handleCreateLicense" class="btn-primary mt-4">
              {{ t('softwareDetail.licenses.addLicense') }}
            </button>
          </div>

          <div v-else class="table-container">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {{ t('licenses.list.type') }}
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {{ t('licenses.list.maxActivations') }}
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {{ t('licenses.list.expirationDate') }}
                  </th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    {{ t('licenses.list.actions') }}
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                <tr v-for="license in licenses" :key="license.id" class="hover:bg-gray-50">
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', getLicenseTypeBadgeColor(license.license_type)]">
                      {{ t(`licenses.types.${license.license_type}`) }}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {{ license.max_activations || t('licenses.list.unlimited') }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {{ license.expiration_date ? formatDate(license.expiration_date) : t('licenses.list.noExpiration') }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <div class="flex items-center gap-2">
                      <button 
                        @click="handleViewLicenseKey(license)"
                        class="text-primary-600 hover:text-primary-700" 
                        :title="t('licenses.list.view')"
                      >
                        <Eye class="w-4 h-4" />
                      </button>
                      <button 
                        @click="handleEditLicense(license)"
                        class="text-blue-600 hover:text-blue-700" 
                        :title="t('licenses.list.edit')"
                      >
                        <Edit class="w-4 h-4" />
                      </button>
                      <button 
                        @click="handleDeleteLicense(license)"
                        class="text-red-600 hover:text-red-700" 
                        :title="t('licenses.list.delete')"
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
      </div>
    </div>

    <!-- Modals -->
    <SoftwareFormModal
      :show="showEditModal"
      :software="software"
      @close="showEditModal = false"
      @success="handleEditSuccess"
    />

    <DeleteConfirmModal
      :show="showDeleteModal"
      :title="t('softwareDetail.delete')"
      message="Are you sure you want to delete this software? This will also delete all associated installers and licenses."
      @close="showDeleteModal = false"
      @confirm="handleDeleteConfirm"
    />

    <LicenseFormModal
      :show="showLicenseModal"
      :license="selectedLicense"
      @close="showLicenseModal = false; selectedLicense = null"
      @success="handleLicenseSuccess"
    />

    <ViewLicenseKeyModal
      :show="showViewKeyModal"
      :license-id="selectedLicense?.id || null"
      @close="showViewKeyModal = false; selectedLicense = null"
    />

    <DeleteConfirmModal
      :show="showDeleteLicenseModal"
      :title="t('licenses.list.delete')"
      message="Are you sure you want to delete this license? This action cannot be undone."
      @close="showDeleteLicenseModal = false; selectedLicense = null"
      @confirm="handleDeleteLicenseConfirm"
    />
  </AppLayout>
</template>