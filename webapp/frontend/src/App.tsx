// Main App component - handles routing and global styling with lazy loading
import { lazy, Suspense } from "react";
import { createGlobalStyle } from "styled-components";
import { LocalAlertProvider } from "@/shared/components/ui";
import { AppProvider } from "@/app/contexts/AppContext";
import { Routes, Route, Link } from "react-router";
import { SimpleLoader } from "@/shared/components/common";

import "./index.css";

// Lazy load route components to reduce initial bundle size
const Home = lazy(() => import("./pages/homepage/Home"));
const Graph = lazy(() => import("./pages/graph/Graph"));

// Global styles with optimized font loading
const GlobalStyles = createGlobalStyle`
  /* CSS Reset for consistent cross-browser styling */
  *, *::before, *::after {
    box-sizing: border-box;
  }
  
  * {
    margin: 0;
    padding: 0;
  }
  
  body {
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  
  img, picture, video, canvas, svg {
    display: block;
    max-width: 100%;
  }
  
  input, button, textarea, select {
    font: inherit;
  }
  
  p, h1, h2, h3, h4, h5, h6 {
    overflow-wrap: break-word;
  }
  
  /* Consolidated font declarations */
  body, input, select, textarea {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
      'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
      sans-serif;
  }
  
  .font-jersey {
    font-family: 'Jersey 20', sans-serif;
    font-weight: 400;
    font-style: normal;
  }
  
  code {
    font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New', monospace;
  }
`;

// Main app component with lazy-loaded routing configuration:
// "/" - Landing page with demo graph and contract input
// "/graph" - Analysis page with URL parameters
// "/graph/:address" - Direct contract analysis route
const App = () => (
  <div>
    <GlobalStyles />
    <AppProvider>
      <LocalAlertProvider>
        <Suspense fallback={<SimpleLoader />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/graph" element={<Graph />} />
            <Route path="/graph/:address" element={<Graph />} />
            <Route
              path="*"
              element={
                <div className="p-8 text-center">
                  <h2 className="mb-4 text-xl">Oops..Page Not Found...</h2>
                  <Link
                    to="/"
                    className="rounded px-3 py-2 underline hover:!text-[#3A7D44]"
                  >
                    Go home
                  </Link>
                </div>
              }
            />
          </Routes>
        </Suspense>
      </LocalAlertProvider>
    </AppProvider>
  </div>
);

export default App;
