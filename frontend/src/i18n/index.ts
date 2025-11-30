import { createI18n } from 'vue-i18n';
import en from '@/locales/en.json';
import es from '@/locales/es.json';

// Tipos para autocompletado
export type MessageSchema = typeof en;

// Idiomas disponibles
export const AVAILABLE_LOCALES = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'es', name: 'Spanish', nativeName: 'Español' },
  // Añadir euskera más adelante:
  // { code: 'eu', name: 'Basque', nativeName: 'Euskara' },
] as const;

export type LocaleCode = typeof AVAILABLE_LOCALES[number]['code'];

// Obtener idioma por defecto
const getDefaultLocale = (): LocaleCode => {
  // 1. Comprobar localStorage
  const saved = localStorage.getItem('locale');
  if (saved && AVAILABLE_LOCALES.some(l => l.code === saved)) {
    return saved as LocaleCode;
  }

  // 2. Comprobar idioma del navegador
  const browserLang = navigator.language.split('-')[0];
  if (AVAILABLE_LOCALES.some(l => l.code === browserLang)) {
    return browserLang as LocaleCode;
  }

  // 3. Fallback a inglés
  return 'en';
};

// Crear instancia de i18n
const i18n = createI18n<[MessageSchema], LocaleCode>({
  legacy: false, // Usar Composition API
  locale: getDefaultLocale(),
  fallbackLocale: 'en',
  messages: {
    en,
    es,
    // Añadir euskera más adelante:
    // eu,
  },
  globalInjection: true, // Usar $t en templates
  missingWarn: import.meta.env.DEV, // Avisar de traducciones faltantes solo en dev
  fallbackWarn: import.meta.env.DEV,
});

export default i18n;

// Helper para cambiar idioma
export const setLocale = (locale: LocaleCode) => {
  i18n.global.locale.value = locale;
  localStorage.setItem('locale', locale);
  
  // Actualizar atributo lang del HTML
  document.documentElement.setAttribute('lang', locale);
};

// Helper para obtener idioma actual
export const getCurrentLocale = (): LocaleCode => {
  return i18n.global.locale.value;
};