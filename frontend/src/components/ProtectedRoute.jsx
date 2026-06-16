import { Navigate, useLocation } from "react-router-dom";

export default function ProtectedRoute({ user, managerOnly = false, memberOnly = false, children }) {
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (managerOnly && user.role !== "meal_manager") return <Navigate to="/" replace />;
  if (memberOnly && !user.is_meal_member) return <Navigate to="/members" replace />;
  return children;
}
