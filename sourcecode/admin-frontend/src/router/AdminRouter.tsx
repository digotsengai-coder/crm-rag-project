import {
  Navigate,
  RouterProvider,
  createBrowserRouter,
} from "react-router-dom";
import { lazy, Suspense, type ReactNode } from "react";
import AdminLayout from "../components/AdminLayout";
import RequireAuth from "../components/RequireAuth";
import { ui } from "../uiStyles";

const DashboardPage = lazy(() => import("../pages/DashboardPage"));
const OrderDetailPage = lazy(() => import("../pages/OrderDetailPage"));
const OrdersPage = lazy(() => import("../pages/OrdersPage"));
const RagPage = lazy(() => import("../pages/RagPage"));
const LoginPage = lazy(() => import("../pages/LoginPage"));
const WelcomePage = lazy(() => import("../pages/WelcomePage"));
const ChatbotSettingsPage = lazy(() => import("../pages/ChatbotSettingsPage"));
const ChatbotsPage = lazy(() => import("../pages/ChatbotsPage"));
const ChatbotPlaceholderPage = lazy(
  () => import("../pages/ChatbotPlaceholderPage"),
);
const LineBotSettingsPage = lazy(() => import("../pages/LineBotSettingsPage"));
const MetaBotSettingsPage = lazy(() => import("../pages/MetaBotSettingsPage"));
const SummaryPage = lazy(() => import("../pages/SummaryPage"));
const AdminAccountsPage = lazy(() => import("../pages/AdminAccountsPage"));
const AuditLogPage = lazy(() => import("../pages/AuditLogPage"));

function PageLoading() {
  return (
    <div className={ui.routeLoading} role="status">
      頁面載入中…
    </div>
  );
}

function loadPage(page: ReactNode) {
  return <Suspense fallback={<PageLoading />}>{page}</Suspense>;
}

const router = createBrowserRouter([
  { path: "login", element: loadPage(<LoginPage />) },
  { path: "welcome", element: loadPage(<WelcomePage />) },
  { path: "select-chatbot", element: <Navigate to="/chatbots" replace /> },
  {
    element: (
      <RequireAuth>
        <AdminLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/chatbots" replace /> },
      { path: "dashboard", element: loadPage(<DashboardPage />) },
      { path: "orders", element: loadPage(<OrdersPage />) },
      { path: "orders/:orderId", element: loadPage(<OrderDetailPage />) },
      { path: "chatbots", element: loadPage(<ChatbotsPage />) },
      { path: "chatbots/settings", element: loadPage(<ChatbotSettingsPage />) },
      { path: "chatbots/knowledge", element: loadPage(<RagPage />) },
      {
        path: "chatbots/linebot-settings",
        element: loadPage(<LineBotSettingsPage />),
      },
      {
        path: "chatbots/meta-settings",
        element: loadPage(<MetaBotSettingsPage />),
      },
      {
        path: "chatbots/script-settings",
        element: loadPage(<ChatbotPlaceholderPage />),
      },
      { path: "chatbots/summary", element: loadPage(<SummaryPage />) },
      {
        path: "chatbots/audit-log",
        element: loadPage(<AuditLogPage />),
      },
      { path: "chatbots/*", element: <Navigate to="/chatbots" replace /> },
      {
        path: "chatbot-settings",
        element: <Navigate to="/chatbots/settings" replace />,
      },
      { path: "rag", element: <Navigate to="/chatbots/knowledge" replace /> },
      {
        path: "linebot-settings",
        element: <Navigate to="/chatbots/linebot-settings" replace />,
      },
      {
        path: "script-settings",
        element: <Navigate to="/chatbots/script-settings" replace />,
      },
      {
        path: "audit-log",
        element: <Navigate to="/chatbots/audit-log" replace />,
      },
      { path: "admin-accounts", element: loadPage(<AdminAccountsPage />) },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

export default function AdminRouter() {
  return <RouterProvider router={router} />;
}
