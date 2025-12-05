<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useLicensesStore } from '@/stores/licenses';
import AppLayout from '@/components/layout/AppLayout.vue';
import LicenseFormModal from '@/components/common/LicenseFormModal.vue';
import ViewLicenseKeyModal from '@/components/common/ViewLicenseKeyModal.vue';
import DeleteConfirmModal from '@/components/common/DeleteConfirmModal.vue';
import type { LicenseResponse } from '@/api/api';
import { Key, Plus, Eye, Edit, Trash2, Shield } from 'lucide-vue-next';
import { formatDate } from "@/utils/format";

const { t } = useI18n();
const licensesStore = useLicensesStore();

// Modals state
const showLicenseModal = ref(false);
const showViewKeyModal = ref(false);
const showDeleteModal = ref(false);
const selectedLicense = ref<LicenseResponse | null>(null);

const fetchLicenses = async () => {
  await licensesStore.fetchLicenses();
};

const handleCreateLicense = () => {
  selectedLicense.value = null;
  showLicenseModal.value = true;
};

const handleViewKey = (license: LicenseResponse) => {
  selectedLicense.value = license;
  showViewKeyModal.value = true;
};

const handleEditLicense = (license: LicenseResponse) => {
  selectedLicense.value = license;
  showLicenseModal.value = true;
};

const handleDeleteLicense = (license: LicenseResponse) => {
  selectedLicense.value = license;
  showDeleteModal.value = true;
};

const handleLicenseSuccess = async () => {
  await fetchLicenses();
  showLicenseModal.value = false;
  selectedLicense.value = null;
};

const handleDeleteConfirm = async () => {
  if (!selectedLicense.value) return;
  
  try {
    await licensesStore.deleteLicense(selectedLicense.value.id);
    showDeleteModal.value = false;
    selectedLicense.value = null;
  } catch (err) {
    console.error('Error deleting license:', err);
  }
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
  fetchLicenses();
});
</script>

<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">{{ t('licenses.title') }}</h1>
          <p class="text-gray-600 mt-1">{{ t('licenses.subtitle') }}</p>
        </div>
        <button @click="handleCreateLicense" class="btn-primary flex items-center gap-2">
          <Plus class="w-5 h-5" />
          <span>{{ t('licenses.newLicense') }}</span>
        </button>
      </div>

      <!-- Security warning -->
      <div class="card bg-amber-50 border-amber-200 mb-6">
        <div class="flex items-start gap-3">
          <Shield class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <p class="text-sm font-medium text-amber-900">{{ t('licenses.security.warning') }}</p>
            <p class="text-sm text-amber-800 mt-1">{{ t('licenses.security.accessLogged') }}</p>
          </div>
        </div>
      </div>

      <!-- Error message -->
      <div v-if="licensesStore.error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-sm text-red-800">{{ licensesStore.error }}</p>
      </div>

      <!-- Loading -->
      <div v-if="licensesStore.isLoading" class="flex items-center justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>

      <!-- Empty state -->
      <div v-else-if="licensesStore.licensesList.length === 0" class="card text-center py-12">
        <Key class="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">
          {{ t('licenses.list.noLicenses') }}
        </h3>
        <button @click="handleCreateLicense" class="btn-primary mt-4">
          {{ t('licenses.newLicense') }}
        </button>
      </div>

      <!-- Licenses table -->
      <div v-else class="table-container">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('licenses.list.software') }}
              </th>
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
            <tr v-for="license in licensesStore.licensesList" :key="license.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center gap-2">
                  <Key class="w-4 h-4 text-gray-400" />
                  <span class="text-sm font-medium text-gray-900">Software #{{ license.software_id }}</span>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', getLicenseTypeBadgeColor(license.license_type)]">
                  {{ t(`licenses.types.${license.license_type}`) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ license.max_activations || t('licenses.list.unlimited') }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ formatDate(license.expiration_date) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <div class="flex items-center gap-2">
                  <button 
                    @click="handleViewKey(license)"
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

      <!-- Pagination -->
      <div v-if="licensesStore.totalPages > 1" class="mt-6 flex items-center justify-between">
        <div class="text-sm text-gray-700">
          {{ t('common.showing') }}
          <span class="font-medium">{{ ((licensesStore.currentPage - 1) * licensesStore.pageSize) + 1 }}</span>
          {{ t('common.to') }}
          <span class="font-medium">{{ Math.min(licensesStore.currentPage * licensesStore.pageSize, licensesStore.totalItems) }}</span>
          {{ t('common.of') }}
          <span class="font-medium">{{ licensesStore.totalItems }}</span>
          {{ t('common.results') }}
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="licensesStore.setPage(licensesStore.currentPage - 1); fetchLicenses()"
            :disabled="licensesStore.currentPage === 1"
            class="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('common.previous') }}
          </button>
          <span class="text-sm text-gray-700">
            {{ t('common.page') }} {{ licensesStore.currentPage }} {{ t('common.of') }} {{ licensesStore.totalPages }}
          </span>
          <button
            @click="licensesStore.setPage(licensesStore.currentPage + 1); fetchLicenses()"
            :disabled="licensesStore.currentPage === licensesStore.totalPages"
            class="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('common.next') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modals -->
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
      :show="showDeleteModal"
      :title="t('licenses.list.delete')"
      message="Are you sure you want to delete this license? This action cannot be undone."
      @close="showDeleteModal = false; selectedLicense = null"
      @confirm="handleDeleteConfirm"
    />
  </AppLayout>
</template>