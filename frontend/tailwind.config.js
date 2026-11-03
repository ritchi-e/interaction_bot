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
        phonwa: {
          cream: "#FDFBF7",
          saffron: "#FF9933",
          marigold: "#FFC83B",
          teal: "#10A3A4",
          indigo: "#1E5A9B",
          terracotta: "#C45C26",
          ink: "#2A2218",
          chalk: "#FFF8E8",
        },
      },
      fontFamily: {
        sans: ["Nunito", "IBM Plex Sans", "sans-serif"],
        serif: ["Source Serif 4", "serif"],
        display: ["Playpen Sans", "cursive"],
        hindi: ["Baloo 2", "Noto Sans Devanagari", "sans-serif"],
      },
      keyframes: {
        "phonwa-float": {
          "0%, 100%": { transform: "translateY(0px) rotate(-1deg)" },
          "50%": { transform: "translateY(-10px) rotate(1.5deg)" },
        },
        "phonwa-wiggle": {
          "0%, 100%": { transform: "rotate(-2deg)" },
          "50%": { transform: "rotate(2deg)" },
        },
        "phonwa-pop": {
          "0%, 100%": { transform: "scale(1)" },
          "50%": { transform: "scale(1.04)" },
        },
        "phonwa-rickshaw": {
          "0%, 100%": { transform: "translateX(0)" },
          "50%": { transform: "translateX(6px)" },
        },
      },
      animation: {
        "phonwa-float": "phonwa-float 4.2s ease-in-out infinite",
        "phonwa-wiggle": "phonwa-wiggle 3.4s ease-in-out infinite",
        "phonwa-pop": "phonwa-pop 2.8s ease-in-out infinite",
        "phonwa-rickshaw": "phonwa-rickshaw 5s ease-in-out infinite",
      },
      borderRadius: {
        doodle: "255px 15px 225px 15px / 15px 225px 15px 255px",
        "doodle-sm": "40px 12px 36px 14px / 12px 36px 14px 40px",
      },
      boxShadow: {
        doodle: "3px 3px 0 rgba(42, 34, 24, 0.12)",
        "doodle-lg": "5px 5px 0 rgba(42, 34, 24, 0.14)",
      },
    },
  },
  plugins: [],
};
