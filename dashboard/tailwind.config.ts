import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0c10",
        panel: "#12151c",
        border: "#1f2530",
        muted: "#8b94a7",
        bull: "#22c55e",
        bear: "#ef4444",
        neutral: "#eab308",
        watch: "#3b82f6",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
