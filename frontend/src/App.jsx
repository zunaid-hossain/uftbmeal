import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { api, clearSession, storedUser } from "./api/client";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import AuthPage from "./pages/AuthPage";
import HomePage from "./pages/HomePage";
import ManagerPage from "./pages/ManagerPage";
import SellPage from "./pages/SellPage";
import AttendancePage from "./pages/AttendancePage";
import MembersPage from "./pages/MembersPage";
import PaymentsPage from "./pages/PaymentsPage";

export default function App() {
  const [user, setUser] = useState(storedUser());
  useEffect(() => {
    if (localStorage.getItem("uftb_token")) {
      api("/me").then((freshUser) => {
        localStorage.setItem("uftb_user", JSON.stringify(freshUser));
        setUser(freshUser);
      }).catch(logout);
    }
  }, []);
  const logout = () => { clearSession(); setUser(null); };
  return (
    <BrowserRouter>
      <Layout user={user} logout={logout}>
        <Routes>
          <Route path="/" element={<HomePage user={user} />} />
          <Route path="/login" element={<AuthPage mode="login" onAuth={setUser} />} />
          <Route path="/register" element={<AuthPage mode="register" onAuth={setUser} />} />
          <Route path="/sell" element={<ProtectedRoute user={user} memberOnly><SellPage /></ProtectedRoute>} />
          <Route path="/attendance" element={<ProtectedRoute user={user} memberOnly><AttendancePage /></ProtectedRoute>} />
          <Route path="/payments" element={<PaymentsPage />} />
          <Route path="/members" element={<MembersPage />} />
          <Route path="/manager" element={<ProtectedRoute user={user} managerOnly><ManagerPage /></ProtectedRoute>} />
          <Route path="*" element={<HomePage user={user} />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
