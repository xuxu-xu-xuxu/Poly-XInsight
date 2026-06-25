import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: "#1a2744",
          light: "#eef2f8",
        },
        nav: "#1a2744",
        surface: "#fafafa",
      },
      fontFamily: {
        heading: ["Georgia", "'Times New Roman'", "serif"],
        mono: ["'Courier New'", "monospace"],
      },
      borderRadius: {
        bubble: "12px",
      },
    },
  },
  plugins: [],
};
export default config;
