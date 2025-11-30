<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { Globe, Check } from 'lucide-vue-next';
import { AVAILABLE_LOCALES, setLocale, type LocaleCode } from '@/i18n';

const { locale } = useI18n();
const isOpen = ref(false);

// Exponer el código de idioma actual de forma clara para evitar comparaciones con Ref.
const currentCode = computed(() => locale.value);

const currentLanguage = computed(() => {
  return AVAILABLE_LOCALES.find(l => l.code === currentCode.value);
});

const toggle = (e?: Event) => {
  e?.stopPropagation();
  isOpen.value = !isOpen.value;
};

const changeLanguage = (code: LocaleCode) => {
  // Actualiza ambos: la utilidad central y la instancia de i18n local
  try {
    setLocale(code);
  } catch {
    // silenciar si setLocale no existe o falla; igualmente forzamos locale.value
  }
  locale.value = code;
  isOpen.value = false;
};

// Cerrar dropdown al hacer clic fuera
function onDocumentClick(e: MouseEvent) {
  const target = e.target as HTMLElement | null;
  if (!target || !target.closest('.language-selector')) {
    isOpen.value = false;
  }
}

onMounted(() => document.addEventListener('click', onDocumentClick));
onBeforeUnmount(() => document.removeEventListener('click', onDocumentClick));
</script>

<template>
  <div class="relative inline-block language-selector">
    <!-- Trigger button -->
    <button
      type="button"
      @click.stop="toggle"
      class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
      :title="`Language: ${currentLanguage?.nativeName ?? currentCode}`"
      :aria-expanded="isOpen"
      aria-haspopup="true"
    >
      <Globe class="w-5 h-5 text-gray-600" />
      <span class="text-sm font-medium text-gray-700 uppercase">
        {{ currentCode }}
      </span>
    </button>

    <!-- Dropdown menu -->
    <div
      v-if="isOpen"
      class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50"
      role="menu"
      aria-orientation="vertical"
    >
      <button
        v-for="lang in AVAILABLE_LOCALES"
        :key="lang.code"
        type="button"
        @click.stop="changeLanguage(lang.code)"
        :class="[
          'w-full flex items-center justify-between px-4 py-2 text-sm transition-colors',
          lang.code === currentCode ? 'bg-primary-50 text-primary-700' : 'text-gray-700 hover:bg-gray-50'
        ]"
        :aria-current="lang.code === currentCode"
      >
        <span>{{ lang.nativeName }}</span>
        <Check
          v-if="lang.code === currentCode"
          class="w-4 h-4 text-primary-600"
        />
      </button>
    </div>
  </div>
</template>