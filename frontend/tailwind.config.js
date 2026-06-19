/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        serif: ['Lora', 'ui-serif', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        inter: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        poppins: ['Poppins', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        bg: 'var(--color-bg)',
        surf: 'var(--color-surf)',
        sub: 'var(--color-sub)',
        tx: 'var(--color-tx)',
        tx2: 'var(--color-tx2)',
        tx3: 'var(--color-tx3)',
        border: 'var(--color-border)',
        border2: 'var(--color-border2)',
        acc: 'var(--color-acc)',
        ok: 'var(--color-ok)',
        warn: 'var(--color-warn)',
        err: 'var(--color-err)',
        info: 'var(--color-info)',
        neutral: {
          50: '#f9fafb',
          100: '#f3f4f6',
        },
      },
      boxShadow: {
        soft: '0 2px 10px rgba(0,0,0,0.06)',
        hard: '0 0 0 1px var(--color-border)',
      },
    },
  },
  plugins: [],
}
