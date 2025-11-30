<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import { useUsersStore } from '@/stores/users';
import AppLayout from '@/components/layout/AppLayout.vue';
import UserFormModal from '@/components/common/UserFormModal.vue';
import DeleteConfirmModal from '@/components/common/DeleteConfirmModal.vue';
import type { UserResponse } from '@/api/api';
import { Users as UsersIcon, Plus, Edit, Trash2, Search, Filter } from 'lucide-vue-next';

const { t } = useI18n();
const authStore = useAuthStore();
const usersStore = useUsersStore();

// Modals state
const showUserModal = ref(false);
const showDeleteModal = ref(false);
const selectedUser = ref<UserResponse | null>(null);

// Local filters
const searchQuery = ref('');
const selectedRole = ref('');

const roles = [
  { value: '', label: t('common.filter') },
  { value: 'admin', label: t('users.roles.admin') },
  { value: 'manager', label: t('users.roles.manager') },
  { value: 'user', label: t('users.roles.user') },
  { value: 'guest', label: t('users.roles.guest') },
];

const fetchUsers = async () => {
  usersStore.setFilters({
    search: searchQuery.value,
    role: selectedRole.value as any,
  });
  await usersStore.fetchUsers();
};

const handleCreateUser = () => {
  selectedUser.value = null;
  showUserModal.value = true;
};

const handleEditUser = (user: UserResponse) => {
  selectedUser.value = user;
  showUserModal.value = true;
};

const handleDeleteUser = (user: UserResponse) => {
  if (user.id === authStore.user?.id) {
    usersStore.error = t('users.delete.cannotDeleteSelf');
    return;
  }
  selectedUser.value = user;
  showDeleteModal.value = true;
};

const handleUserSuccess = async () => {
  await fetchUsers();
  showUserModal.value = false;
  selectedUser.value = null;
};

const handleDeleteConfirm = async () => {
  if (!selectedUser.value) return;
  
  try {
    await usersStore.deleteUser(selectedUser.value.id);
    showDeleteModal.value = false;
    selectedUser.value = null;
  } catch (err) {
    console.error('Error deleting user:', err);
  }
};

const getRoleBadgeColor = (role: string) => {
  const colors: Record<string, string> = {
    admin: 'bg-red-100 text-red-800',
    manager: 'bg-blue-100 text-blue-800',
    user: 'bg-green-100 text-green-800',
    guest: 'bg-gray-100 text-gray-800',
  };
  return colors[role] || colors.guest;
};

const formatDate = (dateString: string | null): string => {
  if (!dateString) return t('users.list.never');
  return new Date(dateString).toLocaleDateString();
};

const clearFilters = () => {
  searchQuery.value = '';
  selectedRole.value = '';
  usersStore.clearFilters();
  fetchUsers();
};

// Watch filters
watch([searchQuery, selectedRole], () => {
  fetchUsers();
}, { debounce: 300 } as any);

onMounted(() => {
  fetchUsers();
});
</script>

