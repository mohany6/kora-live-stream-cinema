/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        live: {
          DEFAULT: "#dc2626",
          soft: "#dc262629",
        },
        countdown: {
          DEFAULT: "#16a34a",
          soft: "#16a34a29",
        },
        pitch: {
          DEFAULT: "#15803d",
          deep: "#14532d",
        },
        brand: {
          DEFAULT: "#0ea5e9",
          hover: "#0284c7",
        },
        surface: {
          light: "#ffffff",
          "light-raised": "#f1f5f9",
          dark: "#111c31",
          "dark-raised": "#1e293b",
        },
      },
      fontFamily: {
        arabic: ['"Cairo"', '"Tajawal"', '"Noto Kufi Arabic"', "sans-serif"],
        latin: ['"Inter"', "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 10px 30px -18px rgba(2, 6, 23, 0.45)",
        "card-hover": "0 18px 45px -20px rgba(2, 6, 23, 0.55)",
        player: "0 18px 50px -24px rgba(2, 6, 23, 0.65)",
      },
      keyframes: {
        "live-pulse": {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(220, 38, 38, 0.55)" },
          "50%": { boxShadow: "0 0 0 7px rgba(220, 38, 38, 0)" },
        },
      },
      animation: {
        "live-pulse": "live-pulse 1.6s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};
