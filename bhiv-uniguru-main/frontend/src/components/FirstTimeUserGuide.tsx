import React, { useState, useEffect } from "react";
import toast from "react-hot-toast";
import { useGuru } from "../context/GuruContext";

interface FirstTimeUserGuideProps {
  onCreateGuruClick: () => void;
  showCreateForm: boolean;
  formData: {
    name: string;
    subject: string;
    description: string;
  };
}

const FirstTimeUserGuide: React.FC<FirstTimeUserGuideProps> = ({
  onCreateGuruClick,
  showCreateForm,
  formData
}) => {
  const { gurus } = useGuru();
  const [isFirstTimeUser, setIsFirstTimeUser] = useState(true);

  // Check if user is first-time user
  useEffect(() => {
    try {
      const firstTime = localStorage.getItem('uniguru_first_time_user');
      setIsFirstTimeUser(firstTime === null);
    } catch {
      setIsFirstTimeUser(true);
    }
  }, []);

  // Mark user as not first-time anymore
  const markAsReturningUser = () => {
    try {
      localStorage.setItem('uniguru_first_time_user', 'false');
      setIsFirstTimeUser(false);
    } catch (err) {
      console.warn('Failed to save first-time user status:', err);
    }
  };

  // Show welcome toast for first-time users
  useEffect(() => {
    if (isFirstTimeUser && gurus.length === 0) {
      toast.success("Welcome! Let's create your first guru to get started 🧙‍♂️", {
        duration: 8000,
        icon: '👋'
      });
    }
  }, [isFirstTimeUser, gurus.length]);

  // Show success toast when guru is created
  useEffect(() => {
    if (!isFirstTimeUser && gurus.length === 1 && formData.name && formData.subject) {
      toast.success("Guru created successfully! Now start a chat with your new guru 🎉", {
        duration: 6000,
        icon: '✨'
      });
    }
  }, [isFirstTimeUser, gurus.length, formData]);

  if (!isFirstTimeUser || gurus.length > 0) {
    return null;
  }

  // Welcome modal for first-time users
  if (!showCreateForm) {
    return (
      <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-gradient-to-br from-purple-900/80 to-purple-800/60 backdrop-blur-lg rounded-2xl p-6 max-w-md w-full border border-purple-400/30 shadow-2xl">
          <div className="text-center">
            <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <img src="/guru.png" alt="Guru" className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Welcome to UniGuru!</h2>
            <p className="text-purple-200 mb-6">
              Let's create your first AI guru to get started. Your guru will be your personal AI assistant for learning.
            </p>
            
            <div className="bg-black/30 rounded-xl p-4 mb-6">
              <h3 className="font-semibold text-white mb-2">How to create your guru:</h3>
              <ol className="text-sm text-purple-200 space-y-2 text-left">
                <li className="flex items-start">
                  <span className="bg-purple-500 rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2 mt-0.5 flex-shrink-0">1</span>
                  <span>Click the "Create Guru" button</span>
                </li>
                <li className="flex items-start">
                  <span className="bg-purple-500 rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2 mt-0.5 flex-shrink-0">2</span>
                  <span>Give your guru a name (e.g., "Math Tutor")</span>
                </li>
                <li className="flex items-start">
                  <span className="bg-purple-500 rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2 mt-0.5 flex-shrink-0">3</span>
                  <span>Specify their subject/expertise</span>
                </li>
                <li className="flex items-start">
                  <span className="bg-purple-500 rounded-full w-5 h-5 flex items-center justify-center text-xs mr-2 mt-0.5 flex-shrink-0">4</span>
                  <span>Add a description of their personality</span>
                </li>
              </ol>
            </div>
            
            <button
              onClick={onCreateGuruClick}
              className="w-full py-3 px-4 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-500 hover:to-purple-600 text-white font-medium rounded-lg transition-all duration-200 transform hover:scale-[1.02] shadow-lg hover:shadow-purple-500/30"
            >
              Get Started
            </button>
            
            <button
              onClick={markAsReturningUser}
              className="mt-3 text-purple-300 hover:text-white text-sm transition-colors"
            >
              Skip for now
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Contextual hints in the form
  return (
    <>
      {/* Visual indicator for first-time users */}
      <div className="absolute -top-2 -right-2">
        <div className="relative">
          <div className="w-4 h-4 bg-yellow-400 rounded-full animate-ping absolute"></div>
          <div className="w-4 h-4 bg-yellow-400 rounded-full relative"></div>
        </div>
      </div>
      
      {/* Step-by-step guidance */}
      {!formData.name && (
        <p className="text-yellow-300 text-xs mt-1">← Give your guru a name (e.g., "Math Tutor")</p>
      )}
      
      {formData.name && !formData.subject && (
        <p className="text-yellow-300 text-xs mt-1">← What subject will your guru specialize in?</p>
      )}
      
      {formData.name && formData.subject && !formData.description && (
        <p className="text-yellow-300 text-xs mt-1">← Add a brief description of your guru's personality</p>
      )}
    </>
  );
};

export default FirstTimeUserGuide;