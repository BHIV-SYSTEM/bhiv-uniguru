import React, { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowRight, faArrowLeft, faCheck, faUser, faGraduationCap, faFileText } from "@fortawesome/free-solid-svg-icons";
import toast from "react-hot-toast";
import { useAuth } from "../context/AuthContext";
import { useGuru } from "../context/GuruContext";
import { createCustomGuru } from "../helpers/api-communicator";

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
          <div className="space-y-6">
            <p className="text-[#525252] text-sm sm:text-base leading-relaxed tracking-[0.16px]">
              Create personalized AI mentors that adapt to your pedagogical needs, ground conversations in verified curriculum, and help you master complex subjects.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="cds-tile p-4 border border-[#e0e0e0] bg-[#f4f4f4]">
                <div className="text-xs font-semibold text-[#0f62fe] uppercase tracking-wider mb-1">Personalized</div>
                <div className="text-xs text-[#525252]">Tailored pedagogical tone and depth</div>
              </div>
              <div className="cds-tile p-4 border border-[#e0e0e0] bg-[#f4f4f4]">
                <div className="text-xs font-semibold text-[#0f62fe] uppercase tracking-wider mb-1">Authoritative</div>
                <div className="text-xs text-[#525252]">Vetted against canonical textbooks</div>
              </div>
              <div className="cds-tile p-4 border border-[#e0e0e0] bg-[#f4f4f4]">
                <div className="text-xs font-semibold text-[#0f62fe] uppercase tracking-wider mb-1">Adaptive</div>
                <div className="text-xs text-[#525252]">Interactive step-by-step reasoning</div>
              </div>
            </div>
          </div>
        );

      case 1:
        return (
          <div className="space-y-4">
            <p className="text-[#525252] text-sm tracking-[0.16px]">What would you like to call your mentor?</p>
            <div>
              <label className="block text-xs font-medium text-[#525252] mb-1.5 tracking-[0.16px]">
                Mentor Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Mathematics Professor, Systems Architect..."
                className="cds-input"
                autoFocus
              />
            </div>
            <div className="p-3 bg-[#f4f4f4] border-l-2 border-[#0f62fe] text-xs text-[#525252]">
              Tip: Choose a descriptive title that reflects their domain expertise.
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <p className="text-[#525252] text-sm tracking-[0.16px]">What domain should <strong className="text-[#161616]">{formData.name}</strong> specialize in?</p>
            <div>
              <label className="block text-xs font-medium text-[#525252] mb-1.5 tracking-[0.16px]">
                Subject / Domain
              </label>
              <input
                type="text"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                placeholder="e.g., Multivariable Calculus, Sanskrit Epistemology, Distributed Systems..."
                className="cds-input"
                autoFocus
              />
            </div>
            <div className="p-3 bg-[#f4f4f4] border-l-2 border-[#0f62fe] text-xs text-[#525252]">
              Tip: Specify core subfields or specializations for tailored dialogue.
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-4">
            <p className="text-[#525252] text-sm tracking-[0.16px]">How should <strong className="text-[#161616]">{formData.name}</strong> guide your learning?</p>
            <div>
              <label className="block text-xs font-medium text-[#525252] mb-1.5 tracking-[0.16px]">
                Pedagogy & Teaching Instructions
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="e.g., Explain from first principles, verify student derivation, provide practical examples, and prompt for understanding..."
                className="cds-input resize-none"
                rows={3}
                autoFocus
              />
            </div>
            <div className="p-3 bg-[#f4f4f4] border-l-2 border-[#0f62fe] text-xs text-[#525252]">
              Tip: Define pedagogical style, rigor, and tone.
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const currentStepData = steps[currentStep];

  return (
    <div className="flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-8 font-carbon">
      <div className="w-full max-w-sm sm:max-w-lg lg:max-w-2xl">
        {/* Progress Bar (Carbon style) */}
        <div className="mb-6 sm:mb-8">
          <div className="flex items-center justify-between mb-2 text-xs text-[#525252] tracking-[0.16px]">
            <div>Step {currentStep + 1} of {steps.length}</div>
            <div className="font-medium text-[#161616]">{Math.round(((currentStep + 1) / steps.length) * 100)}% Complete</div>
          </div>
          <div className="w-full bg-[#e0e0e0] h-1 rounded-none">
            <div 
              className="bg-[#0f62fe] h-1 transition-all duration-300 ease-out"
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Main Card (cds-tile: flat, white, 1px border, 0px radius) */}
        <div className="cds-tile border border-[#e0e0e0] bg-white shadow-none overflow-hidden">
          {/* Header */}
          <div className="p-6 sm:p-8 border-b border-[#e0e0e0] bg-[#f4f4f4]">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-white border border-[#e0e0e0] flex items-center justify-center flex-shrink-0">
                <FontAwesomeIcon icon={currentStepData.icon} className="text-[#0f62fe] text-lg" />
              </div>
              <div>
                <h2 className="text-xl sm:text-2xl font-light text-[#161616] tracking-tight">
                  {currentStepData.title}
                </h2>
                <p className="text-[#525252] text-xs sm:text-sm mt-0.5 tracking-[0.16px]">
                  {currentStepData.subtitle}
                </p>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 sm:p-8 bg-white">
            {renderStepContent()}
          </div>

          {/* Navigation Bar */}
          <div className="bg-[#f4f4f4] px-6 sm:px-8 py-4 border-t border-[#e0e0e0]">
            <div className="flex items-center justify-between">
              <button
                onClick={handlePrevious}
                disabled={currentStep === 0}
                className="cds-btn-ghost text-xs disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ padding: "8px 12px" }}
              >
                <FontAwesomeIcon icon={faArrowLeft} className="text-xs" />
                <span>Previous</span>
              </button>

              {/* Step indicator bars */}
              <div className="flex items-center gap-1.5">
                {steps.map((_, index) => (
                  <div
                    key={index}
                    className={`w-6 h-1 rounded-none transition-colors duration-200 ${
                      index <= currentStep 
                        ? 'bg-[#0f62fe]' 
                        : 'bg-[#e0e0e0]'
                    }`}
                  />
                ))}
              </div>

              {currentStep < steps.length - 1 ? (
                <button
                  onClick={handleNext}
                  disabled={currentStep > 0 && !isStepValid(currentStep)}
                  className="cds-btn-primary text-xs disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ minHeight: "40px", padding: "8px 16px" }}
                >
                  <span>Next</span>
                  <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
                </button>
              ) : (
                <button
                  onClick={handleCreateGuru}
                  disabled={!isStepValid(currentStep) || isCreating}
                  className="cds-btn-primary text-xs disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{ minHeight: "40px", padding: "8px 16px" }}
                >
                  {isCreating ? (
                    <>
                      <div className="animate-spin w-3 h-3 border-2 border-white border-t-transparent" />
                      <span>Creating...</span>
                    </>
                  ) : (
                    <>
                      <span>Create Guru</span>
                      <FontAwesomeIcon icon={faCheck} className="text-xs" />
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Skip Option */}
        <div className="text-center mt-6">
          <button
            onClick={() => {
              try {
                localStorage.setItem('guruOnboardingDismissed', 'true');
              } catch {
                // Ignore localStorage errors
              }
              onComplete();
            }}
            className="text-xs text-[#525252] hover:text-[#161616] underline transition-colors font-carbon"
          >
            Skip onboarding (use workspace sidebar instead)
          </button>
        </div>
      </div>
    </div>
  );
};

export default GuruOnboarding;
