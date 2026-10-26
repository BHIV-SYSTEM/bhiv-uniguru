import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import SanskritDecoder from "../components/SanskritDecoder";
import LeftSidebar from "../components/LeftSidebar";
import { useAuth } from "../context/AuthContext";
import { useChat } from "../context/ChatContext";
import { useGuru } from "../context/GuruContext";
import toast from "react-hot-toast";

/**
 * SanskritDecoderPage
 *
 * Route: /sanskrit-decoder
 * Protected: yes
 *
 * Includes the workspace LeftSidebar and SanskritDecoder component
 * in the standard Carbon layout.
 */
const SanskritDecoderPage: React.FC = () => {
  const { logout } = useAuth();
  const { selectedGuru } = useGuru();
  const { createNewChatManually } = useChat();
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout(navigate);
  };

  const handleCreateNewChat = async () => {
    if (!selectedGuru) {
      toast.error("Please select a guru first", { icon: '🧙‍♂️' });
      navigate("/chatpage");
      return;
    }

    setIsCreatingChat(true);
    toast.loading("Creating new chat...", { id: "create-chat-sanskrit" });

    try {
      await createNewChatManually(selectedGuru.id);
      toast.success("New chat created! 🎉", { id: "create-chat-sanskrit", icon: '💬' });
      navigate("/chatpage");
    } catch (error) {
      console.error("Error creating new chat:", error);
      toast.error("Failed to create new chat. Please try again.", { id: "create-chat-sanskrit" });
    } finally {
      setIsCreatingChat(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-white text-[#161616] font-carbon overflow-hidden">
      {/* Navbar */}
      <div className="relative z-50">
        <Navbar onLogout={handleLogout} isChatStarted={false} />
      </div>

      {/* Main Workspace Layout with LeftSidebar */}
      <div className="flex h-[calc(100vh-4rem)] relative z-10 pt-16 overflow-hidden">
        {/* Left Sidebar */}
        <div className="hidden lg:block flex-shrink-0 z-40">
          <LeftSidebar onCreateNewChat={handleCreateNewChat} isCreatingChat={isCreatingChat} />
        </div>

        {/* Sanskrit Decoder Content */}
        <div className="flex-1 overflow-y-auto w-full">
          <SanskritDecoder />
        </div>
      </div>
    </div>
  );
};

export default SanskritDecoderPage;
