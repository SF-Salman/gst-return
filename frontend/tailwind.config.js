/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        inter: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        poppins: ['Poppins', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        neutral: {
          50: '#f9fafb',
          100: '#f3f4f6',
        },
      },
      boxShadow: {
        soft: '0 10px 20px rgba(0,0,0,0.08)',
      },
    },
  },
  plugins: [],
}