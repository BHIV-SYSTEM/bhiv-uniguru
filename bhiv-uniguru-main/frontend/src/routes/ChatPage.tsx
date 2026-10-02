  import React, { useState, useEffect } from "react";
import toast from "react-hot-toast";
import ChatContainer from "../components/ChatContainer";
import LoadingSpinner from "../components/LoadingSpinner";
import GuruOnboarding from "../components/GuruOnboarding";
import { useGuru } from "../context/GuruContext";
import { useChat } from "../context/ChatContext";
import LeftSidebar from "../components/LeftSidebar";

interface ChatPageProps {
  onCreateNewChat?: () => void;
  isCreatingChat?: boolean;
}

const ChatPage: React.FC<ChatPageProps> = ({ onCreateNewChat, isCreatingChat }) => {
  const { selectedGuru, gurus } = useGuru();
  const { createNewChatManually, isLoading: isChatLoading } = useChat();
  const [isCreatingChatLocal, setIsCreatingChatLocal] = useState(false);
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [showOnboarding, setShowOnboarding] = useState<boolean>(() => {
    try {
      const dismissed = localStorage.getItem('guruOnboardingDismissed') === 'true';
      return !dismissed;
    } catch {
      return true;
    }
  });

  // Use props if provided, otherwise use local state
  const actualIsCreatingChat = isCreatingChat !== undefined ? isCreatingChat : isCreatingChatLocal;

  // Simulate page loading for better UX
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsPageLoading(false);
    }, 800); // Short delay to show loading state

    return () => clearTimeout(timer);
  }, []);

  // Auto-dismiss onboarding once the user has at least one guru
  useEffect(() => {
    if (gurus.length > 0 && showOnboarding) {
      try {
        localStorage.setItem('guruOnboardingDismissed', 'true');
      } catch {
        // Ignore localStorage errors
      }
      setShowOnboarding(false);
    }
  }, [gurus.length, showOnboarding]);

  // Listen for onboarding restart event
  useEffect(() => {
    const handleRestartOnboarding = () => {
      try {
        localStorage.setItem('guruOnboardingDismissed', 'false');
      } catch {
        // Ignore localStorage errors
      }
      setShowOnboarding(true);
    };

    window.addEventListener('restart-guru-onboarding', handleRestartOnboarding);
    return () => {
      window.removeEventListener('restart-guru-onboarding', handleRestartOnboarding);
    };
  }, []);

  const handleOnboardingComplete = () => {
    setShowOnboarding(false);
  };

  // Show loading screen while page is initializing
  if (isPageLoading || isChatLoading) {
    return (
      <div className="relative h-screen overflow-hidden">
        <div className="flex items-center justify-center h-full">
          <div className="bg-glass-card backdrop-blur-xl rounded-xl p-8 border border-glass-border shadow-glass">
            <LoadingSpinner
              size="large"
              variant="orbit"
              text="Loading chat interface..."
            />
          </div>
        </div>
      </div>
    );
  }

  const handleCreateNewChat = async () => {
    if (!selectedGuru) {
      toast.error("Please select a guru first", {
        icon: '🧙‍♂️'
      });
      return;
    }

    // Use provided handler if available, otherwise use local handler
    if (onCreateNewChat) {
      onCreateNewChat();
      return;
    }

    setIsCreatingChatLocal(true);
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
      setIsCreatingChatLocal(false);
    }
  };

  return (
    <div className="relative h-screen overflow-hidden">
      {/* Main Chat Layout */}
      <div className="flex h-screen relative z-10 pt-16 overflow-hidden">
        {/* Left Sidebar - Hidden on mobile, visible on larger screens */}
        <div className="hidden lg:block">
          <LeftSidebar onCreateNewChat={handleCreateNewChat} isCreatingChat={actualIsCreatingChat} />
        </div>

        {/* Main Chat Area - Centered and wider */}
        <div className="flex-1 flex justify-center items-stretch overflow-hidden">
          <div className="w-full max-w-7xl flex flex-col overflow-hidden mx-auto">
            {/* Onboarding - Show when no guru is selected and onboarding not dismissed */}
            {!selectedGuru && showOnboarding && gurus.length === 0 && (
              <GuruOnboarding onComplete={handleOnboardingComplete} />
            )}

            {/* Chat Container - Show when guru is selected or onboarding dismissed */}
            {(selectedGuru || !showOnboarding || gurus.length > 0) && (
              <div className="flex-1 overflow-hidden">
                <ChatContainer />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
