import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import {
  OverlayProvider,
  AlertProvider,
  ToastProvider,
} from "@pikoloo/darwin-ui";
import "@pikoloo/darwin-ui/styles.css";
import { App } from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <OverlayProvider>
      <AlertProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </AlertProvider>
    </OverlayProvider>
  </StrictMode>
);
