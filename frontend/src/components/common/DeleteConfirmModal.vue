<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import BaseModal from '@/components/common/BaseModal.vue';
import { AlertTriangle } from 'lucide-vue-next';

interface Props {
  show: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  isDangerous?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  confirmText: '',
  cancelText: '',
  isDangerous: true,
});

const emit = defineEmits<{
  close: [];
  confirm: [];
}>();

const { t } = useI18n();
const isDeleting = ref(false);

const handleConfirm = async () => {
  isDeleting.value = true;
  emit('confirm');
  // Note: parent component should close the modal after delete completes
};
</script>

<template>
  <BaseModal
    :show="show"
    :title="title"
    size="sm"
    @close="emit('close')"
  >
    <div class="flex items-start gap-4">
      <div
        :class="[
          'w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0',
          isDangerous ? 'bg-red-100' : 'bg-yellow-100'
        ]"
      >
        <AlertTriangle
          :class="[
            'w-6 h-6',
            isDangerous ? 'text-red-600' : 'text-yellow-600'
          ]"
        />
      </div>

      <div class="flex-1">
        <p class="text-sm text-gray-700">{{ message }}</p>
        
        <div v-if="isDangerous" class="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p class="text-xs font-medium text-red-800">
            ⚠️ This action cannot be undone
          </p>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-end gap-3">
        <button
          type="button"
          @click="emit('close')"
          class="btn-secondary"
          :disabled="isDeleting"
        >
          {{ cancelText || t('common.cancel') }}
        </button>
        <button
          type="button"
          @click="handleConfirm"
          :class="[
            'btn-danger',
            { 'opacity-50 cursor-not-allowed': isDeleting }
          ]"
          :disabled="isDeleting"
        >
          <span v-if="isDeleting">{{ t('common.loading') }}</span>
          <span v-else>{{ confirmText || t('common.delete') }}</span>
        </button>
      </div>
    </template>
  </BaseModal>
</template>