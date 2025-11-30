<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { useBranding } from '@/composables/useBranding';
import LanguageSelector from '@/components/common/LanguageSelector.vue';
import {
  Menu,
  X,
  LayoutDashboard,
  Package,
  Download,
  Key,
  Users,
  FileText,
  LogOut,
  ChevronDown,
} from 'lucide-vue-next';

const authStore = useAuthStore();
const router = useRouter();
const { t } = useI18n();
const { getAppName } = useBranding();

const sidebarOpen = ref(true);
const userMenuOpen = ref(false);

const handleLogout = () => {
  authStore.logout();
  router.push('/login');
};

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value;
};

// Menú de navegación basado en roles
const getNavigationItems = () => {
  const items = [
    {
      name: t('nav.dashboard'),
      to: '/dashboard',
      icon: LayoutDashboard,
      show: true,
    },
    {
      name: t('nav.software'),
      to: '/software',
      icon: Package,
      show: true,
    },
    {
      name: t('nav.installers'),
      to: '/installers',
      icon: Download,
      show: authStore.canManageSoftware,
    },
    {
      name: t('nav.licenses'),
      to: '/licenses',
      icon: Key,
      show: authStore.canViewLicenses,
    },
    {
      name: t('nav.users'),
      to: '/users',
      icon: Users,
      show: authStore.canManageUsers,
    },
    {
      name: t('nav.audit'),
      to: '/audit',
      icon: FileText,
      show: authStore.canManageUsers,
    },
  ];

  return items.filter(item => item.show);
};

const navigationItems = getNavigationItems();
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Sidebar -->
    <aside
      :class="[
        'fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      ]"
    >
      <!-- Logo -->
      <div class="h-16 flex items-center justify-between px-6 border-b border-gray-200">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background-color: var(--color-primary-600)">
            <Package class="w-5 h-5 text-white" />
          </div>
          <span class="font-bold text-lg text-gray-900">{{ getAppName() }}</span>
        </div>
        <button
          @click="toggleSidebar"
          class="lg:hidden p-1 rounded-md hover:bg-gray-100"
        >
          <X class="w-5 h-5 text-gray-500" />
        </button>
      </div>

      <!-- Navigation -->
      <nav class="p-4 space-y-1">
        <RouterLink
          v-for="item in navigationItems"
          :key="item.to"
          :to="item.to"
          v-slot="{ isActive }"
          class="block"
        >
          <div
            :class="[
              'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
              isActive
                ? 'text-primary-700'
                : 'text-gray-700 hover:bg-gray-100'
            ]"
            :style="isActive ? 'background-color: var(--color-primary-50)' : ''"
          >
            <component :is="item.icon" class="w-5 h-5" />
            <span>{{ item.name }}</span>
          </div>
        </RouterLink>
      </nav>

      <!-- User info at bottom -->
      <div class="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 bg-white">
        <div class="flex items-center gap-3 px-3 py-2">
          <div class="w-10 h-10 rounded-full flex items-center justify-center" style="background-color: var(--color-primary-100)">
            <span class="font-semibold text-sm" style="color: var(--color-primary-700)">
              {{ authStore.user?.username?.charAt(0).toUpperCase() }}
            </span>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-900 truncate">
              {{ authStore.user?.username }}
            </p>
            <p class="text-xs text-gray-500 capitalize">
              {{ authStore.userRole }}
            </p>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main content -->
    <div
      :class="[
        'transition-all duration-300 ease-in-out',
        sidebarOpen ? 'lg:pl-64' : 'pl-0'
      ]"
    >
      <!-- Header -->
      <header class="h-16 bg-white border-b border-gray-200 sticky top-0 z-40">
        <div class="h-full px-4 flex items-center justify-between">
          <!-- Menu toggle -->
          <button
            @click="toggleSidebar"
            class="p-2 rounded-md hover:bg-gray-100"
          >
            <Menu class="w-5 h-5 text-gray-500" />
          </button>

          <!-- Right side -->
          <div class="flex items-center gap-4">
            <!-- Language selector -->
            <LanguageSelector />

            <!-- User menu -->
            <div class="relative">
              <button
                @click="userMenuOpen = !userMenuOpen"
                class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100"
              >
                <div class="w-8 h-8 rounded-full flex items-center justify-center" style="background-color: var(--color-primary-100)">
                  <span class="font-semibold text-sm" style="color: var(--color-primary-700)">
                    {{ authStore.user?.username?.charAt(0).toUpperCase() }}
                  </span>
                </div>
                <ChevronDown class="w-4 h-4 text-gray-500" />
              </button>

              <!-- Dropdown -->
              <div
                v-if="userMenuOpen"
                class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1"
              >
                <button
                  @click="handleLogout"
                  class="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  <LogOut class="w-4 h-4" />
                  <span>{{ t('nav.logout') }}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      <!-- Page content -->
      <main class="p-6">
        <slot />
      </main>
    </div>

    <!-- Overlay for mobile -->
    <div
      v-if="sidebarOpen"
      @click="toggleSidebar"
      class="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
    ></div>
  </div>
</template>