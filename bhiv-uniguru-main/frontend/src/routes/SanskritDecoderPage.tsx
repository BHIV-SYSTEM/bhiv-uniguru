import React from "react";
import { useNavigate } from "react-router-dom";
import StarsCanvas from "../components/StarBackground";
import Navbar from "../components/Navbar";
import SanskritDecoder from "../components/SanskritDecoder";
import { useAuth } from "../context/AuthContext";

/**
 * SanskritDecoderPage
 *
 * Route: /sanskrit-decoder
 * Protected: yes (same level as /tools)
 *
 * Wraps the SanskritDecoder component inside the standard UniGuru
 * page layout (star background + navbar).
 */
const SanskritDecoderPage: React.FC = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout(navigate);
  };

  return (
    <div className="relative min-h-screen bg-black">
      {/* Star background (same as other pages) */}
      <div className="fixed inset-0 z-0">
        <StarsCanvas />
      </div>

      {/* Navbar */}
      <div className="relative z-10">
        <Navbar onLogout={handleLogout} isChatStarted={false} />
      </div>

      {/* Main content — scrollable over the fixed starfield */}
      <div className="relative z-10 pt-16 overflow-y-auto">
        <SanskritDecoder />
      </div>
    </div>
  );
};

export default SanskritDecoderPage;
