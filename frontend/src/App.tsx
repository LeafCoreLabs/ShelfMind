import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { ToastProvider } from "./components/Toast";
import ErrorBoundary from "./components/ErrorBoundary";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import Chatbot from "./components/Chatbot";
import LoginPage from "./pages/LoginPage";
import AdminDashboard from "./pages/admin/AdminDashboard";
import UsersPage from "./pages/admin/UsersPage";
import StoresPage from "./pages/admin/StoresPage";
import OnboardingWizard from "./pages/admin/OnboardingWizard";
import SystemHealthPage from "./pages/admin/SystemHealthPage";
import StoreDashboard from "./pages/store/StoreDashboard";
import InventoryPage from "./pages/store/InventoryPage";
import MLInsightsPage from "./pages/store/MLInsightsPage";
import AIAssistantPage from "./pages/store/AIAssistantPage";
import CustomersPage from "./pages/store/CustomersPage";
import SalesPage from "./pages/store/SalesPage";
import BillingPage from "./pages/store/BillingPage";
import StoreAlertsPage from "./pages/store/StoreAlertsPage";
import ReportsPage from "./pages/store/ReportsPage";
import PurchasesPage from "./pages/store/PurchasesPage";
import SettingsPage from "./pages/store/SettingsPage";
import "./styles/glass.css";
import "./styles/skeuo.css";

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "admin" ? "/admin" : "/store"} replace />;
}

function StoreChatbot() {
  const { user } = useAuth();
  if (!user || user.role !== "user") return null;
  return <Chatbot />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ThemeProvider>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/dashboard" element={<Navigate to="/store" replace />} />
              <Route path="/store" element={<ProtectedRoute role="user"><StoreDashboard /></ProtectedRoute>} />
              <Route path="/store/inventory" element={<ProtectedRoute role="user"><InventoryPage /></ProtectedRoute>} />
              <Route path="/store/insights" element={<ProtectedRoute role="user"><MLInsightsPage /></ProtectedRoute>} />
              <Route path="/store/ai" element={<ProtectedRoute role="user"><AIAssistantPage /></ProtectedRoute>} />
              <Route path="/store/customers" element={<ProtectedRoute role="user"><CustomersPage /></ProtectedRoute>} />
              <Route path="/store/sales" element={<ProtectedRoute role="user"><SalesPage /></ProtectedRoute>} />
              <Route path="/store/billing" element={<ProtectedRoute role="user"><BillingPage /></ProtectedRoute>} />
              <Route path="/store/alerts" element={<ProtectedRoute role="user"><StoreAlertsPage /></ProtectedRoute>} />
              <Route path="/store/reports" element={<ProtectedRoute role="user"><ReportsPage /></ProtectedRoute>} />
              <Route path="/store/purchases" element={<ProtectedRoute role="user"><PurchasesPage /></ProtectedRoute>} />
              <Route path="/store/settings" element={<ProtectedRoute role="user"><SettingsPage /></ProtectedRoute>} />
              <Route path="/admin" element={<ProtectedRoute role="admin"><AdminDashboard /></ProtectedRoute>} />
              <Route path="/admin/stores" element={<ProtectedRoute role="admin"><StoresPage /></ProtectedRoute>} />
              <Route path="/admin/onboarding" element={<ProtectedRoute role="admin"><OnboardingWizard /></ProtectedRoute>} />
              <Route path="/admin/users" element={<ProtectedRoute role="admin"><UsersPage /></ProtectedRoute>} />
              <Route path="/admin/system" element={<ProtectedRoute role="admin"><SystemHealthPage /></ProtectedRoute>} />
              <Route path="/" element={<RootRedirect />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            <StoreChatbot />
          </BrowserRouter>
        </ToastProvider>
        </ThemeProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
