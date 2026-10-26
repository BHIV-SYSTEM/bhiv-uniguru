import React from "react";
import { Link } from "react-router-dom";
import Loginbox from "../components/Loginbox";
import Navbar from "../components/Navbar";

const LoginPage: React.FC = () => {
  return (
    <div className="relative min-h-screen bg-[#ffffff] text-[#161616] font-carbon flex flex-col justify-between">
      {/* Carbon Navbar with Logo */}
      <Navbar
        onLogout={() => {}}
        isChatStarted={false}
      />

      {/* Main Login Area */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pt-24 pb-16 z-10">
        <div className="w-full max-w-md">
          {/* Section Eyebrow */}
          <div className="text-xs uppercase tracking-wider text-[#525252] mb-2 font-medium">
            Authentication
          </div>
          <h1 className="text-3xl font-light text-[#161616] mb-8 tracking-tight">
            Sign in to UniGuru
          </h1>

          {/* Login Container (cds-tile 0px radius) */}
          <div className="cds-tile p-8 sm:p-10 border border-[#e0e0e0] bg-white shadow-none">
            <Loginbox onLoginSuccess={() => {}} />
          </div>

          {/* Additional Links */}
          <div className="mt-8 text-center text-xs text-[#525252] space-y-3 font-normal tracking-[0.16px]">
            <p>
              Don't have an account?{" "}
              <Link
                to="/signup"
                className="text-[#0f62fe] hover:underline font-medium"
              >
                Create an account
              </Link>
            </p>
            <p>
              <Link
                to="/forgot-password"
                className="text-[#525252] hover:text-[#161616] underline"
              >
                Forgot your password?
              </Link>
            </p>
            <p>
              <Link
                to="/"
                className="text-[#8c8c8c] hover:text-[#161616] transition-colors"
              >
                ← Back to Home
              </Link>
            </p>
          </div>
        </div>
      </main>

      {/* Carbon Minimal Footer */}
      <footer className="w-full border-t border-[#e0e0e0] py-6 px-6 text-center text-xs text-[#8c8c8c]">
        © {new Date().getFullYear()} UniGuru. Powered by Blackhole Infiverse. All rights reserved.
      </footer>
    </div>
  );
};

export default LoginPage;
