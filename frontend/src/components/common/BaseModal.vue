<script setup lang="ts">
import { X } from 'lucide-vue-next';

interface Props {
  show: boolean;
  title: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showClose?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  showClose: true,
});

const emit = defineEmits<{
  close: [];
}>();

const sizeClasses = {
  sm: 'max-w-md',
  md: 'max-w-2xl',
  lg: 'max-w-4xl',
  xl: 'max-w-6xl',
};

const handleBackdropClick = (e: MouseEvent) => {
  if ((e.target as HTMLElement).classList.contains('modal-backdrop')) {
    emit('close');
  }
};
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="show"
        class="modal-backdrop fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
        @click="handleBackdropClick"
      >
        <Transition
          enter-active-class="transition ease-out duration-300"
          enter-from-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
          enter-to-class="opacity-100 translate-y-0 sm:scale-100"
          leave-active-class="transition ease-in duration-200"
          leave-from-class="opacity-100 translate-y-0 sm:scale-100"
          leave-to-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
        >
          <div
            v-if="show"
            :class="['bg-white rounded-lg shadow-xl w-full', sizeClasses[size]]"
            @click.stop
          >
            <!-- Header -->
            <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h2 class="text-xl font-semibold text-gray-900">{{ title }}</h2>
              <button
                v-if="showClose"
                @click="emit('close')"
                class="p-1 rounded-md hover:bg-gray-100 transition-colors"
              >
                <X class="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <!-- Body -->
            <div class="px-6 py-4 max-h-[70vh] overflow-y-auto">
              <slot />
            </div>

            <!-- Footer -->
            <div v-if="$slots.footer" class="px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-lg">
              <slot name="footer" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>