import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, HashRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

// Use HashRouter on GitHub Pages or in static demo mode so deep linking and page refresh work without server URL rewrites
const isStaticOrGhPages =
  import.meta.env.VITE_STATIC_DEMO === "true" ||
  window.location.hostname.endsWith("github.io") ||
  window.location.search.includes("demo=true");

const Router = isStaticOrGhPages ? HashRouter : BrowserRouter;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Router>
      <App />
    </Router>
  </React.StrictMode>,
);
