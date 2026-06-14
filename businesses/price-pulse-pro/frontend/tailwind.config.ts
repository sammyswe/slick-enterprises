import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0f1419",
          raised: "#161b22",
          overlay: "#1c2128",
        },
        accent: {
          DEFAULT: "#3b82f6",
          muted: "#2563eb",
        },
        border: "#30363d",
        muted: "#9aa0a6",
      },
    },
  },
  plugins: [],
};

export default config;
