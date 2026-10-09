import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import App from "./App.jsx";
import { AuthProvider } from "./auth/AuthContext.jsx";
import { PublicConfigProvider } from "./config/PublicConfig.jsx";
import { ThemeProvider } from "./theme/ThemeContext.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
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
