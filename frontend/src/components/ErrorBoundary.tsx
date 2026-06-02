import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          minHeight: "60vh", gap: 16, padding: 32, textAlign: "center",
        }}>
          <div style={{ fontSize: 48, opacity: 0.5 }}>:(</div>
          <h2 style={{ margin: 0, color: "var(--text, #e7ebf5)" }}>Something went wrong</h2>
          <p style={{ margin: 0, opacity: 0.7, maxWidth: 420, color: "var(--text-secondary, #a0a6b8)" }}>
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: 8, padding: "10px 24px", borderRadius: 8, border: "none",
              background: "var(--accent, #6b93ff)", color: "#fff", cursor: "pointer",
              fontSize: 14, fontWeight: 600,
            }}
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
