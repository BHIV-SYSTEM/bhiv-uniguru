import React from "react";
import toast from "react-hot-toast";

// Show welcome toast for first-time users
export const showFirstTimeUserWelcome = () => {
  const isFirstTime = (() => {
    try {
      const firstTime = localStorage.getItem('uniguru_first_time_user');
      return firstTime === null;
    } catch {
      return true;
    }
  })();

  if (isFirstTime) {
    toast.success("Welcome! Let's create your first guru to get started 🧙‍♂️", {
      duration: 8000,
      icon: '👋'
    });
  }
};

// Show success message after first guru creation
export const showFirstGuruCreatedMessage = () => {
  const isFirstTime = (() => {
    try {
      const firstTime = localStorage.getItem('uniguru_first_time_user');
      return firstTime === null;
    } catch {
      return true;
    }
  })();

  if (isFirstTime) {
    try {
      localStorage.setItem('uniguru_first_time_user', 'false');
    } catch (err) {
      console.warn('Failed to save first-time user status:', err);
    }

    toast.success("Guru created successfully! Now start a chat with your new guru 🎉", {
      duration: 6000,
      icon: '✨'
    });
    
    return true;
  }
  
  return false;
};

// First-time user guide component for the create form
export const FirstTimeUserFormGuide: React.FC<{
  isFirstTime: boolean;
  formData: {
    name: string;
    subject: string;
    description: string;
  };
  gurusLength: number;
}> = ({ isFirstTime, formData, gurusLength }) => {
  if (!isFirstTime || gurusLength > 0) {
    return null;
  }

  return (
    <>
      {/* Visual indicator */}
      <div className="absolute -top-2 -right-2">
        <div className="relative">
          <div className="w-4 h-4 bg-yellow-400 rounded-full animate-ping absolute"></div>
          <div className="w-4 h-4 bg-yellow-400 rounded-full relative"></div>
        </div>
      </div>

      {/* Contextual hints */}
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

// First-time user welcome modal
export const FirstTimeUserWelcomeModal: React.FC<{
  isVisible: boolean;
  onGetStarted: () => void;
  onSkip: () => void;
}> = ({ isVisible, onGetStarted, onSkip }) => {
  if (!isVisible) {
    return null;
  }

  const isFirstTime = (() => {
    try {
      const firstTime = localStorage.getItem('uniguru_first_time_user');
      return firstTime === null;
    } catch {
      return true;
    }
  })();

  if (!isFirstTime) {
    return null;
  }

  return (
    <div className="first-time-modal">
      <div className="first-time-modal-content">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <img src="/guru.png" alt="Guru" className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Welcome to UniGuru!</h2>
          <p className="text-purple-200 mb-6">
            Let's create your first AI guru to get started. Your guru will be your personal AI assistant for learning.
          </p>
          
          <div className="first-time-steps">
            <h3 className="font-semibold text-white mb-2">How to create your guru:</h3>
            <div className="space-y-2 text-left">
              <div className="first-time-step">
                <div className="first-time-step-number">1</div>
                <div className="first-time-step-text">Click the "Create Guru" button</div>
              </div>
              <div className="first-time-step">
                <div className="first-time-step-number">2</div>
                <div className="first-time-step-text">Give your guru a name (e.g., "Math Tutor")</div>
              </div>
              <div className="first-time-step">
                <div className="first-time-step-number">3</div>
                <div className="first-time-step-text">Specify their subject/expertise</div>
              </div>
              <div className="first-time-step">
                <div className="first-time-step-number">4</div>
                <div className="first-time-step-text">Add a description of their personality</div>
              </div>
            </div>
          </div>
          
          <div className="first-time-buttons">
            <button
              onClick={onGetStarted}
              className="first-time-button-primary"
            >
              Get Started
            </button>
            
            <button
              onClick={onSkip}
              className="first-time-button-secondary"
            >
              Skip for now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};