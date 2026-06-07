/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
        },
      },
      animation: {
        'fade-in':   'fadeIn 0.4s ease-out',
        'fade-up':   'fadeUp 0.6s ease-out both',
        'fade-up-d1':'fadeUp 0.6s ease-out 100ms both',
        'fade-up-d2':'fadeUp 0.6s ease-out 200ms both',
        'fade-up-d3':'fadeUp 0.6s ease-out 300ms both',
        'slide-up':  'slideUp 0.4s ease-out',
        'scale-in':  'scaleIn 0.35s ease-out both',
        'shimmer':   'shimmer 3s linear infinite',
        'pulse-slow':'pulse 2.5s cubic-bezier(0.4,0,0.6,1) infinite',
      },
      keyframes: {
        fadeIn:  { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        fadeUp:  { '0%': { opacity: '0', transform: 'translateY(20px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        slideUp: { '0%': { opacity: '0', transform: 'translateY(16px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        scaleIn:  { '0%': { opacity: '0', transform: 'scale(0.96)' }, '100%': { opacity: '1', transform: 'scale(1)' } },
        shimmer:  { '0%': { backgroundPosition: '0% center' }, '100%': { backgroundPosition: '200% center' } },
      },
    },
  },
  plugins: [],
}
