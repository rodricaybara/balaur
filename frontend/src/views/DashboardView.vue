<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import AppLayout from '@/components/layout/AppLayout.vue';
import { Package, Download, Users, Key, TrendingUp } from 'lucide-vue-next';
import apiClient from '@/api/client';

const authStore = useAuthStore();
const router = useRouter();
const { t } = useI18n();

const stats = ref({
  totalSoftware: 0,
  totalInstallers: 0,
  totalUsers: 0,
  totalLicenses: 0,
});

const isLoading = ref(true);

// Welcome message con nombre del usuario
const welcomeMessage = computed(() => {
  const name = authStore.user?.full_name || authStore.user?.username || '';
  return t('dashboard.welcome', { name });
});

onMounted(async () => {
  try {
    // Cargar estadísticas básicas
    const softwareResponse = await apiClient.software.listSoftware(1, 1);
    stats.value.totalSoftware = softwareResponse.data.total || 0;

    // Solo admins pueden ver stats de usuarios y licencias
    if (authStore.isAdmin) {
      const usersResponse = await apiClient.users.listUsers(1, 1);
      stats.value.totalUsers = usersResponse.data.total || 0;

      const licensesResponse = await apiClient.licenses.listLicenses(1, 1);
      stats.value.totalLicenses = licensesResponse.data.total || 0;
    }
  } catch (error) {
    console.error('Error loading dashboard stats:', error);
  } finally {
    isLoading.value = false;
  }
});

const quickActions = computed(() => [
  {
    name: t('dashboard.quickActions.exploreSoftware.name'),
    description: t('dashboard.quickActions.exploreSoftware.description'),
    icon: Package,
    to: '/software',
    color: 'primary',
    show: true,
  },
  {
    name: t('dashboard.quickActions.manageInstallers.name'),
    description: t('dashboard.quickActions.manageInstallers.description'),
    icon: Download,
    to: '/installers',
    color: 'blue',
    show: authStore.canManageSoftware,
  },
  {
    name: t('dashboard.quickActions.manageUsers.name'),
    description: t('dashboard.quickActions.manageUsers.description'),
    icon: Users,
    to: '/users',
    color: 'purple',
    show: authStore.isAdmin,
  },
  {
    name: t('dashboard.quickActions.manageLicenses.name'),
    description: t('dashboard.quickActions.manageLicenses.description'),
    icon: Key,
    to: '/licenses',
    color: 'green',
    show: authStore.isAdmin,
  },
]);

const visibleActions = computed(() => quickActions.value.filter(action => action.show));

const roleNote = computed(() => {
  if (authStore.isGuest) {
    return t('dashboard.roleInfo.guestNote');
  }
  return '';
});
</script>

<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto">
      <!-- Welcome message -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">
          {{ welcomeMessage }}
        </h1>
        <p class="text-gray-600 mt-2">
          {{ t('dashboard.subtitle') }}
        </p>
      </div>

      <!-- Stats grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <!-- Total Software -->
        <div class="card">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">
                {{ t('dashboard.stats.totalSoftware') }}
              </p>
              <p class="text-3xl font-bold text-gray-900 mt-2">
                {{ isLoading ? '...' : stats.totalSoftware }}
              </p>
            </div>
            <div class="w-12 h-12 rounded-lg flex items-center justify-center" style="background-color: var(--color-primary-100)">
              <Package class="w-6 h-6" style="color: var(--color-primary-600)" />
            </div>
          </div>
          <div class="mt-4 flex items-center text-sm text-gray-600">
            <TrendingUp class="w-4 h-4 text-green-500 mr-1" />
            <span>{{ t('dashboard.stats.availableForDownload') }}</span>
          </div>
        </div>

        <!-- Total Installers -->
        <div class="card">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">
                {{ t('dashboard.stats.installers') }}
              </p>
              <p class="text-3xl font-bold text-gray-900 mt-2">
                {{ isLoading ? '...' : stats.totalInstallers }}
              </p>
            </div>
            <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <Download class="w-6 h-6 text-blue-600" />
            </div>
          </div>
          <div class="mt-4 flex items-center text-sm text-gray-600">
            <span>{{ t('dashboard.stats.filesInRepository') }}</span>
          </div>
        </div>

        <!-- Total Users (Admin only) -->
        <div v-if="authStore.isAdmin" class="card">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">
                {{ t('dashboard.stats.users') }}
              </p>
              <p class="text-3xl font-bold text-gray-900 mt-2">
                {{ isLoading ? '...' : stats.totalUsers }}
              </p>
            </div>
            <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <Users class="w-6 h-6 text-purple-600" />
            </div>
          </div>
          <div class="mt-4 flex items-center text-sm text-gray-600">
            <span>{{ t('dashboard.stats.registeredUsers') }}</span>
          </div>
        </div>

        <!-- Total Licenses (Admin only) -->
        <div v-if="authStore.isAdmin" class="card">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm font-medium text-gray-600">
                {{ t('dashboard.stats.licenses') }}
              </p>
              <p class="text-3xl font-bold text-gray-900 mt-2">
                {{ isLoading ? '...' : stats.totalLicenses }}
              </p>
            </div>
            <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Key class="w-6 h-6 text-green-600" />
            </div>
          </div>
          <div class="mt-4 flex items-center text-sm text-gray-600">
            <span>{{ t('dashboard.stats.activeLicenses') }}</span>
          </div>
        </div>
      </div>

      <!-- Quick actions -->
      <div class="card">
        <h2 class="text-xl font-semibold text-gray-900 mb-6">
          {{ t('dashboard.quickActions.title') }}
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            v-for="action in visibleActions"
            :key="action.to"
            @click="router.push(action.to)"
            class="flex items-start gap-4 p-4 rounded-lg border-2 border-gray-200 transition-all text-left hover:border-primary-300"
            style="hover:background-color: var(--color-primary-50)"
          >
            <div
              :class="[
                'w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0',
                `bg-${action.color}-100`
              ]"
            >
              <component :is="action.icon" :class="`w-6 h-6 text-${action.color}-600`" />
            </div>
            <div>
              <h3 class="font-semibold text-gray-900">{{ action.name }}</h3>
              <p class="text-sm text-gray-600 mt-1">{{ action.description }}</p>
            </div>
          </button>
        </div>
      </div>

      <!-- Role info -->
      <div class="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p class="text-sm text-blue-800">
          <strong>{{ t('dashboard.roleInfo.yourRole') }}</strong>
          <span class="capitalize ml-1">{{ authStore.userRole }}</span>
          <span v-if="roleNote" class="ml-2">- {{ roleNote }}</span>
        </p>
      </div>
    </div>
  </AppLayout>
</template>