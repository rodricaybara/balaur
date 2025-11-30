import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import i18n from './i18n';
import { useBranding } from './composables/useBranding';
import './style.css';

// Función de inicialización asíncrona
const initApp = async () => {
  // Cargar configuración de branding
  const { loadBranding } = useBranding();
  await loadBranding();

  // Crear y configurar app
  const app = createApp(App);
  const pinia = createPinia();

  app.use(pinia);
  app.use(router);
  app.use(i18n);

  app.mount('#app');
};

// Iniciar aplicación
initApp().catch((error) => {
  console.error('Failed to initialize app:', error);
  // Montar app con configuración por defecto en caso de error
  const app = createApp(App);
  const pinia = createPinia();
  app.use(pinia);
  app.use(router);
  app.use(i18n);
  app.mount('#app');
});