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
          // Light landing surface
          snow: "#F5F9FB",
          mist: "#E8F1F4",
          ink: "#0B1220",
          mute: "#5B6B7C",
          line: "#D7E2EA",
          cyan: "#06B6C4",
          "cyan-deep": "#0891B2",
          teal: "#0F766E",
          navy: "#0B3A4A",
          glow: "rgba(6, 182, 196, 0.18)",
          glass: "rgba(255, 255, 255, 0.72)",
          "glass-border": "rgba(15, 23, 42, 0.08)",
          // Legacy sketch theme (app/login)
          cream: "#FDFBF7",
          saffron: "#FF9933",
          marigold: "#FFC83B",
          indigo: "#1E5A9B",
          terracotta: "#C45C26",
          chalk: "#FFF8E8",
          midnight: "#0B0C10",
          ash: "#9CA3AF",
        },
      },
      fontFamily: {
        sans: ["Inter", "IBM Plex Sans", "Nunito", "sans-serif"],
        display: ["Plus Jakarta Sans", "Inter", "sans-serif"],
        serif: ["Source Serif 4", "serif"],
        hindi: ["Baloo 2", "Noto Sans Devanagari", "sans-serif"],
      },
      keyframes: {
        "phonwa-marquee": {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        "phonwa-float": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-8px)" },
        },
      },
      animation: {
        "phonwa-marquee": "phonwa-marquee 36s linear infinite",
        "phonwa-float": "phonwa-float 4.8s ease-in-out infinite",
      },
      borderRadius: {
        doodle: "255px 15px 225px 15px / 15px 225px 15px 255px",
        "doodle-sm": "40px 12px 36px 14px / 12px 36px 14px 40px",
      },
      boxShadow: {
        doodle: "3px 3px 0 rgba(42, 34, 24, 0.12)",
        "doodle-lg": "5px 5px 0 rgba(42, 34, 24, 0.14)",
        soft: "0 18px 50px -28px rgba(11, 58, 74, 0.35)",
        panel: "0 1px 0 rgba(255,255,255,0.7) inset, 0 20px 50px -30px rgba(11, 58, 74, 0.28)",
      },
    },
  },
  plugins: [],
};
