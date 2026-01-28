/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0f0f23',
        'bg-secondary': '#1a1a35',
        'bg-card': '#24243e',
        'accent-primary': '#6366f1',
        'accent-secondary': '#a855f7',
        'accent-success': '#22c55e',
        'accent-warning': '#eab308',
        'accent-error': '#ef4444',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite',
        'shake': 'shake 0.5s cubic-bezier(.36,.07,.19,.97) both',
      },
      keyframes: {
        glow: {
          '0%, 100%': { 
            boxShadow: '0 0 20px rgba(99, 102, 241, 0.3)' 
          },
          '50%': { 
            boxShadow: '0 0 40px rgba(168, 85, 247, 0.5)' 
          },
        },
        shake: {
          '10%, 90%': { transform: 'translate3d(-1px, 0, 0)' },
          '20%, 80%': { transform: 'translate3d(2px, 0, 0)' },
          '30%, 50%, 70%': { transform: 'translate3d(-4px, 0, 0)' },
          '40%, 60%': { transform: 'translate3d(4px, 0, 0)' },
        },
      },
    },
  },
  plugins: [],
};
