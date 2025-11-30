<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseModal from '@/components/common/BaseModal.vue';
import apiClient, { handleApiError } from '@/api/client';
import type { UserResponse } from '@/api/api';
import { AlertCircle } from 'lucide-vue-next';

interface Props {
  show: boolean;
  user?: UserResponse | null;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  close: [];
  success: [];
}>();

const { t } = useI18n();

const form = ref({
  username: '',
  email: '',
  full_name: '',
  role: 'guest' as 'admin' | 'manager' | 'user' | 'guest',
  password: '',
  is_active: true,
});

const isSubmitting = ref(false);
const error = ref<string | null>(null);

const isEditMode = computed(() => !!props.user);

const roles = [
  { value: 'admin', label: t('users.roles.admin') },
  { value: 'manager', label: t('users.roles.manager') },
  { value: 'user', label: t('users.roles.user') },
  { value: 'guest', label: t('users.roles.guest') },
];

watch(() => props.show, (show) => {
  if (show && props.user) {
    // Edit mode: populate form
    form.value = {
      username: props.user.username,
      email: props.user.email,
      full_name: props.user.full_name || '',
      role: props.user.role as any,
      password: '',
      is_active: props.user.is_active,
    };
  } else if (show) {
    // Create mode: reset form
    form.value = {
      username: '',
      email: '',
      full_name: '',
      role: 'guest',
      password: '',
      is_active: true,
    };
  }
  error.value = null;
});

const handleSubmit = async () => {
  // Validation
  if (!form.value.username || !form.value.email) {
    error.value = 'Username and email are required';
    return;
  }

  if (!isEditMode.value && !form.value.password) {
    error.value = 'Password is required for new users';
    return;
  }

  isSubmitting.value = true;
  error.value = null;

  try {
    if (isEditMode.value && props.user) {
      // Update user
      await apiClient.users.updateUser(props.user.id, {
        email: form.value.email,
        full_name: form.value.full_name || undefined,
        role: form.value.role,
        is_active: form.value.is_active,
      });
    } else {
      // Create user
      await apiClient.users.createUser({
        username: form.value.username,
        email: form.value.email,
        full_name: form.value.full_name || undefined,
        role: form.value.role,
        password: form.value.password || undefined,
      });
    }

    emit('success');
    emit('close');
  } catch (err) {
    const apiError = handleApiError(err);
    error.value = apiError.message;
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <BaseModal
    :show="show"
    :title="isEditMode ? t('users.form.title') : t('users.newUser')"
    size="md"
    @close="emit('close')"
  >
    <!-- Error message -->
    <div v-if="error" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
      <AlertCircle class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <p class="text-sm text-red-800">{{ error }}</p>
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Username -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('users.form.username') }} *
        </label>
        <input
          v-model="form.username"
          type="text"
          required
          :disabled="isEditMode"
          class="input-field"
          :class="{ 'bg-gray-100': isEditMode }"
        />
        <p v-if="isEditMode" class="text-xs text-gray-500 mt-1">
          Username cannot be changed
        </p>
      </div>

      <!-- Email -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('users.form.email') }} *
        </label>
        <input
          v-model="form.email"
          type="email"
          required
          class="input-field"
        />
      </div>

      <!-- Full Name -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('users.form.fullName') }}
        </label>
        <input
          v-model="form.full_name"
          type="text"
          class="input-field"
        />
      </div>

      <!-- Role -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('users.form.role') }} *
        </label>
        <select v-model="form.role" required class="input-field">
          <option v-for="role in roles" :key="role.value" :value="role.value">
            {{ role.label }}
          </option>
        </select>
      </div>

      <!-- Password (only for create or if changing) -->
      <div v-if="!isEditMode">
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ t('users.form.password') }} *
        </label>
        <input
          v-model="form.password"
          type="password"
          :required="!isEditMode"
          class="input-field"
          minlength="8"
        />
        <p class="text-xs text-gray-500 mt-1">
          Minimum 8 characters
        </p>
      </div>

      <!-- Is Active (only for edit) -->
      <div v-if="isEditMode">
        <label class="flex items-center gap-2 cursor-pointer">
          <input
            v-model="form.is_active"
            type="checkbox"
            class="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
          />
          <span class="text-sm font-medium text-gray-700">
            {{ t('users.form.isActive') }}
          </span>
        </label>
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
          {{ t('users.form.cancel') }}
        </button>
        <button
          type="submit"
          @click="handleSubmit"
          class="btn-primary"
          :disabled="isSubmitting"
        >
          <span v-if="isSubmitting">{{ t('common.loading') }}</span>
          <span v-else>{{ t('users.form.save') }}</span>
        </button>
      </div>
    </template>
  </BaseModal>
</template>