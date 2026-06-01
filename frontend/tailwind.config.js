/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Brand & Accent
        primary: '#0066cc',
        'primary-focus': '#0071e3',
        'primary-on-dark': '#2997ff',
        // Surface
        canvas: '#ffffff',
        'canvas-parchment': '#f5f5f7',
        'surface-pearl': '#fafafc',
        'surface-tile-1': '#272729',
        'surface-tile-2': '#2a2a2c',
        'surface-tile-3': '#252527',
        'surface-black': '#000000',
        // Text
        ink: '#1d1d1f',
        'body-on-dark': '#ffffff',
        'body-muted': '#cccccc',
        'ink-muted-80': '#333333',
        'ink-muted-48': '#7a7a7a',
        // Borders
        'divider-soft': 'rgba(0,0,0,0.08)',
        hairline: '#e0e0e0',
      },
      fontFamily: {
        display: ['"Inter"', '"SF Pro Display"', 'system-ui', '-apple-system', 'sans-serif'],
        body: ['"Inter"', '"SF Pro Text"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      fontSize: {
        'hero': ['56px', { lineHeight: '1.07', letterSpacing: '0', fontWeight: '600' }],
        'display-lg': ['40px', { lineHeight: '1.10', letterSpacing: '0px', fontWeight: '600' }],
        'display-md': ['34px', { lineHeight: '1.47', letterSpacing: '0', fontWeight: '600' }],
        'lead': ['28px', { lineHeight: '1.14', letterSpacing: '0.196px', fontWeight: '400' }],
        'lead-airy': ['24px', { lineHeight: '1.5', letterSpacing: '0px', fontWeight: '300' }],
        'tagline': ['21px', { lineHeight: '1.19', letterSpacing: '0.231px', fontWeight: '600' }],
        'body-strong': ['17px', { lineHeight: '1.24', letterSpacing: '0', fontWeight: '600' }],
        'body': ['17px', { lineHeight: '1.47', letterSpacing: '0', fontWeight: '400' }],
        'dense-link': ['17px', { lineHeight: '2.41', letterSpacing: '0px', fontWeight: '400' }],
        'caption': ['14px', { lineHeight: '1.43', letterSpacing: '0', fontWeight: '400' }],
        'caption-strong': ['14px', { lineHeight: '1.29', letterSpacing: '0', fontWeight: '600' }],
        'fine-print': ['12px', { lineHeight: '1.0', letterSpacing: '0', fontWeight: '400' }],
        'nav-link': ['12px', { lineHeight: '1.0', letterSpacing: '0', fontWeight: '400' }],
      },
      spacing: {
        'xxs': '4px',
        'xs': '8px',
        'sm': '12px',
        'md': '17px',
        'lg': '24px',
        'xl': '32px',
        'xxl': '48px',
        'section': '80px',
      },
      borderRadius: {
        'none': '0px',
        'xs': '5px',
        'sm': '8px',
        'md': '11px',
        'lg': '18px',
        'pill': '9999px',
        'full': '50%',
      },
      boxShadow: {
        'product': 'rgba(0, 0, 0, 0.22) 3px 5px 30px 0',
        'hairline': '0 0 0 1px rgba(0, 0, 0, 0.08)',
      },
      backdropBlur: {
        'nav': '20px',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-dot': 'pulseDot 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
      },
    },
  },
  plugins: [],
}
