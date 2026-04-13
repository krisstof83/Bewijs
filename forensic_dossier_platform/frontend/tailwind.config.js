/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        panel: '#121726',
        ink: '#E5E7EB',
        accent: '#38BDF8'
      }
    }
  },
  plugins: []
}
