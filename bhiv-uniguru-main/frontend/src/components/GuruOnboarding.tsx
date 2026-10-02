import React, { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRight, faArrowLeft, faCheck, faUser, faGraduationCap, faFileText } from "@fortawesome/free-solid-svg-icons";
import toast from "react-hot-toast";
import { useAuth } from "../context/AuthContext";
import { useGuru } from "../context/GuruContext";
import { createCustomGuru } from "../helpers/api-communicator";
import BubblyButton from "./BubblyButton";

interface GuruOnboardingProps {
  onComplete: () => void;
}

interface GuruFormData {
  name: string;
  subject: string;
  description: string;
}

const GuruOnboarding: React.FC<GuruOnboardingProps> = ({ onComplete }) => {
  const { user } = useAuth();
  const { addGuru, selectGuru, refreshGurus } = useGuru();
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<GuruFormData>({
    name: "",
    subject: "",
    description: ""
  });
  const [isCreating, setIsCreating] = useState(false);

  // Reset onboarding state when component mounts or restarts
  React.useEffect(() => {
    setCurrentStep(0);
    setFormData({ name: "", subject: "", description: "" });
    setIsCreating(false);
  }, []);

  const steps = [
    {
      id: 'welcome',
      title: 'Welcome to UniGuru!',
      subtitle: 'Let\'s create your first AI tutor',
      icon: faGraduationCap,
      color: 'from-purple-500 to-blue-500'
    },
    {
      id: 'name',
      title: 'Name Your Guru',
      subtitle: 'Give your AI tutor a memorable name',
      icon: faUser,
      color: 'from-blue-500 to-cyan-500'
    },
    {
      id: 'subject',
      title: 'Choose Expertise',
      subtitle: 'What subject should your guru specialize in?',
      icon: faGraduationCap,
      color: 'from-cyan-500 to-green-500'
    },
    {
      id: 'description',
      title: 'Describe Teaching Style',
      subtitle: 'How should your guru help you learn?',
      icon: faFileText,
      color: 'from-green-500 to-purple-500'
    }
  ];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleCreateGuru = async () => {
    if (!formData.name.trim() || !formData.subject.trim() || !formData.description.trim()) {
      toast.error("Please fill in all fields");
      return;
    }

    setIsCreating(true);
    toast.loading("Creating your first guru...", { id: "create-guru-onboarding" });

    try {
      const newGuruResponse = await createCustomGuru(
        user?.id || '',
        formData.name.trim(),
        formData.subject.trim(),
        formData.description.trim()
      );

      const newGuru = {
        id: newGuruResponse.chatbot?._id || newGuruResponse.guru?.id || newGuruResponse.id,
        name: newGuruResponse.chatbot?.name || formData.name.trim(),
        subject: newGuruResponse.chatbot?.subject || formData.subject.trim(),
        description: newGuruResponse.chatbot?.description || formData.description.trim(),
        userid: user?.id || ''
      };
      
      addGuru(newGuru);
      selectGuru(newGuru);
      
      try {
        await refreshGurus();
      } catch (refreshError) {
        console.warn("Could not refresh guru list immediately:", refreshError);
      }

      toast.success("🎉 Your guru is ready! Start chatting now.", {
        id: "create-guru-onboarding",
        icon: '✨'
      });

      // Mark onboarding as completed
      try {
        localStorage.setItem('guruOnboardingDismissed', 'true');
      } catch {
        // Ignore localStorage errors
      }

      onComplete();
    } catch (error) {
      console.error("Error creating guru:", error);
      toast.error("Failed to create guru. Please try again.", { id: "create-guru-onboarding" });
    } finally {
      setIsCreating(false);
    }
  };

  const isStepValid = (step: number): boolean => {
    switch (step) {
      case 1: return formData.name.trim().length > 0;
      case 2: return formData.subject.trim().length > 0;
      case 3: return formData.description.trim().length > 0;
      default: return true;
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="text-center space-y-4 sm:space-y-6">
            <div className="space-y-3 sm:space-y-4">
              <p className="text-gray-300 text-sm sm:text-lg leading-relaxed">
                Create personalized AI tutors that adapt to your learning style and help you master any subject.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 text-xs sm:text-sm">
                <div className="bg-white/5 rounded-lg p-3 sm:p-4 border border-white/10">
                  <div className="text-purple-300 font-medium mb-1 sm:mb-2">🎯 Personalized</div>
                  <div className="text-gray-400">Tailored to your learning needs</div>
                </div>
                <div className="bg-white/5 rounded-lg p-3 sm:p-4 border border-white/10">
                  <div className="text-blue-300 font-medium mb-1 sm:mb-2">🧠 Smart</div>
                  <div className="text-gray-400">Adapts teaching methods</div>
                </div>
                <div className="bg-white/5 rounded-lg p-3 sm:p-4 border border-white/10">
                  <div className="text-green-300 font-medium mb-1 sm:mb-2">📚 Expert</div>
                  <div className="text-gray-400">Deep subject knowledge</div>
                </div>
              </div>
            </div>
          </div>
        );

      case 1:
        return (
          <div className="space-y-4 sm:space-y-6">
            <div className="text-center mb-4 sm:mb-6">
              <p className="text-gray-300 text-sm sm:text-base">What would you like to call your guru?</p>
            </div>
            <div className="space-y-3 sm:space-y-4">
              <div>
                <label className="block text-xs sm:text-sm font-medium text-gray-300 mb-2">
                  Guru Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Math Mentor, Code Coach, Physics Pal..."
                  className="w-full px-3 sm:px-4 py-2 sm:py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 text-sm sm:text-base"
                  autoFocus
                />
              </div>
              <div className="bg-blue-500/10 border border-blue-400/30 rounded-lg p-2 sm:p-3">
                <div className="text-blue-200 text-xs sm:text-sm">
                  💡 <strong>Tip:</strong> Choose a friendly name that reflects the subject or your relationship with learning.
                </div>
              </div>
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-4 sm:space-y-6">
            <div className="text-center mb-4 sm:mb-6">
              <p className="text-gray-300 text-sm sm:text-base">What subject should <strong className="text-white">{formData.name}</strong> specialize in?</p>
            </div>
            <div className="space-y-3 sm:space-y-4">
              <div>
                <label className="block text-xs sm:text-sm font-medium text-gray-300 mb-2">
                  Subject/Expertise
                </label>
                <input
                  type="text"
                  value={formData.subject}
                  onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                  placeholder="e.g., Mathematics (Algebra, Calculus), Programming (Python, JavaScript)..."
                  className="w-full px-3 sm:px-4 py-2 sm:py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all duration-200 text-sm sm:text-base"
                  autoFocus
                />
              </div>
              <div className="bg-cyan-500/10 border border-cyan-400/30 rounded-lg p-2 sm:p-3">
                <div className="text-cyan-200 text-xs sm:text-sm">
                  💡 <strong>Tip:</strong> Be specific! Include subtopics or programming languages for better help.
                </div>
              </div>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-4 sm:space-y-6">
            <div className="text-center mb-4 sm:mb-6">
              <p className="text-gray-300 text-sm sm:text-base">How should <strong className="text-white">{formData.name}</strong> teach you <strong className="text-white">{formData.subject}</strong>?</p>
            </div>
            <div className="space-y-3 sm:space-y-4">
              <div>
                <label className="block text-xs sm:text-sm font-medium text-gray-300 mb-2">
                  Teaching Style & Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="e.g., Patient tutor who explains step-by-step with examples and checks understanding. Uses analogies and visual explanations..."
                  className="w-full px-3 sm:px-4 py-2 sm:py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all duration-200 resize-none text-sm sm:text-base"
                  rows={3}
                  autoFocus
                />
              </div>
              <div className="bg-green-500/10 border border-green-400/30 rounded-lg p-2 sm:p-3">
                <div className="text-green-200 text-xs sm:text-sm">
                  💡 <strong>Tip:</strong> Describe how you learn best - with examples, step-by-step, visual aids, etc.
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const currentStepData = steps[currentStep];

  return (
    <div className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-sm sm:max-w-lg lg:max-w-2xl">
        {/* Progress Bar */}
        <div className="mb-6 sm:mb-8">
          <div className="flex items-center justify-between mb-3 sm:mb-4">
            <div className="text-xs sm:text-sm text-gray-400">Step {currentStep + 1} of {steps.length}</div>
            <div className="text-xs sm:text-sm text-gray-400">{Math.round(((currentStep + 1) / steps.length) * 100)}% Complete</div>
          </div>
          <div className="w-full bg-gray-700/50 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-purple-500 to-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Main Card */}
        <div className="bg-gradient-to-br from-gray-900/80 to-gray-800/60 backdrop-blur-xl rounded-xl sm:rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="relative p-4 sm:p-6 lg:p-8 pb-4 sm:pb-6">
            <div className="absolute inset-0 bg-gradient-to-r opacity-10" style={{
              background: `linear-gradient(135deg, ${currentStepData.color.split(' ')[1]} 0%, ${currentStepData.color.split(' ')[3]} 100%)`
            }} />
            
            <div className="relative z-10 text-center">
              <div className={`w-12 h-12 sm:w-14 sm:h-14 lg:w-16 lg:h-16 mx-auto mb-3 sm:mb-4 bg-gradient-to-r ${currentStepData.color} rounded-full flex items-center justify-center shadow-lg`}>
                <FontAwesomeIcon icon={currentStepData.icon} className="text-white text-lg sm:text-xl" />
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">
                {currentStepData.title}
              </h2>
              <p className="text-gray-300 text-sm sm:text-base">
                {currentStepData.subtitle}
              </p>
            </div>
          </div>

          {/* Content */}
          <div className="px-4 sm:px-6 lg:px-8 pb-4 sm:pb-6 lg:pb-8">
            {renderStepContent()}
          </div>

          {/* Navigation */}
          <div className="bg-black/20 px-4 sm:px-6 lg:px-8 py-4 sm:py-6 border-t border-white/10">
            <div className="flex items-center justify-between">
              <button
                onClick={handlePrevious}
                disabled={currentStep === 0}
                className="flex items-center gap-1 sm:gap-2 px-2 sm:px-4 py-2 text-gray-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 text-sm sm:text-base"
              >
                <FontAwesomeIcon icon={faArrowLeft} className="text-xs sm:text-sm" />
                <span className="hidden sm:inline">Previous</span>
              </button>

              <div className="flex items-center gap-1 sm:gap-2">
                {steps.map((_, index) => (
                  <div
                    key={index}
                    className={`w-2 h-2 rounded-full transition-all duration-300 ${
                      index <= currentStep 
                        ? 'bg-gradient-to-r from-purple-500 to-blue-500' 
                        : 'bg-gray-600'
                    }`}
                  />
                ))}
              </div>

              {currentStep < steps.length - 1 ? (
                <BubblyButton
                  onClick={handleNext}
                  disabled={currentStep > 0 && !isStepValid(currentStep)}
                  variant="primary"
                  className="flex items-center gap-1 sm:gap-2 px-3 sm:px-6 py-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base"
                >
                  <span className="hidden sm:inline">Next</span>
                  <FontAwesomeIcon icon={faArrowRight} className="text-xs sm:text-sm" />
                </BubblyButton>
              ) : (
                <BubblyButton
                  onClick={handleCreateGuru}
                  disabled={!isStepValid(currentStep) || isCreating}
                  variant="primary"
                  className="flex items-center gap-1 sm:gap-2 px-3 sm:px-6 py-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base"
                >
                  {isCreating ? (
                    <>
                      <div className="animate-spin w-3 h-3 sm:w-4 sm:h-4 border-2 border-white/30 border-t-white rounded-full" />
                      <span className="hidden sm:inline">Creating...</span>
                    </>
                  ) : (
                    <>
                      <FontAwesomeIcon icon={faCheck} className="text-xs sm:text-sm" />
                      <span className="hidden sm:inline">Create Guru</span>
                    </>
                  )}
                </BubblyButton>
              )}
            </div>
          </div>
        </div>

        {/* Skip Option */}
        <div className="text-center mt-4 sm:mt-6">
          <button
            onClick={() => {
              try {
                localStorage.setItem('guruOnboardingDismissed', 'true');
              } catch {
                // Ignore localStorage errors
              }
              onComplete();
            }}
            className="text-xs sm:text-sm text-gray-400 hover:text-gray-300 underline transition-colors duration-200"
          >
            Skip onboarding (use sidebar instead)
          </button>
        </div>
      </div>
    </div>
  );
};

export default GuruOnboarding;
