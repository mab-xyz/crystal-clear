// Enhanced Error Boundary component with better error handling
import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);

    // Call optional error callback
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to error reporting service
    this.logErrorToService(error, errorInfo);
  }

  private logErrorToService = (error: Error, errorInfo: ErrorInfo) => {
    // In a real app, you'd send this to an error reporting service
    console.group("Error Boundary Details");
    console.error("Error:", error.name, error.message);
    console.error("Stack:", error.stack);
    console.error("Component Stack:", errorInfo.componentStack);
    console.groupEnd();
  };

  private handleReset = () => {
    this.setState({ hasError: false });
  };

  override render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className="error-boundary-container">
          <h2 className="error-boundary-title">Something went wrong</h2>
          <p className="error-boundary-message">
            {this.state.error?.message || "An unexpected error occurred"}
          </p>
          <button onClick={this.handleReset} className="error-boundary-button">
            Try Again
          </button>
          <style>{`
            .error-boundary-container {
              padding: var(--spacing-xl);
              text-align: center;
              background-color: var(--color-card);
              border: 1px solid var(--color-destructive);
              border-radius: var(--radius-lg);
              margin: var(--spacing-md);
              box-shadow: var(--shadow-lg);
              font-family: var(--font-sans);
            }
            .error-boundary-title {
              color: var(--color-destructive);
              margin-bottom: var(--spacing-md);
              font-size: var(--font-size-xl);
              font-weight: var(--font-weight-semibold);
              line-height: var(--line-height-tight);
            }
            .error-boundary-message {
              color: var(--color-muted-foreground);
              margin-bottom: var(--spacing-md);
              line-height: var(--line-height-normal);
              font-size: var(--font-size-sm);
            }
            .error-boundary-button {
              padding: var(--spacing-sm) var(--spacing-lg);
              background-color: var(--color-primary);
              color: var(--color-primary-foreground);
              border: none;
              border-radius: var(--radius-lg);
              cursor: pointer;
              font-weight: var(--font-weight-medium);
              font-size: var(--font-size-sm);
              transition: var(--transition-base);
              box-shadow: var(--shadow-sm);
            }
            .error-boundary-button:hover {
              background-color: var(--color-accent);
              color: var(--color-accent-foreground);
              box-shadow: var(--shadow-md);
              transform: translateY(-1px);
            }
          `}</style>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
