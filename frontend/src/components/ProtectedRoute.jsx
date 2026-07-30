import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import EmptyState from "./EmptyState";

// Gates routes on login / verified-community-membership / admin (plan §10).
export default function ProtectedRoute({ children, requireVerified = false, requireAdmin = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <p className="py-16 text-center text-gray-500">Loading…</p>;
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  if (requireAdmin && !user.is_admin) {
    return <EmptyState title="Admins only" message="You don't have access to this page." />;
  }
  if (requireVerified && !user.is_verified_member) {
    return (
      <EmptyState
        title="Community members only"
        message="Your Telegram account isn't in the community group, so you can't list items. Join the group and log in again."
      />
    );
  }
  return children;
}
