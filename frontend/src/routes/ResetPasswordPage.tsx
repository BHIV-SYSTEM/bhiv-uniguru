import React, { useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "react-hot-toast";
import StarsCanvas from "../components/StarBackground";
import AuthCard from "../components/AuthCard";
import AuthInput from "../components/AuthInput";
import AuthButton from "../components/AuthButton";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";

interface FieldErrors {
  password?: string;
  confirmPassword?: string;
  general?: string;
}

const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});

  const token = searchParams.get("token");

  const validateForm = (): boolean => {
    const newErrors: FieldErrors = {};

    if (!password) {
      newErrors.password = "Password is required";
    } else if (password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    if (!confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      toast.loading("Resetting password...", { id: "reset-password" });
      
      // Replace with your actual API endpoint
      await axios.post("/api/v1/user/reset-password", {
        token,
        password,
      });

      toast.success("Password reset successfully! Redirecting to login...", {
        id: "reset-password"
      });

      // Redirect to login page after successful reset
      setTimeout(() => {
        navigate("/login");
      }, 2000);
    } catch (error) {
      console.error("Reset password failed:", error);
      if (axios.isAxiosError(error)) {
        const errorMessage = error.response?.data?.message || "Failed to reset password. Please try again.";
        setErrors({ general: errorMessage });
        toast.error(errorMessage, { id: "reset-password" });
      } else {
        const errorMsg = "An unexpected error occurred. Please try again.";
        setErrors({ general: errorMsg });
        toast.error(errorMsg, { id: "reset-password" });
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="relative">
        <div className="fixed inset-0 z-0">
          <StarsCanvas />
        </div>
        <div className="relative z-10 flex items-center justify-center min-h-screen" style={{ minHeight: '100dvh' }}>
          <AuthCard title="Invalid Reset Link">
            <div className="text-center space-y-6">
              <div className="flex justify-center">
                <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center">
                  <FontAwesomeIcon
                    icon={faExclamationTriangle}
                    className="text-red-400 text-2xl"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-glass font-poppins">
                  This password reset link is invalid or has expired. Please request a new one.
                </p>
              </div>

              <AuthButton
                onClick={() => navigate("/forgot-password")}
                variant="primary"
              >
                Request New Reset Link
              </AuthButton>
            </div>
          </AuthCard>
        </div>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Star Background */}
      <div className="fixed inset-0 z-0">
        <StarsCanvas />
      </div>


      {/* Reset Password Container */}
      <div className="relative z-10 flex items-center justify-center min-h-screen" style={{ minHeight: '100dvh' }}>
        <AuthCard title="Reset Password">
          <form onSubmit={handleSubmit}>
            <AuthInput
              type="password"
              name="password"
              placeholder="New Password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (errors.password) {
                  setErrors(prev => ({ ...prev, password: undefined }));
                }
              }}
              required
              autoComplete="new-password"
              label="New Password"
              error={errors.password}
              disabled={isLoading}
            />

            <AuthInput
              type="password"
              name="confirmPassword"
              placeholder="Confirm New Password"
              value={confirmPassword}
              onChange={(e) => {
                setConfirmPassword(e.target.value);
                if (errors.confirmPassword) {
                  setErrors(prev => ({ ...prev, confirmPassword: undefined }));
                }
              }}
              required
              autoComplete="new-password"
              label="Confirm Password"
              error={errors.confirmPassword}
              disabled={isLoading}
            />

            {/* General error message */}
            {errors.general && (
              <p className="text-red-400 text-sm font-medium mt-4 font-poppins">
                {errors.general}
              </p>
            )}

            <AuthButton
              type="submit"
              loading={isLoading}
              disabled={isLoading}
              variant="primary"
            >
              {isLoading ? "Resetting..." : "Reset Password"}
            </AuthButton>
          </form>
        </AuthCard>

        {/* Additional Links */}
        <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 text-center space-y-2 z-20">
          <div className="text-white text-sm space-y-1 font-poppins">
            <p>
              Remember your password?{" "}
              <Link
                to="/login"
                className="text-blue-300 hover:text-blue-200 underline transition-colors duration-200"
              >
                Login here
              </Link>
            </p>
            <p>
              <Link
                to="/"
                className="text-white/70 hover:text-white underline transition-colors duration-200"
              >
                Back to Home
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordPage;
