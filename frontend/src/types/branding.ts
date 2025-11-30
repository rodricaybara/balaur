export interface BrandingConfig {
  appName: string;
  colors: {
    primary: {
      50: string;
      100: string;
      200: string;
      300: string;
      400: string;
      500: string;
      600: string;
      700: string;
      800: string;
      900: string;
    };
    secondary: {
      50: string;
      100: string;
      200: string;
      300: string;
      400: string;
      500: string;
      600: string;
      700: string;
      800: string;
      900: string;
    };
  };
  logo: {
    main: string; // Path to main logo
    icon: string; // Path to icon/favicon
  };
  login: {
    background: 'gradient' | 'image' | 'solid';
    backgroundImage?: string; // URL if background is 'image'
    backgroundColor?: string; // Color if background is 'solid'
  };
  footer: {
    text: string;
    showYear: boolean;
  };
}

export const DEFAULT_BRANDING: BrandingConfig = {
  appName: 'Balaur SMS',
  colors: {
    primary: {
      50: '#eff6ff',
      100: '#dbeafe',
      200: '#bfdbfe',
      300: '#93c5fd',
      400: '#60a5fa',
      500: '#3b82f6',
      600: '#2563eb',
      700: '#1d4ed8',
      800: '#1e40af',
      900: '#1e3a8a',
    },
    secondary: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a',
    },
  },
  logo: {
    main: '/assets/branding/logo.svg',
    icon: '/favicon.ico',
  },
  login: {
    background: 'gradient',
  },
  footer: {
    text: 'University. All rights reserved.',
    showYear: true,
  },
};