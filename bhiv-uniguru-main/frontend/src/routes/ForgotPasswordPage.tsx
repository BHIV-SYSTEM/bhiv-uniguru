import React, { useState } from "react";
import { Link } from "react-router-dom";
import StarsCanvas from "../components/StarBackground";
// import Navbar from "../components/Navbar";
import toast from "react-hot-toast";
import axios from "axios";
import BHI from "../assets/blackhole-logo.png";
import AuthCard from "../components/AuthCard";
import AuthInput from "../components/AuthInput";
import AuthButton from "../components/AuthButton";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCheckCircle } from "@fortawesome/free-solid-svg-icons";

const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!email.trim()) {
      setError("Email address is required");
      return;
    }

    if (!validateEmail(email)) {
      setError("Please enter a valid email address");
      return;
    }

    setIsLoading(true);
    setError(undefined);

    try {
      toast.loading("Sending reset email...", { id: "forgot-password" });

      await axios.post("/api/v1/user/forgot-password", {
        email,
      });

      toast.success("Password reset email sent! Check your inbox.", {
        id: "forgot-password"
      });
      setIsSubmitted(true);
    } catch (error: any) {
      console.error("Forgot password failed:", error);
      if (axios.isAxiosError(error)) {
        const errorMessage = error.response?.data?.message || "Failed to send reset email. Please try again.";
        setError(errorMessage);
        toast.error(errorMessage, { id: "forgot-password" });
      } else {
        const errorMsg = "An unexpected error occurred. Please try again.";
        setError(errorMsg);
        toast.error(errorMsg, { id: "forgot-password" });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen">
      {/* Star Background */}
      <div className="fixed inset-0 z-0">
        <StarsCanvas />
      </div>


      {/* Forgot Password Container */}
      <div className="relative z-10">
        {!isSubmitted ? (
          <AuthCard title="Forgot Password">
            <form onSubmit={handleSubmit}>
              <AuthInput
                type="email"
                name="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError(undefined);
                }}
                required
                autoComplete="email"
                label="Email"
                error={error}
              />

              <AuthButton
                type="submit"
                loading={isLoading}
                disabled={isLoading}
                variant="primary"
              >
                {isLoading ? "Sending..." : "Send Reset Email"}
              </AuthButton>
            </form>
          </AuthCard>
        ) : (
          <AuthCard title="Email Sent!">
            <div className="text-center space-y-6">
              <div className="flex justify-center">
                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center">
                  <FontAwesomeIcon
                    icon={faCheckCircle}
                    className="text-green-400 text-2xl"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-glass font-poppins">
                  We've sent a password reset link to{" "}
                  <span className="font-semibold">{email}</span>
                </p>
                <p className="text-sm text-glass/70 font-poppins">
                  Didn't receive the email? Check your spam folder or{" "}
                  <button
                    onClick={() => {
                      setIsSubmitted(false);
                      setEmail("");
                      setError(undefined);
                    }}
                    className="text-blue-300 hover:underline font-medium"
                  >
                    try again
                  </button>
                </p>
              </div>
            </div>
          </AuthCard>
        )}

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
              Don't have an account?{" "}
              <Link
                to="/signup"
                className="text-blue-300 hover:text-blue-200 underline transition-colors duration-200"
              >
                Sign up here
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

      {/* Footer with blackhole logo - Hidden on mobile */}
      <footer className="absolute bottom-5 right-5 z-10 hidden sm:block">
        <a 
          href="https://blackholeinfiverse.com/" 
          target="_blank" 
          rel="noopener noreferrer"
          className="block hover:scale-105 transition-transform duration-200"
        >
          <img src={BHI} alt="BHI Logo" className="h-12" />
        </a>
      </footer>
    </div>
  );
};

export default ForgotPasswordPage;
