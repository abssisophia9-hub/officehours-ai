import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api/client.js";

const PublicConfigContext = createContext({
  demo: false,
  lti: false,
  microsoft: false,
  canvas_mode: "none",
  loaded: false,
});

export function PublicConfigProvider({ children }) {
  const [config, setConfig] = useState({
    demo: false,
    lti: false,
    microsoft: false,
    canvas_mode: "none",
    loaded: false,
  });

  useEffect(() => {
    let cancelled = false;
    api("/auth/config")
      .then((body) => {
        if (cancelled) return;
        setConfig({
          demo: Boolean(body?.demo),
          lti: Boolean(body?.lti),
          microsoft: Boolean(body?.microsoft),
          canvas_mode: body?.canvas_mode || "none",
          loaded: true,
        });
      })
      .catch(() => {
        if (!cancelled) setConfig((current) => ({ ...current, loaded: true }));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return <PublicConfigContext.Provider value={config}>{children}</PublicConfigContext.Provider>;
}

export function usePublicConfig() {
  return useContext(PublicConfigContext);
}
