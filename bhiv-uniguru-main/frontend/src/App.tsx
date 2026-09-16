import { useState, useEffect } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Navbar from "./components/Navbar";
import HomePage from "./routes/HomePage";
import LoginPage from "./routes/LoginPage";
import SignupPage from "./routes/SignupPage";
import ForgotPasswordPage from "./routes/ForgotPasswordPage";
import ResetPasswordPage from "./routes/ResetPasswordPage";
import ToolsPage from "./routes/ToolsPage";
import SanskritDecoderPage from "./routes/SanskritDecoderPage";
import AboutPage from "./routes/AboutPage";
import NotFoundPage from "./routes/NotFoundPage";

import StarsCanvas from "./components/StarBackground";
import ChatPage from "./routes/ChatPage";
import BubblyButtonDemo from "./components/BubblyButtonDemo";
import AppInitializer from "./components/AppInitializer";
import ProtectedRoute from "./components/ProtectedRoute";
import { useGuru } from "./context/GuruContext";
import { useChat } from "./context/ChatContext";
import { useAuth } from "./context/AuthContext";
import toast from "react-hot-toast";

// Wrapper component for ChatPage that handles chat creation
const ChatPageWrapper: React.FC<{
  isChatStarted: boolean;
}> = ({ isChatStarted }) => {
  const { selectedGuru } = useGuru();
  const { createNewChatManually } = useChat();
  const { logout } = useAuth();
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const navigate = useNavigate();

  const handleCreateNewChat = async () => {
    if (!selectedGuru) {
      toast.error("Please select a guru first", {
        icon: '🧙‍♂️'
      });
      return;
    }

    setIsCreatingChat(true);
    toast.loading("Creating new chat...", { id: "create-chat-main" });

    try {
      await createNewChatManually(selectedGuru.id);
      toast.success("New chat created! 🎉", {
        id: "create-chat-main",
        icon: '💬'
      });
    } catch (error) {
      console.error("Error creating new chat:", error);
      toast.error("Failed to create new chat. Please try again.", { id: "create-chat-main" });
    } finally {
      setIsCreatingChat(false);
    }
  };

  const handleLogout = async () => {
    await logout(navigate);
  };

  return (
    <div className="relative h-screen overflow-hidden">
      <div className="fixed inset-0 z-0">
        <StarsCanvas />
      </div>
      <Navbar
        onLogout={handleLogout}
        isChatStarted={isChatStarted}
        onCreateNewChat={handleCreateNewChat}
        isCreatingChat={isCreatingChat}
      />
      <ChatPage
        onCreateNewChat={handleCreateNewChat}
        isCreatingChat={isCreatingChat}
      />
    </div>
  );
};

function App() {
  const [isChatStarted, setIsChatStarted] = useState(false); // Track if Let's Chat was clicked
  const { logout, isLoggedIn } = useAuth();
  const navigate = useNavigate();

  // Hide initial HTML loader when React is ready
  useEffect(() => {
    // Immediately hide the loader when React loads
    const loader = document.getElementById('initial-loader');
    if (loader) {
      loader.classList.add('hidden');
      loader.style.display = 'none';
      // Remove completely
      setTimeout(() => {
        if (loader && loader.parentNode) {
          loader.parentNode.removeChild(loader);
        }
      }, 50);
    }
    document.body.classList.add('loaded');
  }, []);

  const handleLogout = async () => {
    await logout(navigate);
  };

  const handleChatStarted = () => {
    setIsChatStarted(true); // Hide Login/Signup buttons when Let's Chat is clicked
  };

  return (
    <div className="min-h-screen bg-black">
      <AppInitializer>
        <Routes>
        <Route
          path="/"
          element={
            <div className="relative min-h-screen">
              <div className="fixed inset-0 z-0">
                <StarsCanvas />
              </div>
              <Navbar
                onLogout={handleLogout}
                isChatStarted={isChatStarted}
              />
              <HomePage
                onChatStarted={handleChatStarted}
              />
            </div>
          }
        />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route
          path="/tools"
          element={
            <ProtectedRoute isLoggedIn={isLoggedIn}>
              <div className="relative min-h-screen">
                <div className="fixed inset-0 z-0">
                  <StarsCanvas />
                </div>
                <Navbar
                  onLogout={handleLogout}
                  isChatStarted={isChatStarted}
                />
                <div className="pt-16">
                  <ToolsPage />
                </div>
              </div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/sanskrit-decoder"
          element={
            <ProtectedRoute isLoggedIn={isLoggedIn}>
              <SanskritDecoderPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/chatpage"
          element={
            <ProtectedRoute isLoggedIn={isLoggedIn}>
              <ChatPageWrapper
                isChatStarted={isChatStarted}
              />
            </ProtectedRoute>
          }
        />
        <Route
          path="/about"
          element={
            <div className="relative min-h-screen">
              <div className="fixed inset-0 z-0">
                <StarsCanvas />
              </div>
              {/* Hide navbar on mobile for about page */}
              <div className="hidden md:block">
                <Navbar
                  onLogout={handleLogout}
                  isChatStarted={isChatStarted}
                />
              </div>
              <div className="pt-0 md:pt-16">
                <AboutPage />
              </div>
            </div>
          }
        />
        <Route path="/demo" element={<BubblyButtonDemo />} />

        {/* 404 NotFound - Catch all unmatched routes */}
        <Route
          path="*"
          element={
            <div className="relative min-h-screen">
              <div className="fixed inset-0 z-0">
                <StarsCanvas />
              </div>
              <NotFoundPage />
            </div>
          }
        />
      </Routes>

      {/* Toast Notifications */}
      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1f2937',
            color: '#f9fafb',
            border: '1px solid #374151',
            borderRadius: '8px',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#f9fafb',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#f9fafb',
            },
          },
        }}
      />
      </AppInitializer>
    </div>
  );
}

export default App;
