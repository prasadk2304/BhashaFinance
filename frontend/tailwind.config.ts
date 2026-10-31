import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paytm: {
          navy: "#002E6E",
          blue: "#00BAF2",
          text: "#1B2A41",
          page: "#F5F7FA",
          card: "#FFFFFF",
          border: "#E1E8F0",
          success: "#0F9D58",
          warning: "#F4B400",
          danger: "#DB4437",
          muted: "#6B7C93",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "8px",
        lg: "8px",
        md: "8px",
        sm: "6px",
      },
      borderWidth: {
        DEFAULT: "1px",
      },
      boxShadow: {
        modal: "0 4px 12px rgba(0, 46, 110, 0.08)",
        subtle: "0 2px 4px rgba(0, 0, 0, 0.04)",
      },
    },
  },
  plugins: [],
};
export default config;
