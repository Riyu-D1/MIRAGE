import type { Config } from "tailwindcss";

// MIRAGE obsidian design tokens — keep in sync with docs/DESIGN_SYSTEM.md
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: "#07080C",
        panel: "#0D0F16",
        elevated: "#141824",
        line: "#232A3D",
        ink: {
          primary: "#EDEFF5",
          secondary: "#9AA3B8",
        },
        accent: {
          cyan: "#37E0D8",
          violet: "#8B7CF6",
          crimson: "#FF3B5C",
          amber: "#FFB224",
          green: "#2FD67A",
          heat: "#FF7A18",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
      },
      keyframes: {
        "pulse-box": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
      },
      animation: {
        "pulse-box": "pulse-box 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
