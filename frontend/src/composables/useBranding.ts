import { ref, readonly } from 'vue';
import type { BrandingConfig } from '@/types/branding';
import { DEFAULT_BRANDING } from '@/types/branding';

// Estado global del branding
const brandingConfig = ref<BrandingConfig>(DEFAULT_BRANDING);
const isLoaded = ref(false);
const loadError = ref<string | null>(null);

/**
 * Composable para acceder y gestionar el branding de la aplicación
 */
export function useBranding() {
  /**
   * Cargar configuración de branding desde config.json
   */
  const loadBranding = async (): Promise<void> => {
    try {
      const response = await fetch('/config.json');
      
      if (!response.ok) {
        throw new Error(`Failed to load branding config: ${response.statusText}`);
      }

      const config: BrandingConfig = await response.json();
      brandingConfig.value = { ...DEFAULT_BRANDING, ...config };
      
      // Aplicar colores CSS
      applyColors(config.colors);
      
      // Aplicar nombre de la app al título
      if (config.appName) {
        document.title = config.appName;
      }

      isLoaded.value = true;
      loadError.value = null;
    } catch (error) {
      console.warn('Failed to load branding config, using defaults:', error);
      loadError.value = error instanceof Error ? error.message : 'Unknown error';
      
      // Usar configuración por defecto
      brandingConfig.value = DEFAULT_BRANDING;
      applyColors(DEFAULT_BRANDING.colors);
      isLoaded.value = true;
    }
  };

  /**
   * Aplicar colores al CSS
   */
  const applyColors = (colors: BrandingConfig['colors']): void => {
    const root = document.documentElement;

    // Aplicar colores primarios
    Object.entries(colors.primary).forEach(([shade, color]) => {
      root.style.setProperty(`--color-primary-${shade}`, color);
    });

    // Aplicar colores secundarios
    Object.entries(colors.secondary).forEach(([shade, color]) => {
      root.style.setProperty(`--color-secondary-${shade}`, color);
    });
  };

  /**
   * Obtener URL del logo principal
   */
  const getLogoUrl = (): string => {
    return brandingConfig.value.logo.main;
  };

  /**
   * Obtener URL del icono/favicon
   */
  const getIconUrl = (): string => {
    return brandingConfig.value.logo.icon;
  };

  /**
   * Obtener nombre de la aplicación
   */
  const getAppName = (): string => {
    return brandingConfig.value.appName;
  };

  /**
   * Obtener configuración del footer
   */
  const getFooterText = (): string => {
    const { text, showYear } = brandingConfig.value.footer;
    if (showYear) {
      return `© ${new Date().getFullYear()} ${text}`;
    }
    return text;
  };

  /**
   * Obtener configuración de fondo del login
   */
  const getLoginBackground = () => {
    return brandingConfig.value.login;
  };

  return {
    // State (readonly)
    branding: readonly(brandingConfig),
    isLoaded: readonly(isLoaded),
    loadError: readonly(loadError),

    // Methods
    loadBranding,
    getLogoUrl,
    getIconUrl,
    getAppName,
    getFooterText,
    getLoginBackground,
  };
}