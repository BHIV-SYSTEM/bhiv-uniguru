import React from "react";
import { Link } from "react-router-dom";
import Loginbox from "../components/Loginbox";
import StarsCanvas from "../components/StarBackground";
import Navbar from "../components/Navbar";
import BHI from "../assets/blackhole-logo.png";

const LoginPage: React.FC = () => {
  return (
    <div className="relative min-h-screen">
      {/* Star Background */}
      <div className="fixed inset-0 z-0">
        <StarsCanvas />
      </div>

      {/* Navbar with Logo */}
      <Navbar
        onLogout={() => {}}
        isChatStarted={false}
      />

      {/* Login Container */}
      <div className="relative z-10">
        <Loginbox onLoginSuccess={() => {}} />
      </div>

      {/* Additional Links */}
      <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2 text-center space-y-2 z-20">
        <div className="text-white text-sm font-poppins space-y-1">
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
              to="/forgot-password"
              className="text-blue-300 hover:text-blue-200 underline transition-colors duration-200"
            >
              Forgot your password?
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

export default LoginPage;
