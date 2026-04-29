/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['IBM Plex Sans', 'Segoe UI', 'Tahoma', 'sans-serif'],
        display: ['Rajdhani', 'Segoe UI', 'Tahoma', 'sans-serif'],
        mono: ['IBM Plex Mono', 'Consolas', 'monospace']
      }
    }
  },
  plugins: []
}
