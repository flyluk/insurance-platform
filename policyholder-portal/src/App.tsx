import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import Layout from "./components/Layout";
import { useAuth } from "./components/AuthContext";
import Billing from "./pages/Billing";
import Claims from "./pages/Claims";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Policies from "./pages/Policies";

function Private({ children }: { children: ReactNode }) {
  const { token, user } = useAuth();
  if (!token || !user) return <Navigate to="/login" replace />;
  if (user.role !== "policyholder" && user.role !== "admin") return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Private>
            <Layout />
          </Private>
        }
      >
        <Route index element={<Home />} />
        <Route path="policies" element={<Policies />} />
        <Route path="billing" element={<Billing />} />
        <Route path="claims" element={<Claims />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
