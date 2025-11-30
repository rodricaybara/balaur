<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuditStore } from '@/stores/audit';
import AppLayout from '@/components/layout/AppLayout.vue';
import { FileText, Filter, Download as DownloadIcon } from 'lucide-vue-next';

const { t } = useI18n();
const auditStore = useAuditStore();

// Local filters
const localFilters = ref({
  user_id: '',
  action: '',
  resource_type: '',
  date_from: '',
  date_to: '',
});

const fetchLogs = async () => {
  auditStore.setFilters({
    userId: localFilters.value.user_id ? parseInt(localFilters.value.user_id) : null,
    action: localFilters.value.action as any,
    resourceType: localFilters.value.resource_type,
    dateFrom: localFilters.value.date_from || null,
    dateTo: localFilters.value.date_to || null,
  });
  await auditStore.fetchAuditLogs();
};

const getActionBadgeColor = (action: string) => {
  const colors: Record<string, string> = {
    login: 'bg-blue-100 text-blue-800',
    logout: 'bg-gray-100 text-gray-800',
    create: 'bg-green-100 text-green-800',
    update: 'bg-yellow-100 text-yellow-800',
    delete: 'bg-red-100 text-red-800',
    download: 'bg-purple-100 text-purple-800',
    view_license: 'bg-orange-100 text-orange-800',
  };
  return colors[action] || 'bg-gray-100 text-gray-800';
};

const formatDateTime = (dateString: string): string => {
  return new Date(dateString).toLocaleString();
};

const clearFilters = () => {
  localFilters.value = {
    user_id: '',
    action: '',
    resource_type: '',
    date_from: '',
    date_to: '',
  };
  auditStore.clearFilters();
  fetchLogs();
};

const handleExportCSV = () => {
  auditStore.exportToCSV();
};

onMounted(() => {
  fetchLogs();
});
</script>

<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">{{ t('audit.title') }}</h1>
          <p class="text-gray-600 mt-1">{{ t('audit.subtitle') }}</p>
        </div>
        <button 
          v-if="auditStore.auditLogs.length > 0"
          @click="handleExportCSV" 
          class="btn-secondary flex items-center gap-2"
        >
          <DownloadIcon class="w-4 h-4" />
          <span>Export CSV</span>
        </button>
      </div>

      <!-- Filters -->
      <div class="card mb-6">
        <div class="flex items-center gap-2 mb-4">
          <Filter class="w-5 h-5 text-gray-500" />
          <h3 class="font-medium text-gray-900">{{ t('common.filter') }}</h3>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- Action filter -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('audit.filters.action') }}
            </label>
            <select v-model="localFilters.action" class="input-field">
              <option value="">{{ t('audit.filters.allActions') }}</option>
              <option value="login">{{ t('audit.actions.login') }}</option>
              <option value="logout">{{ t('audit.actions.logout') }}</option>
              <option value="create">{{ t('audit.actions.create') }}</option>
              <option value="update">{{ t('audit.actions.update') }}</option>
              <option value="delete">{{ t('audit.actions.delete') }}</option>
              <option value="download">{{ t('audit.actions.download') }}</option>
              <option value="view_license">{{ t('audit.actions.view_license') }}</option>
            </select>
          </div>
          <!-- Resource type filter -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('audit.filters.resourceType') }}
            </label>
            <select v-model="localFilters.resource_type" class="input-field">
              <option value="">{{ t('audit.filters.allResources') }}</option>
              <option value="software">{{ t('audit.resources.software') }}</option>
              <option value="installer">{{ t('audit.resources.installer') }}</option>
              <option value="license">{{ t('audit.resources.license') }}</option>
              <option value="user">{{ t('audit.resources.user') }}</option>
            </select>
          </div>
          <!-- Date from -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('audit.filters.dateFrom') }}
            </label>
            <input
              v-model="localFilters.date_from"
              type="date"
              class="input-field"
            />
          </div>
        </div>
        <div class="flex items-center gap-3 mt-4">
          <button @click="fetchLogs" class="btn-primary">
            {{ t('audit.filters.apply') }}
          </button>
          <button v-if="auditStore.hasFilters" @click="clearFilters" class="btn-secondary">
            {{ t('audit.filters.clear') }}
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="auditStore.isLoading" class="flex items-center justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>

      <!-- Error -->
      <div v-else-if="auditStore.error" class="card bg-red-50 border-red-200">
        <p class="text-red-800">{{ auditStore.error }}</p>
      </div>

      <!-- Empty state -->
      <div v-else-if="auditStore.auditLogs.length === 0" class="card text-center py-12">
        <FileText class="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">
          {{ t('audit.list.noLogs') }}
        </h3>
      </div>

      <!-- Logs table -->
      <div v-else class="table-container">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('audit.list.timestamp') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('audit.list.user') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('audit.list.action') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('audit.list.resource') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('audit.list.ipAddress') }}
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="log in auditStore.auditLogs" :key="log.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ formatDateTime(log.timestamp) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ log.username || t('audit.list.anonymous') }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', getActionBadgeColor(log.action)]">
                  {{ t(`audit.actions.${log.action}`) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                <span v-if="log.resource_type">
                  {{ t(`audit.resources.${log.resource_type}`) }}
                  <span v-if="log.resource_id" class="text-gray-500">#{{ log.resource_id }}</span>
                </span>
                <span v-else class="text-gray-400">—</span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ log.ip_address || '—' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="auditStore.totalPages > 1" class="mt-6 flex items-center justify-between">
        <div class="text-sm text-gray-700">
          {{ t('common.showing') }}
          <span class="font-medium">{{ ((auditStore.currentPage - 1) * auditStore.pageSize) + 1 }}</span>
          {{ t('common.to') }}
          <span class="font-medium">{{ Math.min(auditStore.currentPage * auditStore.pageSize, auditStore.totalItems) }}</span>
          {{ t('common.of') }}
          <span class="font-medium">{{ auditStore.totalItems }}</span>
          {{ t('common.results') }}
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="auditStore.setPage(auditStore.currentPage - 1); fetchLogs()"
            :disabled="auditStore.currentPage === 1"
            class="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('common.previous') }}
          </button>
          <span class="text-sm text-gray-700">
            {{ t('common.page') }} {{ auditStore.currentPage }} {{ t('common.of') }} {{ auditStore.totalPages }}
          </span>
          <button
            @click="auditStore.setPage(auditStore.currentPage + 1); fetchLogs()"
            :disabled="auditStore.currentPage === auditStore.totalPages"
            class="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('common.next') }}
          </button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>