<template>
  <AppLayout>
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">{{ t('users.title') }}</h1>
          <p class="text-gray-600 mt-1">{{ t('users.subtitle') }}</p>
        </div>
        <button @click="handleCreateUser" class="btn-primary flex items-center gap-2">
          <Plus class="w-5 h-5" />
          <span>{{ t('users.newUser') }}</span>
        </button>
      </div>

      <!-- Filters -->
      <div class="card mb-6">
        <div class="flex items-center gap-2 mb-4">
          <Filter class="w-5 h-5 text-gray-500" />
          <h3 class="font-medium text-gray-900">{{ t('common.filter') }}</h3>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- Search -->
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('common.search') }}
            </label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search class="h-5 w-5 text-gray-400" />
              </div>
              <input
                v-model="searchQuery"
                type="text"
                :placeholder="t('users.list.username') + ' / ' + t('users.list.email')"
                class="input-field pl-10"
              />
            </div>
          </div>
          <!-- Role filter -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              {{ t('users.list.role') }}
            </label>
            <select v-model="selectedRole" class="input-field">
              <option v-for="role in roles" :key="role.value" :value="role.value">
                {{ role.label }}
              </option>
            </select>
          </div>
        </div>
        <div v-if="usersStore.hasFilters" class="mt-4">
          <button @click="clearFilters" class="text-sm text-primary-600 hover:text-primary-700">
            {{ t('software.clearFilters') }}
          </button>
        </div>
      </div>

      <!-- Error message -->
      <div v-if="usersStore.error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
        <p class="text-sm text-red-800">{{ usersStore.error }}</p>
      </div>

      <!-- Loading -->
      <div v-if="usersStore.isLoading" class="flex items-center justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>

      <!-- Empty state -->
      <div v-else-if="usersStore.usersList.length === 0" class="card text-center py-12">
        <UsersIcon class="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">
          {{ t('users.list.noUsers') }}
        </h3>
      </div>

      <!-- Users table -->
      <div v-else class="table-container">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('users.list.username') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('users.list.email') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('users.list.role') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('users.list.status') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('users.list.lastLogin') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {{ t('users.list.actions') }}
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="user in usersStore.usersList" :key="user.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full flex items-center justify-center" style="background-color: var(--color-primary-100)">
                    <span class="font-semibold text-sm" style="color: var(--color-primary-700)">
                      {{ user.username.charAt(0).toUpperCase() }}
                    </span>
                  </div>
                  <div>
                    <div class="text-sm font-medium text-gray-900">{{ user.username }}</div>
                    <div v-if="user.full_name" class="text-sm text-gray-500">{{ user.full_name }}</div>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ user.email }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="['px-2.5 py-0.5 rounded-full text-xs font-medium', getRoleBadgeColor(user.role)]">
                  {{ t(`users.roles.${user.role}`) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span :class="[
                  'px-2.5 py-0.5 rounded-full text-xs font-medium',
                  user.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                ]">
                  {{ user.is_active ? t('users.list.active') : t('users.list.inactive') }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ formatDate(user.last_login) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm">
                <div class="flex items-center gap-2">
                  <button 
                    @click="handleEditUser(user)"
                    class="text-primary-600 hover:text-primary-700" 
                    :title="t('users.list.edit')"
                  >
                    <Edit class="w-4 h-4" />
                  </button>
                  <button 
                    v-if="user.id !== authStore.user?.id"
                    @click="handleDeleteUser(user)"
                    class="text-red-600 hover:text-red-700" 
                    :title="t('users.list.delete')"
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
      <div v-if="usersStore.totalPages > 1" class="mt-6 flex items-center justify-between">
        <div class="text-sm text-gray-700">
          {{ t('common.showing') }}
          <span class="font-medium">{{ ((usersStore.currentPage - 1) * usersStore.pageSize) + 1 }}</span>
          {{ t('common.to') }}
          <span class="font-medium">{{ Math.min(usersStore.currentPage * usersStore.pageSize, usersStore.totalItems) }}</span>
          {{ t('common.of') }}
          <span class="font-medium">{{ usersStore.totalItems }}</span>
          {{ t('common.results') }}
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="usersStore.setPage(usersStore.currentPage - 1); fetchUsers()"
            :disabled="usersStore.currentPage === 1"
            class="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('common.previous') }}
          </button>
          <span class="text-sm text-gray-700">
            {{ t('common.page') }} {{ usersStore.currentPage }} {{ t('common.of') }} {{ usersStore.totalPages }}
          </span>
          <button
            @click="usersStore.setPage(usersStore.currentPage + 1); fetchUsers()"
            :disabled="usersStore.currentPage === usersStore.totalPages"
            class="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ t('common.next') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <UserFormModal
      :show="showUserModal"
      :user="selectedUser"
      @close="showUserModal = false; selectedUser = null"
      @success="handleUserSuccess"
    />
    
    <DeleteConfirmModal
      :show="showDeleteModal"
      :title="t('users.delete.title')"
      :message="t('users.delete.message')"
      @close="showDeleteModal = false; selectedUser = null"
      @confirm="handleDeleteConfirm"
    />
  </AppLayout>
</template>