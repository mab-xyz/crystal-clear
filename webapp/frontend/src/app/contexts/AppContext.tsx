// Global application context for shared state
// Reduces prop drilling for commonly used values

import React, {
  createContext,
  useContext,
  useReducer,
  useCallback,
  type ReactNode,
} from "react";

// State shape
interface AppState {
  // UI State
  theme: "light" | "dark";
  sidebarCollapsed: boolean;

  // Analysis State
  currentTab: string;
  analysisMode: "single" | "batch";

  // Error State
  globalError: string | null;
}

// Action types
type AppAction =
  | { type: "SET_THEME"; payload: "light" | "dark" }
  | { type: "TOGGLE_SIDEBAR" }
  | { type: "SET_CURRENT_TAB"; payload: string }
  | { type: "SET_ANALYSIS_MODE"; payload: "single" | "batch" }
  | { type: "SET_GLOBAL_ERROR"; payload: string | null }
  | { type: "CLEAR_GLOBAL_ERROR" };

// Initial state
const initialState: AppState = {
  theme: "light",
  sidebarCollapsed: false,
  currentTab: "Risk Score",
  analysisMode: "single",
  globalError: null,
};

// Reducer
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "SET_THEME":
      return { ...state, theme: action.payload };
    case "TOGGLE_SIDEBAR":
      return { ...state, sidebarCollapsed: !state.sidebarCollapsed };
    case "SET_CURRENT_TAB":
      return { ...state, currentTab: action.payload };
    case "SET_ANALYSIS_MODE":
      return { ...state, analysisMode: action.payload };
    case "SET_GLOBAL_ERROR":
      return { ...state, globalError: action.payload };
    case "CLEAR_GLOBAL_ERROR":
      return { ...state, globalError: null };
    default:
      return state;
  }
}

// Context
interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;

  // Convenience methods
  setTheme: (theme: "light" | "dark") => void;
  toggleSidebar: () => void;
  setCurrentTab: (tab: string) => void;
  setAnalysisMode: (mode: "single" | "batch") => void;
  setGlobalError: (error: string | null) => void;
  clearGlobalError: () => void;
}

const AppContext = createContext<AppContextValue | undefined>(undefined);

// Provider component
interface AppProviderProps {
  children: ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Convenience methods
  const setTheme = useCallback((theme: "light" | "dark") => {
    dispatch({ type: "SET_THEME", payload: theme });
  }, []);

  const toggleSidebar = useCallback(() => {
    dispatch({ type: "TOGGLE_SIDEBAR" });
  }, []);

  const setCurrentTab = useCallback((tab: string) => {
    dispatch({ type: "SET_CURRENT_TAB", payload: tab });
  }, []);

  const setAnalysisMode = useCallback((mode: "single" | "batch") => {
    dispatch({ type: "SET_ANALYSIS_MODE", payload: mode });
  }, []);

  const setGlobalError = useCallback((error: string | null) => {
    dispatch({ type: "SET_GLOBAL_ERROR", payload: error });
  }, []);

  const clearGlobalError = useCallback(() => {
    dispatch({ type: "CLEAR_GLOBAL_ERROR" });
  }, []);

  const contextValue: AppContextValue = {
    state,
    dispatch,
    setTheme,
    toggleSidebar,
    setCurrentTab,
    setAnalysisMode,
    setGlobalError,
    clearGlobalError,
  };

  return (
    <AppContext.Provider value={contextValue}>{children}</AppContext.Provider>
  );
}

// Hook to use the context
export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useAppContext must be used within an AppProvider");
  }
  return context;
}

// Individual hooks for specific state slices (optional convenience)
export function useTheme() {
  const { state, setTheme } = useAppContext();
  return { theme: state.theme, setTheme };
}

export function useSidebar() {
  const { state, toggleSidebar } = useAppContext();
  return { collapsed: state.sidebarCollapsed, toggleSidebar };
}

export function useCurrentTab() {
  const { state, setCurrentTab } = useAppContext();
  return { currentTab: state.currentTab, setCurrentTab };
}
