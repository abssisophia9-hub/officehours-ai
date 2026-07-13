/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        aui: {
          ink: "#10261c",
          forest: "#0f6b45",
          deep: "#0a4f34",
          mist: "#e8f4ee",
          sand: "#d6c4a1",
        },
      },
      fontFamily: {
        sans: ["Sora", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(18px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pop-in": {
          "0%": { opacity: "0", transform: "scale(0.86)" },
          "70%": { opacity: "1", transform: "scale(1.04)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        floaty: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.55s ease-out both",
        "pop-in": "pop-in 0.55s ease-out both",
        floaty: "floaty 4.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
