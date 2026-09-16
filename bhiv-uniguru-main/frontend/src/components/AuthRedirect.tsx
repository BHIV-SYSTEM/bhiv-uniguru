import React from "react";
import { Navigate } from "react-router-dom";

interface AuthRedirectProps {
  children: React.ReactNode;
  isLoggedIn: boolean;
}

const AuthRedirect: React.FC<AuthRedirectProps> = ({ children, isLoggedIn }) => {
  if (isLoggedIn) {
    return <Navigate to="/chatpage" replace />;
  }

  return <>{children}</>;
};

export default AuthRedirect;
