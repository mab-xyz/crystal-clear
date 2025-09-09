// Application entry point - bootstraps React app with necessary providers
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "@/shared/components/common";
import "./index.css";
import App from "./App.tsx";
import { initializeEnvironment } from "@/shared/utils/envValidation";

// Initialize environment validation before app startup
initializeEnvironment();

// Initialize TanStack Query client for server state management
const queryClient = new QueryClient();

// Render app with providers: ErrorBoundary, QueryClient for API state, BrowserRouter for routing
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
);
