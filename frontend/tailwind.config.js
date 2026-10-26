/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        spotify: {
          green: "#1db954",
          light: "#1ed760",
          dark: "#121212",
          gray: "#282828",
          lightgray: "#b3b3b3"
        }
      }
    },
  },
  plugins: [],
}
