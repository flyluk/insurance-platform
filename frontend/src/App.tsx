import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./components/AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Home from "./pages/Home";
import Quotes from "./pages/Quotes";
import Underwriting from "./pages/Underwriting";
import Policies from "./pages/Policies";
import PolicyDetail from "./pages/PolicyDetail";
import Claims from "./pages/Claims";
import Clients from "./pages/Clients";
import Finance from "./pages/Finance";
import Users from "./pages/Users";

function Private({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
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
        <Route path="clients" element={<Clients />} />
        <Route path="quotes" element={<Quotes />} />
        <Route path="underwriting" element={<Underwriting />} />
        <Route path="policies" element={<Policies />} />
        <Route path="policies/:id" element={<PolicyDetail />} />
        <Route path="claims" element={<Claims />} />
        <Route path="finance" element={<Finance />} />
        <Route path="users" element={<Users />} />
      </Route>
    </Routes>
  );
}
