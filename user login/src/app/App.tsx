import { LoginScreen } from "./components/LoginScreen";

export default function App() {
  console.log("App component rendering");
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0B1020",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "auto",
      }}
    >
      <div style={{ transform: "scale(1)", transformOrigin: "top center" }}>
        <LoginScreen />
      </div>
    </div>
  );
}
