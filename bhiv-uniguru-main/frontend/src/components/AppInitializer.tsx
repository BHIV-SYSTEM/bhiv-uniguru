import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useGuru } from '../context/GuruContext';
import { useChat } from '../context/ChatContext';
import LoadingSpinner from './LoadingSpinner';
import StarsCanvas from './StarBackground';
import toast from 'react-hot-toast';

interface AppInitializerProps {
  children: React.ReactNode;
}

const AppInitializer: React.FC<AppInitializerProps> = ({ children }) => {
  const { user, isLoggedIn, isAuthLoading } = useAuth();
  const { refreshGurus } = useGuru();
  const { initializeChats } = useChat();
  const [isInitialized, setIsInitialized] = useState(false);
  const [showFullScreenLoader, setShowFullScreenLoader] = useState(false);

  useEffect(() => {
    const initializeApp = async () => {
      // Only initialize if user is authenticated and not currently loading auth status
      if (isLoggedIn && user && !isInitialized && !isAuthLoading) {
        try {
          console.log('🚀 Initializing UniGuru application...');

          // Show full screen loader for better UX
          setShowFullScreenLoader(true);

          // Initialize gurus first
          await refreshGurus();
          console.log('✅ Gurus loaded');

          // Then initialize chats
          await initializeChats();
          console.log('✅ Chats loaded');

          // Hide full screen loader
          setShowFullScreenLoader(false);

          setIsInitialized(true);
        } catch (error) {
          console.error('❌ Error initializing app:', error);
          setShowFullScreenLoader(false);
          toast.error('Failed to load data. Please refresh if needed.', {
            duration: 4000,
            icon: '⚠️'
          });
          setIsInitialized(true); // Set as initialized even on error to prevent infinite loops
        }
      } else if (!isLoggedIn && !isAuthLoading) {
        // User is not authenticated, reset initialization state
        setIsInitialized(false);
        setShowFullScreenLoader(false);
      }
    };

    // Add a small delay to prevent multiple rapid initializations
    const timeoutId = setTimeout(initializeApp, 100);
    return () => clearTimeout(timeoutId);
  }, [isLoggedIn, user, isInitialized, isAuthLoading, refreshGurus, initializeChats]);

  // Reset initialization state when user logs out
  useEffect(() => {
    if (!isLoggedIn) {
      setIsInitialized(false);
      setShowFullScreenLoader(false);
    }
  }, [isLoggedIn]);

  // Show full screen loader when initializing
  if (showFullScreenLoader) {
    return (
      <div className="fixed inset-0 z-50 bg-black">
        <div className="fixed inset-0 z-0">
          <StarsCanvas />
        </div>
        <div className="relative z-10 flex items-center justify-center min-h-screen">
          <div className="bg-glass-card backdrop-blur-xl rounded-xl p-8 border border-glass-border shadow-glass">
            <LoadingSpinner
              size="xl"
              variant="gradient-ring"
              text="Initializing UniGuru..."
            />
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default AppInitializer;
