<script setup lang="ts">
import { ref, computed, onMounted, watch, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { useSoftwareStore } from '@/stores/software';
import AppLayout from '@/components/layout/AppLayout.vue';
import SoftwareFormModal from '@/components/common/SoftwareFormModal.vue';
import {
  Search,
  Filter,
  Package,
  ExternalLink,
  Plus,
  Grid3x3,
  List,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Loader2,
} from 'lucide-vue-next';

// ============================================================================
// STATE
// ============================================================================

const authStore = useAuthStore();
const softwareStore = useSoftwareStore();
const router = useRouter();
const { t } = useI18n();

// Vista (grid o lista)
const viewMode = ref<'grid' | 'list'>('grid');

// Modal state
const showSoftwareModal = ref(false);

// ============================================================================
// COMPUTED
// ============================================================================

const canCreateSoftware = computed(() => authStore.canManageSoftware);

// Debounce para búsqueda
let searchTimeout: ReturnType<typeof setTimeout> | null = null;
watch(
  () => softwareStore.filters.search,
  () => {
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      softwareStore.currentPage = 1;
      fetchSoftware();
    }, 400);
  }
);

// Computed pages array para paginación (más claro que iterar sobre un número)
const pages = computed(() => {
  const p = Math.max(0, softwareStore.totalPages || 0);
  return Array.from({ length: p }, (_, i) => i + 1);
});

// ============================================================================
// METHODS
// ============================================================================

const fetchSoftware = async () => {
  await softwareStore.fetchSoftwareList();
};

const handleSearch = () => {
  fetchSoftware();
};

const clearFilters = () => {
  softwareStore.clearFilters();
  fetchSoftware();
};

const goToPage = (page: number) => {
  softwareStore.setPage(page);
  fetchSoftware();
};

// Limpieza
onBeforeUnmount(() => {
  if (searchTimeout) clearTimeout(searchTimeout);
});

// Protección al navegar a detalle
const viewSoftwareDetail = (softwareId?: number) => {
  if (!softwareId) return;
  router.push(`/software/${softwareId}`);
};

const handleCreateSoftware = () => {
  showSoftwareModal.value = true;
};

const handleSoftwareSuccess = async () => {
  await fetchSoftware();
  showSoftwareModal.value = false;
};

// ============================================================================
// LIFECYCLE
// ============================================================================

onMounted(() => {
  fetchSoftware();
});

// Watch para refrescar cuando cambien los filtros
watch(
  () => [softwareStore.filters.category, softwareStore.filters.vendor],
  () => {
    softwareStore.currentPage = 1;
    fetchSoftware();
  }
);
</script>

