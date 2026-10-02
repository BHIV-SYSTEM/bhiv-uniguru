import React from "react";
import { Navigate } from "react-router-dom";
import LoadingSpinner from "./LoadingSpinner";
import StarsCanvas from "./StarBackground";
import { useAuth } from "../context/AuthContext";
import { toast } from "react-hot-toast";

interface ProtectedRouteProps {
  children: React.ReactNode;
  isLoggedIn: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, isLoggedIn }) => {
  const { isAuthLoading } = useAuth();

  // Show loading screen while checking authentication
  if (isAuthLoading) {
    return (
      <div className="fixed inset-0 z-50 bg-black/80">
        <div className="fixed inset-0 z-0">
          <StarsCanvas />
        </div>
        <div className="relative z-10 flex items-center justify-center min-h-screen" style={{ minHeight: '100dvh' }}>
          <div className="bg-glass-card backdrop-blur-xl rounded-xl p-8 border border-glass-border shadow-glass">
            <LoadingSpinner
              size="large"
              variant="gradient-ring"
              text="Verifying authentication..."
            />
          </div>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isLoggedIn) {
    // Inform the user why they were redirected
    toast.error("Please log in to continue.", { id: "auth-required" });
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
