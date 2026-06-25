/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist Variable', 'Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#f4f6fb',
          100: '#e7ebf4',
          200: '#cdd5e4',
          300: '#aab8d0',
          400: '#8096b7',
          500: '#5b7296',
          600: '#425471',
          700: '#2d3b52',
          800: '#1d2535',
          900: '#111722',
          DEFAULT: '#1a1f2e',
          hover: '#2e3547',
        },
        'slate-ink': '#0f1117',
        surface: '#FAFAFA',
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
      },
      borderRadius: {
        DEFAULT: '0.375rem',
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
        'float-slow': 'float 8s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:  { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        fadeUp:  { '0%': { opacity: '0', transform: 'translateY(20px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        slideUp: { '0%': { opacity: '0', transform: 'translateY(16px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        scaleIn:  { '0%': { opacity: '0', transform: 'scale(0.96)' }, '100%': { opacity: '1', transform: 'scale(1)' } },
        shimmer:  { '0%': { backgroundPosition: '0% center' }, '100%': { backgroundPosition: '200% center' } },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
    },
  },
  plugins: [],
}