<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">{{ t('software.title') }}</h1>
          <p class="text-gray-600 mt-1">
            {{ t('software.availableApps', { count: softwareStore.totalItems }) }}
          </p>
        </div>
        <!-- Botón crear (solo para admin/manager) -->
        <button
          v-if="canCreateSoftware"
          @click="handleCreateSoftware"
          class="btn-primary flex items-center gap-2"
        >
          <Plus class="w-5 h-5" />
          <span>{{ t('software.newSoftware') }}</span>
        </button>
      </div>

      <!-- Filtros y búsqueda -->
      <div class="card mb-6">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <!-- Búsqueda -->
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('common.search') }}
            </label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search class="h-5 w-5 text-gray-400" />
              </div>
              <input
                v-model="softwareStore.filters.search"
                type="text"
                :placeholder="t('software.searchPlaceholder')"
                class="input-field pl-10"
                @keyup.enter="handleSearch"
              />
            </div>
          </div>

          <!-- Categoría -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('software.category') }}
            </label>
            <select
              v-model="softwareStore.filters.category"
              class="input-field"
            >
              <option value="">{{ t('software.allCategories') }}</option>
              <option
                v-for="category in softwareStore.categories"
                :key="category"
                :value="category"
              >
                {{ category }}
              </option>
            </select>
          </div>

          <!-- Vendor -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('software.vendor') }}
            </label>
            <select
              v-model="softwareStore.filters.vendor"
              class="input-field"
            >
              <option value="">{{ t('software.allVendors') }}</option>
              <option
                v-for="vendor in softwareStore.vendors"
                :key="vendor"
                :value="vendor"
              >
                {{ vendor }}
              </option>
            </select>
          </div>
        </div>

        <!-- Acciones de filtros -->
        <div class="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
          <button
            v-if="softwareStore.hasFilters"
            @click="clearFilters"
            class="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-2"
          >
            <Filter class="w-4 h-4" />
            <span>{{ t('software.clearFilters') }}</span>
          </button>
          <div v-else></div>

          <!-- Toggle vista -->
          <div class="flex items-center gap-2">
            <button
              @click="viewMode = 'grid'"
              :class="[
                'p-2 rounded-md',
                viewMode === 'grid'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-500 hover:bg-gray-100'
              ]"
              :title="t('software.viewMode.grid')"
            >
              <Grid3x3 class="w-5 h-5" />
            </button>
            <button
              @click="viewMode = 'list'"
              :class="[
                'p-2 rounded-md',
                viewMode === 'list'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-500 hover:bg-gray-100'
              ]"
              :title="t('software.viewMode.list')"
            >
              <List class="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      <!-- Loading state -->
      <div v-if="softwareStore.isLoading" class="flex items-center justify-center py-12">
        <Loader2 class="w-8 h-8 text-primary-600 animate-spin" />
      </div>

      <!-- Error state -->
      <div
        v-else-if="softwareStore.error"
        class="card bg-red-50 border-red-200 flex items-start gap-3"
      >
        <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
        <div>
          <p class="text-sm font-medium text-red-800">{{ t('software.errorLoading') }}</p>
          <p class="text-sm text-red-700 mt-1">{{ softwareStore.error }}</p>
          <button
            @click="fetchSoftware"
            class="mt-3 text-sm text-red-700 underline hover:text-red-800"
          >
            {{ t('common.retry') }}
          </button>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="softwareStore.softwareList.length === 0"
        class="card text-center py-12"
      >
        <Package class="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">
          {{ t('software.noSoftware') }}
        </h3>
        <p class="text-gray-600 mb-4">
          {{ softwareStore.hasFilters ? t('software.changeFilters') : t('software.noSoftwareInSystem') }}
        </p>
        <button
          v-if="softwareStore.hasFilters"
          @click="clearFilters"
          class="btn-secondary"
        >
          {{ t('software.clearFilters') }}
        </button>
      </div>

      <!-- Grid view -->
      <div
        v-else-if="viewMode === 'grid'"
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        <div
          v-for="software in softwareStore.softwareList"
          :key="software.id"
          @click="viewSoftwareDetail(software.id)"
          class="card hover:shadow-lg transition-shadow cursor-pointer group"
        >
          <!-- Header -->
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
                <Package class="w-6 h-6 text-primary-600" />
              </div>
              <div>
                <h3 class="font-semibold text-gray-900 group-hover:text-primary-600 transition-colors">
                  {{ software.name }}
                </h3>
                <p class="text-sm text-gray-600">{{ software.vendor }}</p>
              </div>
            </div>
          </div>

          <!-- Category badge -->
          <div class="mb-3">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {{ software.category }}
            </span>
          </div>

          <!-- Description -->
          <p v-if="software.description" class="text-sm text-gray-600 line-clamp-2 mb-4">
            {{ software.description }}
          </p>

          <!-- Footer -->
          <div class="flex items-center justify-between pt-4 border-t border-gray-200">
            <div class="flex items-center gap-3">
              <a
                v-if="software.website"
                :href="software.website"
                target="_blank"
                @click.stop
                class="text-sm text-primary-600 hover:text-primary-700 flex items-center gap-1"
              >
                <ExternalLink class="w-4 h-4" />
                <span>{{ t('software.website') }}</span>
              </a>
              <div v-else class="text-gray-400">—</div>
            </div>
            <span class="text-xs text-gray-500">
              ID: {{ software.id }}
            </span>
          </div>
        </div>
      </div>

      <!-- List view -->
      <div v-else-if="viewMode === 'list'" class="table-container">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ t('software.title') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ t('software.category') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ t('software.vendor') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ t('software.website') }}
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr
              v-for="software in softwareStore.softwareList"
              :key="software.id"
              @click="viewSoftwareDetail(software.id)"
              class="hover:bg-gray-50 cursor-pointer"
            >
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <div class="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center mr-3">
                    <Package class="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <div class="text-sm font-medium text-gray-900">
                      {{ software.name }}
                    </div>
                    <div v-if="software.description" class="text-sm text-gray-500 max-w-md truncate">
                      {{ software.description }}
                    </div>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {{ software.category }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ software.vendor }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <a
                  v-if="software.website"
                  :href="software.website"
                  target="_blank"
                  @click.stop
                  class="text-primary-600 hover:text-primary-700 flex items-center gap-1"
                >
                  <ExternalLink class="w-4 h-4" />
                  <span>{{ t('software.visit') }}</span>
                </a>
                <span v-else class="text-gray-400">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Paginación -->
      <div
        v-if="softwareStore.totalPages > 1 && !softwareStore.isLoading"
        class="flex items-center justify-between mt-6"
      >
        <div class="text-sm text-gray-700">
          {{ t('common.showing') }}
          <span class="font-medium">{{ ((softwareStore.currentPage - 1) * softwareStore.pageSize) + 1 }}</span>
          {{ t('common.to') }}
          <span class="font-medium">{{ Math.min(softwareStore.currentPage * softwareStore.pageSize, softwareStore.totalItems) }}</span>
          {{ t('common.of') }}
          <span class="font-medium">{{ softwareStore.totalItems }}</span>
          {{ t('common.results') }}
        </div>

        <div class="flex items-center gap-2">
          <button
            @click="goToPage(softwareStore.currentPage - 1)"
            :disabled="softwareStore.currentPage === 1"
            class="btn-secondary flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft class="w-4 h-4" />
            <span>{{ t('common.previous') }}</span>
          </button>

          <!-- Números de página -->
          <div class="hidden sm:flex items-center gap-1">
            <button
              v-for="page in softwareStore.totalPages"
              :key="page"
              v-show="page === 1 || page === softwareStore.totalPages || Math.abs(page - softwareStore.currentPage) <= 1"
              @click="goToPage(page)"
              :class="[
                'px-3 py-2 text-sm font-medium rounded-lg',
                page === softwareStore.currentPage
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-700 hover:bg-gray-100'
              ]"
            >
              {{ page }}
            </button>
          </div>

          <button
            @click="goToPage(softwareStore.currentPage + 1)"
            :disabled="softwareStore.currentPage === softwareStore.totalPages"
            class="btn-secondary flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span>{{ t('common.next') }}</span>
            <ChevronRight class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Software Form Modal -->
    <SoftwareFormModal
      :show="showSoftwareModal"
      @close="showSoftwareModal = false"
      @success="handleSoftwareSuccess"
    />
  </AppLayout>
</template>