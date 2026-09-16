import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import AuthCard from "./AuthCard";
import AuthInput from "./AuthInput";
import AuthButton from "./AuthButton";
import GoogleOAuthProduction from "./GoogleOAuthProduction";
import { useAuth } from "../context/AuthContext";

interface LoginboxProps {
  onLoginSuccess: () => void;
}

const Loginbox: React.FC<LoginboxProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const { login, googleLogin } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(undefined);
    toast.loading("Signing you in...", { id: "login" });

    try {
      await login(email, password);

      toast.success("Welcome back! Redirecting to chat...", { id: "login" });
      onLoginSuccess();
      navigate("/chatpage");
    } catch (err) {
      console.error("Login failed:", err);
      const errorMessage = err instanceof Error ? err.message : "Invalid username or password. Please try again.";
      setError(errorMessage);
      toast.error(errorMessage, { id: "login" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSuccess = async (credential: string) => {
    setIsLoading(true);
    setError(undefined);
    toast.loading("Signing in with Google...", { id: "google-login" });

    try {
      await googleLogin(credential);

      toast.success("Welcome! Redirecting to chat...", { id: "google-login" });
      onLoginSuccess();
      navigate("/chatpage");
    } catch (err) {
      console.error("Google login failed:", err);
      const errorMessage = err instanceof Error ? err.message : "Google authentication failed. Please try again.";
      setError(errorMessage);
      toast.error(errorMessage, { id: "google-login" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleError = (error: any) => {
    console.error("Google OAuth error:", error);
    toast.error("Google authentication failed. Please try again.", { id: "google-login" });
  };

  return (
    <AuthCard title="Welcome Back">
      <form onSubmit={handleSubmit}>
        <AuthInput
          type="email"
          name="email"
          placeholder="Email or Phone"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          label="Username"
          error={error}
        />

        <AuthInput
          type="password"
          name="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
          label="Password"
        />

        <AuthButton
          type="submit"
          loading={isLoading}
          disabled={isLoading}
          variant="primary"
        >
          {isLoading ? "Logging in..." : "Log In"}
        </AuthButton>

        {/* Divider */}
        <div className="flex items-center my-4 sm:my-6">
          <div className="flex-1 border-t border-gray-600"></div>
          <span className="px-3 sm:px-4 text-gray-400 text-xs sm:text-sm">or</span>
          <div className="flex-1 border-t border-gray-600"></div>
        </div>

        {/* Google OAuth Button */}
        <div className="relative">
          <GoogleOAuthProduction
            onSuccess={handleGoogleSuccess}
            onError={handleGoogleError}
            disabled={isLoading}
            text="Continue with Google"
            className="w-full"
          />
        </div>
      </form>
    </AuthCard>
  );
};

export default Loginbox;