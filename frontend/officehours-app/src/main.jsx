import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import App from "./App.jsx";
import { AuthProvider } from "./auth/AuthContext.jsx";
import { PublicConfigProvider } from "./config/PublicConfig.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <PublicConfigProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </PublicConfigProvider>
    </BrowserRouter>
  </StrictMode>,
);
