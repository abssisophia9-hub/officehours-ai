import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import App from "./App.jsx";
import { AuthProvider } from "./auth/AuthContext.jsx";
import { PublicConfigProvider } from "./config/PublicConfig.jsx";
import { ThemeProvider } from "./theme/ThemeContext.jsx";
import "./styles.css";

// Match Vite base / CDN sub-path. Empty → site root (local :5180 unchanged).
const routerBasename =
  (import.meta.env.VITE_ROOT_PATH || "").trim().replace(/\/$/, "") || undefined;

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter basename={routerBasename}>
      <ThemeProvider>
        <PublicConfigProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </PublicConfigProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>,
);
