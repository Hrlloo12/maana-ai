import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#081126",
          900: "#0c1a3a",
          800: "#13254d",
          700: "#1d3363",
          600: "#2c4479",
          500: "#4a5f8f",
          400: "#7484a8",
          300: "#a3aec7",
        },
        sand: {
          50: "#fbf8f2",
          100: "#f5f0e6",
          200: "#ebe3d3",
          300: "#ddd2bc",
        },
        emerald: {
          50: "#ebf5f2",
          100: "#d3ebe4",
          200: "#a8d6c9",
          500: "#1b8a74",
          600: "#147563",
          700: "#0f5e50",
          800: "#0b4a3f",
        },
        gold: {
          50: "#faf4e6",
          100: "#f3e6c6",
          300: "#dcc18a",
          500: "#b48f45",
          600: "#977535",
          700: "#7a5e2a",
        },
        clay: {
          50: "#fbefeb",
          100: "#f5dcd4",
          500: "#b5543a",
          600: "#9a432c",
          700: "#7e3623",
        },
        amber: {
          50: "#fcf5e7",
          100: "#f8e8c5",
          500: "#c08a1e",
          600: "#9c6f16",
          700: "#7c5812",
        },
      },
      fontFamily: {
        sans: ["IBM Plex Sans Arabic", "Inter", "system-ui", "sans-serif"],
        latin: ["Inter", "IBM Plex Sans Arabic", "system-ui", "sans-serif"],
        display: ["Amiri", "IBM Plex Sans Arabic", "serif"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(12,26,58,0.04), 0 8px 24px -12px rgba(12,26,58,0.12)",
        lift: "0 2px 4px rgba(12,26,58,0.05), 0 18px 40px -18px rgba(12,26,58,0.25)",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        breathe: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(27,138,116,0.35)" },
          "50%": { boxShadow: "0 0 0 8px rgba(27,138,116,0)" },
        },
      },
      animation: {
        fadeUp: "fadeUp .5s ease-out both",
        breathe: "breathe 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
