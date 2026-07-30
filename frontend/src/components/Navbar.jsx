import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const linkClass = ({ isActive }) =>
  `rounded px-3 py-1.5 text-sm font-medium ${
    isActive ? "bg-indigo-100 text-indigo-700" : "text-gray-600 hover:bg-gray-100"
  }`;

export default function Navbar() {
  const { user, config, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <header className="sticky top-0 z-10 border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
        <Link to="/" className="mr-2 flex items-center gap-2 text-lg font-bold text-indigo-600">
          <span aria-hidden>🛍️</span>
          <span className="hidden sm:inline">{config.community_name} Marketplace</span>
          <span className="sm:hidden">Marketplace</span>
        </Link>

        <nav className="flex flex-1 items-center gap-1">
          <NavLink to="/" end className={linkClass}>
            Browse
          </NavLink>
          {user && (
            <>
              <NavLink to="/sell" className={linkClass}>
                Sell
              </NavLink>
              <NavLink to="/my-listings" className={linkClass}>
                My Listings
              </NavLink>
            </>
          )}
          {user?.is_admin && (
            <NavLink to="/admin" className={linkClass}>
              Admin
            </NavLink>
          )}
        </nav>

        {user ? (
          <div className="flex items-center gap-2">
            <span className="hidden max-w-32 truncate text-sm text-gray-600 sm:inline">
              {user.first_name}
              {user.telegram_username ? ` (@${user.telegram_username})` : ""}
            </span>
            <button
              onClick={handleLogout}
              className="rounded border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
            >
              Log out
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Log in
          </Link>
        )}
      </div>
    </header>
  );
}
