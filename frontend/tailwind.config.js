/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "var(--color-primary)",
          hover: "var(--color-primary-hover)",
        },
        good: "var(--color-good)",
        warn: "var(--color-warn)",
        danger: "var(--color-danger)",
        ink: {
          DEFAULT: "var(--color-text)",
          muted: "var(--color-text-sec)",
          hint: "var(--color-text-hint)",
        },
      },
      fontFamily: {
        sans: ["Pretendard", "Malgun Gothic", "sans-serif"],
      },
      boxShadow: {
        card: "0 4px 20px rgba(20, 40, 60, 0.06)",
      },
      borderRadius: {
        card: "20px",
        panel: "16px",
      },
    },
  },
  plugins: [],
};
