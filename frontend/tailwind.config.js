/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f4f1ea",
        ink: "#1c1915",
        pine: "#0f6e56",
        line: "#e4ddd0",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "sans-serif"],
        serif: ["Source Serif 4", "serif"],
      },
    },
  },
  plugins: [],
};
