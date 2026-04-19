/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        // Legacy primary (kept for compatibility with other pages)
        primary: {
          50:  '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        // Industrial palette
        iron: {
          950: '#1a1a1a',
          900: '#242424',
          800: '#2e2e2e',
          700: '#3a3a3a',
          600: '#484848',
        },
        steel: {
          700: '#455a64',
          600: '#546e7a',
          500: '#607d8b',
          400: '#78909c',
          300: '#90a4ae',
          200: '#b0bec5',
          100: '#cfd8dc',
        },
        rust: {
          800: '#9e2b0b',
          700: '#bf360c',
          600: '#e64a19',
          500: '#f4511e',
          400: '#ff7043',
          300: '#ff8a65',
        },
        bone: '#f0ebe3',
      },
      fontFamily: {
        display: ['"Bebas Neue"', 'Impact', 'Arial Narrow', 'sans-serif'],
        mono:    ['"IBM Plex Mono"', '"Fira Mono"', 'monospace'],
      },
      backgroundImage: {
        'grid-iron': `
          linear-gradient(rgba(84,110,122,0.07) 1px, transparent 1px),
          linear-gradient(90deg, rgba(84,110,122,0.07) 1px, transparent 1px)
        `,
        'noise': "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E\")",
      },
      backgroundSize: {
        'grid': '32px 32px',
      },
      letterSpacing: {
        'industrial': '0.15em',
        'widest2': '0.25em',
      },
      clipPath: {
        'card': 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)',
        'btn':  'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
