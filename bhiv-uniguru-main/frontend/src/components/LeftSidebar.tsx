import React, { useState, useRef, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { MessageSquarePlus } from "lucide-react";
import {
  faChevronRight,
  faChevronLeft,
  faEdit,
  faTrash,
  faChevronDown,
  faChevronUp,
  faComments,
  faTools,
  faPlus
} from "@fortawesome/free-solid-svg-icons";
import { gsap } from "gsap";
import toast from "react-hot-toast";
import { useAuth } from "../context/AuthContext";
import { useGuru } from "../context/GuruContext";
import { useChat } from "../context/ChatContext";
import { createCustomGuru } from "../helpers/api-communicator";
const guruLogo = "/guru.png";
import BubblyButton from "./BubblyButton";
import ConfirmationModal from "./ConfirmationModal";
import RenameModal from "./RenameModal";
import "../styles/discord-tooltips.css";
import { useTranslation } from 'react-i18next';

interface LeftSidebarProps {
  onCreateNewChat: () => void;
  isCreatingChat: boolean;
}

interface GuruFormData {
  name: string;
  subject: string;
  description: string;
}

interface GuruPreset extends GuruFormData {
  emoji: string;
  tagline?: string;
}

const LeftSidebar: React.FC<LeftSidebarProps> = ({ onCreateNewChat, isCreatingChat }) => {
  const { user } = useAuth();
  const { gurus, addGuru, removeGuru, selectedGuru, refreshGurus, selectGuru } = useGuru();
  const { selectChat, currentChatId, deleteChat, renameChat, chatSessions, getChatsByGuru } = useChat();
  const { t } = useTranslation();

  const [isCollapsed, setIsCollapsed] = useState(() => {
    // Always default to collapsed (closed) on refresh
    try {
      // Always return true to keep sidebar closed on refresh
      return true;
    } catch {
      return true;
    }
  });
  const [activeSection, setActiveSection] = useState<'gurus' | 'chats' | 'tools'>('gurus');

  // Refs for GSAP animations
  const contentRef = useRef<HTMLDivElement>(null);
  const gurusRef = useRef<HTMLDivElement>(null);
  const chatsRef = useRef<HTMLDivElement>(null);
  const toolsRef = useRef<HTMLDivElement>(null);

  // Horizontal scrolling ref for presets carousel
  const presetsScrollRef = useRef<HTMLDivElement>(null);
  const scrollPresets = (dir: 'left' | 'right') => {
    const el = presetsScrollRef.current;
    if (!el) return;
    const amount = Math.max(260, Math.floor(el.clientWidth * 0.85));
    el.scrollBy({ left: dir === 'left' ? -amount : amount, behavior: 'smooth' });
  };

  // Initial animation for sections
  useEffect(() => {
    const currentRef =
      activeSection === 'gurus' ? gurusRef :
      activeSection === 'chats' ? chatsRef : toolsRef;

    if (currentRef.current) {
      gsap.fromTo(currentRef.current,
        { opacity: 0, scale: 0.98 },
        {
          opacity: 1,
          scale: 1,
          duration: 0.3,
          ease: "power2.out",
          delay: 0.05
        }
      );
    }
  }, [activeSection]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [isGuruListExpanded, setIsGuruListExpanded] = useState(true);
  const [isChatListExpanded, setIsChatListExpanded] = useState(true);
  const [isToolsExpanded, setIsToolsExpanded] = useState(true);
  const [formData, setFormData] = useState<GuruFormData>({
    name: "",
    subject: "",
    description: ""
  });

  // Helpful templates to quickly prefill the form
  const guruPresets: GuruPreset[] = [
    {
      emoji: "📐",
      name: "Math Tutor",
      subject: "Mathematics (Algebra, Calculus, Geometry)",
      tagline: "Step-by-step explanations with examples",
      description: "Patient tutor who explains step-by-step with examples and checks understanding."
    },
    {
      emoji: "💻",
      name: "Coding Mentor",
      subject: "Programming (JavaScript, Python)",
      tagline: "Clear code, simple explanations",
      description: "Practical mentor who writes clear code, explains concepts simply, and provides best practices."
    },
    {
      emoji: "⚛️",
      name: "Physics Coach",
      subject: "Physics (Mechanics, Electricity, Waves)",
      tagline: "Analogies and visual intuition",
      description: "Explains concepts with analogies and visual intuition; helps with problem-solving."
    },
    {
      emoji: "✍️",
      name: "Essay Coach",
      subject: "Writing & Essays",
      tagline: "Structure, clarity, and feedback",
      description: "Helps outline a thesis, improve clarity, suggest revisions, and cite sources properly."
    },
    {
      emoji: "🗣️",
      name: "Language Buddy",
      subject: "Languages (English practice)",
      tagline: "Conversation and gentle corrections",
      description: "Conversational practice with friendly corrections and useful phrases."
    },
    {
      emoji: "📊",
      name: "Data Science Guru",
      subject: "Data Science (Python, Pandas, ML)",
      tagline: "From data cleaning to models",
      description: "Guides through EDA, data cleaning, model building, and evaluation with practical tips."
    },
    {
      emoji: "🎯",
      name: "Interview Prep Coach",
      subject: "Interview Prep (Behavioral & Technical)",
      tagline: "Mock questions and feedback",
      description: "Practices common questions, provides behavioral frameworks, and offers feedback."
    },
    {
      emoji: "🧪",
      name: "Chemistry Tutor",
      subject: "Chemistry (Organic, Inorganic, Physical)",
      tagline: "Reactions, mechanisms, and intuition",
      description: "Breaks down reactions and mechanisms, builds chemical intuition with examples."
    },
    {
      emoji: "🏛️",
      name: "History Guide",
      subject: "History (World, Modern)",
      tagline: "Timelines and cause/effect",
      description: "Explains timelines, causes, and consequences with memorable summaries."
    },
    {
      emoji: "💼",
      name: "Business Strategy Advisor",
      subject: "Business/Strategy (Case Studies)",
      tagline: "MECE, hypotheses, and frameworks",
      description: "Uses structured thinking, hypotheses, and classic frameworks to solve cases."
    }
  ];

  // First-time user onboarding helper
  const [showOnboarding, setShowOnboarding] = useState<boolean>(() => {
    try {
      const dismissed = localStorage.getItem('guruOnboardingDismissed') === 'true';
      return !dismissed;
    } catch {
      return true;
    }
  });
  const [showPresets, setShowPresets] = useState<boolean>(true);

  // Rename modal state
  const [renameModal, setRenameModal] = useState<{
    isOpen: boolean;
    chatId: string;
    currentName: string;
  }>({
    isOpen: false,
    chatId: '',
    currentName: ''
  });

  // Confirmation modal states
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    type: 'guru' | 'chat';
    id: string;
    name: string;
  }>({
    isOpen: false,
    type: 'guru',
    id: '',
    name: ''
  });

  const sidebarRef = useRef<HTMLDivElement>(null);

  // Handle click outside to close sidebar on mobile and window resize
  useEffect(() => {
    // Keep sidebar closed by default - no automatic opening based on screen size

    const handleClickOutside = (event: MouseEvent) => {
      if (sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
        // Only auto-close on mobile
        if (typeof window !== 'undefined' && window.innerWidth < 1024) {
          setIsCollapsed(true);
        }
      }
    };

    const handleResize = () => {
      if (typeof window !== 'undefined') {
        const isMobile = window.innerWidth < 1024;
        if (isMobile) {
          setIsCollapsed(true);
          // Note: Not saving to localStorage since we want sidebar closed on refresh
        }
        // Keep sidebar closed on all screen sizes - user must manually open
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    window.addEventListener("resize", handleResize);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  // Open Create Guru panel when receiving global event
  useEffect(() => {
    const onOpenGuruCreate = (_e: Event) => {
      setIsCollapsed(false);
      handleSectionChange('gurus');
      setShowCreateForm(true);
    };
    // custom event not in WindowEventMap; cast to satisfy TS
    window.addEventListener('open-guru-create' as any, onOpenGuruCreate as EventListener);
    return () => {
      window.removeEventListener('open-guru-create' as any, onOpenGuruCreate as EventListener);
    };
  }, []);

  // Auto-dismiss onboarding once the user has at least one guru
  useEffect(() => {
    if (gurus.length > 0 && showOnboarding) {
      try {
        localStorage.setItem('guruOnboardingDismissed', 'true');
      } catch {}
      setShowOnboarding(false);
    }
  }, [gurus.length, showOnboarding]);

  const handleCreateGuru = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim() || !formData.subject.trim() || !formData.description.trim()) {
      toast.error("Please fill in all fields");
      return;
    }

    toast.loading("Creating guru...", { id: "create-guru" });

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
      
      addGuru(newGuru as any);
      // Make the new guru active immediately
      selectGuru(newGuru as any);
      // Sync with backend to ensure consistent state
      try {
        await refreshGurus();
      } catch (refreshError) {
        console.warn("Could not refresh guru list immediately:", refreshError);
      }

      setFormData({ name: "", subject: "", description: "" });
      setShowCreateForm(false);
      try {
        localStorage.setItem('guruOnboardingDismissed','true');
      } catch {}
      setShowOnboarding(false);
      
      toast.success("Guru created successfully! 🧙‍♂️", {
        id: "create-guru",
        icon: '✨'
      });
    } catch (error) {
      console.error("Error creating guru:", error);
      toast.error("Failed to create guru. Please try again.", { id: "create-guru" });
    }
  };

  const handleDeleteGuru = (guruId: string, guruName: string) => {
    setConfirmModal({
      isOpen: true,
      type: 'guru',
      id: guruId,
      name: guruName
    });
  };

  const handleDeleteChat = (chatId: string, chatName: string) => {
    setConfirmModal({
      isOpen: true,
      type: 'chat',
      id: chatId,
      name: chatName
    });
  };

  const confirmDelete = async () => {
    const { type, id } = confirmModal;

    if (type === 'guru') {
      toast.loading("Deleting guru...", { id: "delete-guru" });

      try {
        await removeGuru(id);
        toast.success("Guru deleted successfully", {
          id: "delete-guru",
          icon: '🗑️'
        });
      } catch (error) {
        console.error("Error deleting guru:", error);
        toast.error("Failed to delete guru", { id: "delete-guru" });
      }
    } else if (type === 'chat') {
      toast.loading("Deleting chat...", { id: "delete-chat" });

      try {
        await deleteChat(id);
        toast.success("Chat deleted successfully", {
          id: "delete-chat",
          icon: '🗑️'
        });
      } catch (error) {
        console.error("Error deleting chat:", error);
        toast.error("Failed to delete chat", { id: "delete-chat" });
      }
    }
  };

  const openRenameModal = (chatId: string, currentName: string) => {
    setRenameModal({
      isOpen: true,
      chatId,
      currentName
    });
  };

  const closeRenameModal = () => {
    setRenameModal({
      isOpen: false,
      chatId: '',
      currentName: ''
    });
  };

  const handleRenameChat = async (newName: string) => {
    if (!newName.trim()) {
      toast.error("Chat name cannot be empty");
      return;
    }

    toast.loading("Renaming chat...", { id: "rename-chat" });

    try {
      await renameChat(renameModal.chatId, newName.trim());

      toast.success("Chat renamed successfully", {
        id: "rename-chat",
        icon: '✏️'
      });
    } catch (error) {
      console.error("Error renaming chat:", error);
      toast.error("Failed to rename chat", { id: "rename-chat" });
    }
  };

  const toggleGuruList = () => {
    setIsGuruListExpanded(!isGuruListExpanded);
  };

  const toggleChatList = () => {
    setIsChatListExpanded(!isChatListExpanded);
  };

  const toggleToolsList = () => {
    setIsToolsExpanded(!isToolsExpanded);
  };

  
  const handleChatSelect = (chatId: string) => {
    selectChat(chatId);
  };

  // Format date for chat history display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) return "Today";
    if (diffDays === 2) return "Yesterday";
    if (diffDays <= 7) return `${diffDays - 1} days ago`;
    return date.toLocaleDateString();
  };

  const handleGuruSelect = (guru: any) => {
    selectGuru(guru);
    handleSectionChange('chats');
  };

  // Smooth section transition with GSAP
  const handleSectionChange = (newSection: 'gurus' | 'chats' | 'tools') => {
    if (newSection === activeSection) return;

    const currentRef =
      activeSection === 'gurus' ? gurusRef :
      activeSection === 'chats' ? chatsRef : toolsRef;

    const newRef =
      newSection === 'gurus' ? gurusRef :
      newSection === 'chats' ? chatsRef : toolsRef;

    // Set the content container height to prevent jumping
    if (contentRef.current) {
      const currentHeight = contentRef.current.offsetHeight;
      gsap.set(contentRef.current, { height: currentHeight });
    }

    // Animate out current section
    if (currentRef.current) {
      gsap.to(currentRef.current, {
        opacity: 0,
        scale: 0.98,
        duration: 0.15,
        ease: "power2.out",
        onComplete: () => {
          setActiveSection(newSection);

          // Small delay to ensure DOM update
          gsap.delayedCall(0.02, () => {
            // Reset content container height to auto after transition
            if (contentRef.current) {
              gsap.set(contentRef.current, { height: 'auto' });
            }

            // Animate in new section
            if (newRef.current) {
              gsap.fromTo(newRef.current,
                { opacity: 0, scale: 0.98 },
                {
                  opacity: 1,
                  scale: 1,
                  duration: 0.2,
                  ease: "power2.out"
                }
              );
            }
          });
        }
      });
    } else {
      // Fallback if no current ref
      setActiveSection(newSection);
      if (newRef.current) {
        gsap.fromTo(newRef.current,
          { opacity: 0, scale: 0.98 },
          {
            opacity: 1,
            scale: 1,
            duration: 0.2,
            ease: "power2.out"
          }
        );
      }
    }
  };

  return (
    <>
      {/* Sidebar */}
      <div
        ref={sidebarRef}
        className={`fixed top-16 left-0 h-[calc(100vh-4rem)] transform transition-all duration-300 ease-in-out z-40 backdrop-blur-xl border-r border-purple-400/20 shadow-2xl flex flex-col overflow-hidden ${
          isCollapsed ? 'w-16' : 'w-80 md:w-96 lg:w-[30rem] xl:w-[34rem]'
        }`}
        style={{
          background: "linear-gradient(180deg, rgba(139, 92, 246, 0.08) 0%, rgba(124, 58, 237, 0.06) 30%, rgba(109, 40, 217, 0.05) 70%, rgba(91, 33, 182, 0.04) 100%)",
          backdropFilter: "blur(25px) saturate(120%)",
          borderRight: "1px solid rgba(139, 92, 246, 0.15)",
          boxShadow: "0 25px 50px -12px rgba(139, 92, 246, 0.1), 0 0 0 1px rgba(139, 92, 246, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.05)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-purple-400/20 flex-shrink-0">
          {!isCollapsed && (
            <h2 className="text-lg font-bold flex items-center gap-2">
              <img src={guruLogo} alt="Guru" className="w-6 h-6 drop-shadow-lg" />
              <span className="bg-gradient-to-r from-purple-300 to-purple-500 bg-clip-text text-transparent">UniGuru Tools</span>
            </h2>
          )}
          <button
            onClick={() => {
              const newCollapsed = !isCollapsed;
              setIsCollapsed(newCollapsed);
              // Note: Not saving to localStorage since we want sidebar closed on refresh
            }}
            className="text-purple-300 hover:text-white transition-all duration-200 p-2 rounded-full hover:bg-purple-400/10"
          >
            <FontAwesomeIcon
              icon={isCollapsed ? faChevronRight : faChevronLeft}
              size="sm"
            />
          </button>
        </div>

        {/* Navigation Tabs - Discord Style */}
        {!isCollapsed && (
          <div className="flex border-b border-purple-400/20 flex-shrink-0 bg-black/10">
            <button
              onClick={() => handleSectionChange('gurus')}
              className={`relative flex-1 py-3 px-4 text-sm font-medium transition-all duration-200 ease-out flex items-center justify-center group overflow-hidden ${
                activeSection === 'gurus'
                  ? 'text-white bg-purple-500/20'
                  : 'text-gray-300 hover:text-white hover:bg-purple-400/10'
              }`}
            >
              {/* Discord-style active indicator */}
              {activeSection === 'gurus' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-purple-400 rounded-t-full"></div>
              )}

              {/* Hover effect background */}
              <div className="absolute inset-0 bg-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>

              <img src={guruLogo} alt="Guru" className="w-4 h-4 mr-2 relative z-10 transition-transform duration-200 group-hover:scale-110" />
              <span className="relative z-10">{t('gurus')}</span>
            </button>

            <button
              onClick={() => handleSectionChange('chats')}
              className={`relative flex-1 py-3 px-4 text-sm font-medium transition-all duration-200 ease-out flex items-center justify-center group overflow-hidden ${
                activeSection === 'chats'
                  ? 'text-white bg-blue-500/20'
                  : 'text-gray-300 hover:text-white hover:bg-blue-400/10'
              }`}
            >
              {activeSection === 'chats' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-400 rounded-t-full"></div>
              )}

              <div className="absolute inset-0 bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>

              <FontAwesomeIcon icon={faComments} className="mr-2 relative z-10 transition-transform duration-200 group-hover:scale-110" />
              <span className="relative z-10">{t('chats')}</span>
            </button>

            <button
              onClick={() => handleSectionChange('tools')}
              className={`relative flex-1 py-3 px-4 text-sm font-medium transition-all duration-200 ease-out flex items-center justify-center group overflow-hidden ${
                activeSection === 'tools'
                  ? 'text-white bg-orange-500/20'
                  : 'text-gray-300 hover:text-white hover:bg-orange-400/10'
              }`}
            >
              {activeSection === 'tools' && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-400 rounded-t-full"></div>
              )}

              <div className="absolute inset-0 bg-orange-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>

              <FontAwesomeIcon icon={faTools} className="mr-2 relative z-10 transition-transform duration-200 group-hover:scale-110" />
              <span className="relative z-10">Tools</span>
            </button>
          </div>
        )}

        {/* Collapsed Icons - Discord Style */}
        {isCollapsed && (
          <div className="flex flex-col items-center py-4 space-y-3">
            {/* Gurus Button */}
            <div className="relative group discord-tooltip" data-tooltip={`My Gurus (${gurus.length})`}>
              {/* Discord-style indicator bar */}
              <div className="absolute -left-3 top-1/2 transform -translate-y-1/2 w-1 bg-white rounded-r-full transition-all duration-200 ease-out group-hover:h-5 h-2 opacity-0 group-hover:opacity-100"></div>

              <button
                onClick={() => {
                  setIsCollapsed(false);
                  handleSectionChange('gurus');
                }}
                className="relative w-12 h-12 rounded-3xl bg-gray-700/80 hover:bg-purple-600 text-gray-300 hover:text-white transition-all duration-200 ease-out group-hover:rounded-2xl flex items-center justify-center overflow-hidden"
                title={`My Gurus (${gurus.length})`}
              >
                {/* Discord-style background glow */}
                <div className="absolute inset-0 bg-purple-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-3xl group-hover:rounded-2xl"></div>

                <img src={guruLogo} alt="Guru" className="relative z-10 w-6 h-6 transition-transform duration-200 group-hover:scale-110" />
              </button>
            </div>

            {/* Chats Button */}
            <div className="relative group">
              <div className="absolute -left-3 top-1/2 transform -translate-y-1/2 w-1 bg-white rounded-r-full transition-all duration-200 ease-out group-hover:h-5 h-2 opacity-0 group-hover:opacity-100"></div>

              <button
                onClick={() => {
                  setIsCollapsed(false);
                  handleSectionChange('chats');
                }}
                className="relative w-12 h-12 rounded-3xl bg-gray-700/80 hover:bg-blue-600 text-gray-300 hover:text-white transition-all duration-200 ease-out group-hover:rounded-2xl flex items-center justify-center overflow-hidden"
                title={selectedGuru ? `${selectedGuru.name} Chats (${getChatsByGuru(selectedGuru.id).length})` : `Recent Conversations (${chatSessions.length})`}
              >
                <div className="absolute inset-0 bg-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-3xl group-hover:rounded-2xl"></div>

                <FontAwesomeIcon icon={faComments} className="relative z-10 text-lg transition-transform duration-200 group-hover:scale-110" />
              </button>
            </div>

            {/* Tools Button */}
            <div className="relative group">
              <div className="absolute -left-3 top-1/2 transform -translate-y-1/2 w-1 bg-white rounded-r-full transition-all duration-200 ease-out group-hover:h-5 h-2 opacity-0 group-hover:opacity-100"></div>

              <button
                onClick={() => {
                  setIsCollapsed(false);
                  handleSectionChange('tools');
                }}
                className="relative w-12 h-12 rounded-3xl bg-gray-700/80 hover:bg-orange-600 text-gray-300 hover:text-white transition-all duration-200 ease-out group-hover:rounded-2xl flex items-center justify-center overflow-hidden"
                title="Available Tools"
              >
                <div className="absolute inset-0 bg-orange-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-3xl group-hover:rounded-2xl"></div>

                <FontAwesomeIcon icon={faTools} className="relative z-10 text-lg transition-transform duration-200 group-hover:scale-110" />
              </button>
            </div>

            {/* Separator */}
            <div className="w-8 h-0.5 bg-gray-600/50 rounded-full my-2"></div>

            {/* New Chat Button */}
            <div className="relative group">
              <div className="absolute -left-3 top-1/2 transform -translate-y-1/2 w-1 bg-white rounded-r-full transition-all duration-200 ease-out group-hover:h-5 h-2 opacity-0 group-hover:opacity-100 group-disabled:opacity-0"></div>

              <button
                onClick={onCreateNewChat}
                disabled={isCreatingChat || !selectedGuru}
                className="relative w-12 h-12 rounded-3xl bg-green-600 hover:bg-green-500 text-white transition-all duration-200 ease-out group-hover:rounded-2xl flex items-center justify-center overflow-hidden disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-green-600 disabled:hover:rounded-3xl shadow-lg hover:shadow-green-500/30"
                title={!selectedGuru ? t('selectGuruFirst') : isCreatingChat ? t('creating') : t('startNewChat')}
              >
                {/* Discord-style background glow */}
                <div className="absolute inset-0 bg-green-400/30 opacity-0 group-hover:opacity-100 group-disabled:opacity-0 transition-opacity duration-200 rounded-3xl group-hover:rounded-2xl"></div>

                {/* Disabled state overlay */}
                {(isCreatingChat || !selectedGuru) && (
                  <div className="absolute inset-0 bg-gray-900/40 rounded-3xl"></div>
                )}

                <MessageSquarePlus
                  size={20}
                  className={`relative z-10 transition-all duration-200 group-hover:scale-110 group-disabled:scale-100 ${isCreatingChat ? 'animate-spin' : ''}`}
                />
              </button>
            </div>
          </div>
        )}

        {/* Content */}
        {!isCollapsed && (
          <div ref={contentRef} className="flex-1 overflow-y-auto overflow-x-hidden sidebar-scroll p-4 pb-6 space-y-4 min-h-0">
            {/* Gurus Section */}
            {activeSection === 'gurus' && (
              <div ref={gurusRef} className="flex flex-col h-full space-y-4">
                {/* Action Buttons */}
                {showOnboarding && gurus.length === 0 && !showCreateForm && (
                  <div className="bg-purple-500/10 border border-purple-400/30 text-purple-200 text-sm p-3 rounded-lg flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold">Getting started</div>
                      <div>Step 1: Click "Create Guru" to start.</div>
                    </div>
                    <button
                      onClick={() => { try { localStorage.setItem('guruOnboardingDismissed','true'); } catch {} setShowOnboarding(false); }}
                      className="text-xs text-purple-300 hover:text-white underline"
                    >
                      Hide tips
                    </button>
                  </div>
                )}
                {!showOnboarding && gurus.length === 0 && !showCreateForm && (
                  <div className="bg-purple-500/5 border border-purple-400/20 text-purple-200 text-xs p-2 rounded-lg flex items-center justify-between gap-3">
                    <span>New here? You can show tips again.</span>
                    <button
                      onClick={() => { try { localStorage.setItem('guruOnboardingDismissed','false'); } catch {} setShowOnboarding(true); }}
                      className="text-xs text-purple-300 hover:text-white underline"
                    >
                      Show tips
                    </button>
                  </div>
                )}
                {!showCreateForm && (
                  <div className="flex gap-2">
                    <BubblyButton
                      onClick={() => setShowCreateForm(true)}
                      variant="primary"
                      className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 font-medium text-sm ${showOnboarding && gurus.length === 0 ? 'ring-2 ring-purple-400 shadow-purple-500/30 shadow-lg' : ''}`}
                    >
                      <span>Create Guru</span>
                    </BubblyButton>
                  </div>
                )}

                {/* Create New Guru Form */}
                {showCreateForm && (
                  <div className="bg-gradient-to-br from-purple-900/40 to-purple-800/30 backdrop-blur-sm rounded-xl p-6 border border-purple-400/30 shadow-xl">
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
                          <img src={guruLogo} alt="Guru" className="w-5 h-5" />
                        </div>
                        <h3 className="text-white font-semibold text-lg">Create New Guru</h3>
                      </div>
                      {showOnboarding && (
                        <button
                          onClick={() => { try { localStorage.setItem('guruOnboardingDismissed','true'); } catch {} setShowOnboarding(false); }}
                          className="text-xs text-purple-300 hover:text-white underline"
                        >
                          Hide tips
                        </button>
                      )}
                    </div>

                    {/* Quick start templates - horizontal carousel */}
                    <div className="mb-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-purple-200 text-xs">Quick start templates</div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => setShowPresets((prev) => !prev)}
                            className="text-xs text-purple-300 hover:text-white underline"
                          >
                            {showPresets ? 'Hide' : 'Show'}
                          </button>
                          {showPresets && (
                            <div className="hidden sm:flex items-center gap-1">
                              <button
                                type="button"
                                onClick={() => scrollPresets('left')}
                                className="p-1.5 rounded-full bg-black/30 hover:bg-black/50 border border-purple-400/30 text-purple-200 hover:text-white transition-colors"
                                aria-label="Previous templates"
                              >
                                <FontAwesomeIcon icon={faChevronLeft} className="text-xs" />
                              </button>
                              <button
                                type="button"
                                onClick={() => scrollPresets('right')}
                                className="p-1.5 rounded-full bg-black/30 hover:bg-black/50 border border-purple-400/30 text-purple-200 hover:text-white transition-colors"
                                aria-label="Next templates"
                              >
                                <FontAwesomeIcon icon={faChevronRight} className="text-xs" />
                              </button>
                            </div>
                          )}
                        </div>
                      </div>

                      {showPresets && (
                        <div className="relative">
                          {/* Overlay arrows for mobile too */}
                          <div className="sm:hidden absolute inset-y-0 left-0 flex items-center">
                            <button
                              type="button"
                              onClick={() => scrollPresets('left')}
                              className="ml-[-6px] p-2 rounded-full bg-black/30 hover:bg-black/50 border border-purple-400/30 text-purple-200"
                              aria-label="Previous templates"
                            >
                              <FontAwesomeIcon icon={faChevronLeft} className="text-xs" />
                            </button>
                          </div>
                          <div className="sm:hidden absolute inset-y-0 right-0 flex items-center">
                            <button
                              type="button"
                              onClick={() => scrollPresets('right')}
                              className="mr-[-6px] p-2 rounded-full bg-black/30 hover:bg-black/50 border border-purple-400/30 text-purple-200"
                              aria-label="Next templates"
                            >
                              <FontAwesomeIcon icon={faChevronRight} className="text-xs" />
                            </button>
                          </div>

                          <div
                            ref={presetsScrollRef}
                            className="flex gap-2 overflow-x-auto pr-1"
                            style={{ scrollBehavior: 'smooth' }}
                          >
                            {guruPresets.map((p, idx) => (
                              <button
                                key={idx}
                                type="button"
                                onClick={() => setFormData({ name: p.name, subject: p.subject, description: p.description })}
                                className="min-w-[260px] sm:min-w-[280px] group relative p-3 rounded-lg border border-purple-400/30 bg-white/5 hover:bg-white/10 hover:border-purple-400/60 transition-all text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400/50"
                                title={`${p.name} — ${p.subject}`}
                                aria-label={`Use ${p.name} template`}
                              >
                                <div className="flex items-start gap-3">
                                  <div className="text-lg leading-none">{p.emoji}</div>
                                  <div className="min-w-0">
                                    <div className="text-white text-sm font-medium truncate">{p.name}</div>
                                    <div className="text-purple-200 text-xs truncate">{p.subject}</div>
                                    {p.tagline && (
                                      <div className="text-gray-400 text-xs mt-1 line-clamp-2">{p.tagline}</div>
                                    )}
                                  </div>
                                </div>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <form onSubmit={handleCreateGuru} className="space-y-4">
                      <div>
                        <label className="block text-purple-200 text-sm font-medium mb-2">
                          Guru Name *
                        </label>
                        {showOnboarding && gurus.length === 0 && (
                          <p className="text-xs text-purple-300 mb-2">Step 2: Give your guru a clear, memorable name.</p>
                        )}
                        <input
                          type="text"
                          placeholder="Enter guru name..."
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          className={`w-full px-4 py-3 bg-white/10 border border-purple-400/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-400/20 transition-all ${showOnboarding && gurus.length === 0 ? 'ring-2 ring-purple-400/60' : ''}`}
                          required
                        />
                      </div>

                      <div>
                        <label className="block text-purple-200 text-sm font-medium mb-2">
                          Subject/Expertise *
                        </label>
                        {showOnboarding && gurus.length === 0 && (
                          <p className="text-xs text-purple-300 mb-2">Step 3: Specify the subject or expertise (e.g., Math, Physics, Programming).</p>
                        )}
                        <input
                          type="text"
                          placeholder="e.g., Math, Physics, Programming..."
                          value={formData.subject}
                          onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                          className={`w-full px-4 py-3 bg-white/10 border border-purple-400/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-400/20 transition-all ${showOnboarding && gurus.length === 0 ? 'ring-2 ring-purple-400/60' : ''}`}
                          required
                        />
                      </div>

                      <div>
                        <label className="block text-purple-200 text-sm font-medium mb-2">
                          Description
                        </label>
                        {showOnboarding && gurus.length === 0 && (
                          <p className="text-xs text-purple-300 mb-2">Step 4: Describe your guru's style and what it should help with.</p>
                        )}
                        <textarea
                          placeholder="Describe your guru's personality..."
                          value={formData.description}
                          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                          className={`w-full px-4 py-3 bg-white/10 border border-purple-400/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-400/20 transition-all resize-none ${showOnboarding && gurus.length === 0 ? 'ring-2 ring-purple-400/60' : ''}`}
                          rows={4}
                          required
                        />
                      </div>

                      {showOnboarding && gurus.length === 0 && (
                        <div className="text-purple-200 text-sm mt-2">Step 5: Click "Create Guru" to finish.</div>
                      )}
                      <div className="flex gap-3 pt-2">
                        <button
                          type="button"
                          onClick={() => setShowCreateForm(false)}
                          className="flex-1 py-3 px-4 bg-gray-600/50 hover:bg-gray-600/70 text-gray-200 rounded-lg transition-all duration-200 font-medium"
                        >
                          Cancel
                        </button>
                        <BubblyButton
                          type="submit"
                          variant="primary"
                          className={`flex-1 py-3 px-4 font-medium ${showOnboarding && gurus.length === 0 ? 'ring-2 ring-purple-400 shadow-purple-500/30 shadow-lg' : ''}`}
                        >
                          Create Guru
                        </BubblyButton>
                      </div>
                    </form>
                  </div>
                )}

                {/* Gurus List */}
                <div className={`flex flex-col ${showCreateForm ? 'flex-shrink-0' : 'flex-1'} min-h-0`}>
                  <button
                    onClick={toggleGuruList}
                    className="flex items-center justify-between w-full text-left mb-3 text-purple-300 hover:text-white transition-all duration-200 ease-out py-2 px-2 rounded-lg hover:bg-purple-500/10 group"
                  >
                    <span className="text-base font-semibold transition-colors duration-200">
                      My Gurus ({gurus.length})
                    </span>
                    <FontAwesomeIcon
                      icon={isGuruListExpanded ? faChevronUp : faChevronDown}
                      className="text-sm transition-transform duration-200 group-hover:scale-110"
                    />
                  </button>

                  {isGuruListExpanded && (
                    <div className="space-y-2 flex-1 overflow-y-auto overflow-x-hidden sidebar-scroll min-h-0">
                      {gurus.length === 0 ? (
                        <div className="text-gray-300 text-center py-4">
                          <p className="text-sm">No gurus yet</p>
                          <p className="text-xs">Create your first guru to get started!</p>
                        </div>
                      ) : (
                        gurus.map((guru) => (
                          <div
                            key={guru.id}
                            className={`guru-card relative backdrop-blur-sm rounded-xl p-3 border transition-all duration-200 ease-out cursor-pointer group overflow-hidden ${
                              selectedGuru?.id === guru.id
                                ? "border-purple-400/60 shadow-lg shadow-purple-500/25 scale-[1.02]"
                                : "border-purple-400/20 hover:border-purple-400/50 hover:scale-[1.02]"
                            }`}
                            style={{
                              background: selectedGuru?.id === guru.id
                                ? "linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(124, 58, 237, 0.15))"
                                : "rgba(139, 92, 246, 0.05)",
                            }}
                            onClick={() => handleGuruSelect(guru)}
                            title={`${guru.name}\n${guru.subject}\n${guru.description}`}
                          >
                            {/* Discord-style left indicator for selected */}
                            {selectedGuru?.id === guru.id && (
                              <div className="absolute left-0 top-1/2 transform -translate-y-1/2 w-1 h-8 bg-purple-400 rounded-r-full"></div>
                            )}

                            {/* Hover glow effect */}
                            <div className="absolute inset-0 bg-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl"></div>

                            <div className="flex items-start justify-between relative z-10">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1">
                                  <img src={guruLogo} alt="Guru" className="w-4 h-4 flex-shrink-0 transition-transform duration-200 group-hover:scale-110" />
                                  <h4 className="text-white font-medium text-sm truncate break-words transition-colors duration-200">
                                    {guru.name}
                                  </h4>
                                </div>
                                <p className="text-purple-300 text-xs truncate break-words transition-colors duration-200 group-hover:text-purple-200">
                                  {guru.subject}
                                </p>
                                <p className="text-gray-300 text-xs mt-1 line-clamp-2 break-words transition-colors duration-200 group-hover:text-gray-200">
                                  {guru.description}
                                </p>
                              </div>
                              <div className="flex items-center gap-1 ml-2 opacity-0 group-hover:opacity-100 transition-all duration-200">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteGuru(guru.id, guru.name);
                                  }}
                                  className="p-1.5 rounded-lg transition-all duration-200 text-gray-400 hover:text-red-400 hover:bg-red-500/10 hover:scale-110"
                                  title="Delete guru"
                                >
                                  <FontAwesomeIcon
                                    icon={faTrash}
                                    size="xs"
                                  />
                                </button>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Chats Section */}
            {activeSection === 'chats' && (
              <div ref={chatsRef} className="flex flex-col h-full space-y-4">
                {/* New Chat Button - Discord Style */}
                <div className="relative group">
                  <BubblyButton
                    onClick={onCreateNewChat}
                    disabled={isCreatingChat || !selectedGuru}
                    variant="primary"
                    className="w-full flex items-center justify-center py-3 px-4 font-medium text-sm transition-all duration-200 ease-out relative overflow-hidden group-hover:scale-[1.02] disabled:hover:scale-100"
                  >
                    {/* Discord-style shimmer effect */}
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-out"></div>

                    {/* Pulse effect for disabled state */}
                    {(isCreatingChat || !selectedGuru) && (
                      <div className="absolute inset-0 bg-gray-500/20 animate-pulse rounded-lg"></div>
                    )}

                    <FontAwesomeIcon
                      icon={faPlus}
                      className={`text-sm mr-3 transition-all duration-200 relative z-10 group-hover:rotate-90 group-disabled:rotate-0 ${isCreatingChat ? 'animate-spin' : ''}`}
                    />
                    <span className="relative z-10">{isCreatingChat ? t('creating') : t('startNewChat')}</span>
                  </BubblyButton>
                </div>

                {/* All Chat History */}
                <div className="flex flex-col flex-1 min-h-0">
                  <button
                    onClick={toggleChatList}
                    className="flex items-center justify-between w-full text-left mb-3 text-purple-300 hover:text-white transition-all duration-200 ease-out py-2 px-2 rounded-lg hover:bg-blue-500/10 group"
                  >
                    <span className="text-base font-semibold transition-colors duration-200">
                      {selectedGuru ? `${selectedGuru.name} ${t('chats')}` : 'Recent Conversations'} ({selectedGuru ? getChatsByGuru(selectedGuru.id).length : chatSessions.length})
                    </span>
                    <FontAwesomeIcon
                      icon={isChatListExpanded ? faChevronUp : faChevronDown}
                      className="text-sm transition-transform duration-200 group-hover:scale-110"
                    />
                  </button>

                  {isChatListExpanded && (
                    <div className="space-y-2 flex-1 overflow-y-auto overflow-x-hidden sidebar-scroll min-h-0">
                      {(() => {
                        // Filter chats by selected guru if one is selected
                        const filteredChats = selectedGuru
                          ? getChatsByGuru(selectedGuru.id)
                          : chatSessions;

                        if (filteredChats.length === 0) {
                          return (
                            <div className="text-gray-300 text-center py-8">
                              {selectedGuru ? (
                                <>
                                  <p className="text-sm">No chat history with {selectedGuru.name}</p>
                                  <p className="text-xs">Start a conversation to see your chat history here</p>
                                </>
                              ) : (
                                <>
                                  <p className="text-sm">No chat history yet</p>
                                  <p className="text-xs">Select a guru and start a conversation</p>
                                </>
                              )}
                            </div>
                          );
                        }

                        return filteredChats.slice(0, 20).map((chat) => (
                          <div
                            key={chat.id}
                            className={`chat-card relative backdrop-blur-sm rounded-xl p-3 border transition-all duration-200 ease-out cursor-pointer group overflow-hidden ${
                              currentChatId === chat.id
                                ? "border-blue-400/60 shadow-lg shadow-blue-500/25 scale-[1.02]"
                                : "border-purple-400/20 hover:border-blue-400/50 hover:scale-[1.02]"
                            }`}
                            style={{
                              background: currentChatId === chat.id
                                ? "linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.15))"
                                : "rgba(139, 92, 246, 0.05)",
                            }}
                            onClick={() => handleChatSelect(chat.id)}
                            title={`${chat.title || `Chat ${chat.id.slice(0, 8)}`}\nWith ${chat.guru.name} • ${chat.messageCount} messages\nLast active: ${formatDate(chat.lastActivity)}`}
                          >
                            {/* Discord-style left indicator for active chat */}
                            {currentChatId === chat.id && (
                              <div className="absolute left-0 top-1/2 transform -translate-y-1/2 w-1 h-8 bg-blue-400 rounded-r-full"></div>
                            )}

                            {/* Hover glow effect */}
                            <div className="absolute inset-0 bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl"></div>

                            <div className="flex items-start justify-between relative z-10">
                              <div className="flex-1 min-w-0">
                                <h4 className="text-white font-medium text-sm truncate break-words transition-colors duration-200">
                                  {chat.title || `Chat ${chat.id.slice(0, 8)}`}
                                </h4>
                                <div className="flex items-center justify-between mt-1">
                                  <p className="text-gray-300 text-xs transition-colors duration-200 group-hover:text-gray-200">
                                    {chat.guru.name} • {chat.messageCount} messages
                                  </p>
                                  <p className="text-gray-400 text-xs transition-colors duration-200 group-hover:text-gray-300">
                                    {formatDate(chat.lastActivity)}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center gap-1 ml-2 opacity-0 group-hover:opacity-100 transition-all duration-200">
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openRenameModal(chat.id, chat.title || `Chat ${chat.id.slice(0, 8)}`);
                                  }}
                                  className="p-1.5 rounded-lg transition-all duration-200 text-gray-400 hover:text-blue-400 hover:bg-blue-500/10 hover:scale-110"
                                  title="Rename chat"
                                >
                                  <FontAwesomeIcon icon={faEdit} size="xs" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDeleteChat(chat.id, chat.title || `Chat ${chat.id.slice(0, 8)}`);
                                  }}
                                  className="p-1.5 rounded-lg transition-all duration-200 text-gray-400 hover:text-red-400 hover:bg-red-500/10 hover:scale-110"
                                  title="Delete chat"
                                >
                                  <FontAwesomeIcon
                                    icon={faTrash}
                                    size="xs"
                                  />
                                </button>
                              </div>
                            </div>
                          </div>
                        ));
                      })()}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tools Section */}
            {activeSection === 'tools' && (
              <div ref={toolsRef} className="flex flex-col h-full space-y-4">
                <div>
                  <button
                    onClick={toggleToolsList}
                    className="flex items-center justify-between w-full text-left mb-3 text-purple-300 hover:text-white transition-all duration-200 ease-out py-2 px-2 rounded-lg hover:bg-orange-500/10 group"
                  >
                    <span className="text-base font-semibold transition-colors duration-200">Available Tools</span>
                    <FontAwesomeIcon
                      icon={isToolsExpanded ? faChevronUp : faChevronDown}
                      className="text-sm transition-transform duration-200 group-hover:scale-110"
                    />
                  </button>

                  {isToolsExpanded && (
                    <div className="space-y-2">
                      {/* Sanskrit Knowledge Decoder Tool */}
                      <div
                        key="sanskrit-decoder"
                        id="sidebar-sanskrit-decoder"
                        className="relative backdrop-blur-sm rounded-xl p-3 border border-violet-500/30 hover:border-violet-400/70 transition-all duration-200 ease-out cursor-pointer group overflow-hidden hover:scale-[1.02]"
                        style={{ background: "rgba(109, 40, 217, 0.08)" }}
                        onClick={() => {
                          const nav = (window as unknown as Record<string, unknown>).__sidebarNavigate as ((path: string) => void) | undefined;
                          if (nav) nav("/sanskrit-decoder");
                          else window.location.href = "/sanskrit-decoder";
                        }}
                        title="Sanskrit Knowledge Decoder — Civilizational Intelligence Engine"
                      >
                        <div className="absolute inset-0 bg-violet-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl" />
                        <div className="flex items-center gap-3 relative z-10">
                          <div className="text-violet-300 text-lg transition-transform duration-200 group-hover:scale-110 select-none">ॐ</div>
                          <div>
                            <h4 className="text-white font-semibold text-sm transition-colors duration-200">Sanskrit Decoder</h4>
                            <p className="text-violet-300 text-xs transition-colors duration-200 group-hover:text-violet-200">Civilizational Knowledge Engine</p>
                          </div>
                          <div className="ml-auto">
                            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-violet-900/60 text-violet-300 border border-violet-700/40 font-medium">LIVE</span>
                          </div>
                        </div>
                      </div>

                      {/* AI Assistant Tool */}
                      <div
                        key="ai-assistant"
                        className="relative backdrop-blur-sm rounded-xl p-3 border border-purple-400/20 hover:border-purple-400/50 transition-all duration-200 ease-out cursor-pointer group overflow-hidden hover:scale-[1.02]"
                        style={{
                          background: "rgba(139, 92, 246, 0.05)",
                        }}
                        onClick={() => toast.success("AI Assistant coming soon!")}
                        title="AI Assistant - Get intelligent help with your queries and tasks"
                      >
                        {/* Hover glow effect */}
                        <div className="absolute inset-0 bg-purple-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl"></div>

                        <div className="flex items-center gap-3 relative z-10">
                          <div className="text-purple-400 text-lg transition-transform duration-200 group-hover:scale-110">🤖</div>
                          <div>
                            <h4 className="text-white font-medium text-sm transition-colors duration-200">AI Assistant</h4>
                            <p className="text-gray-300 text-xs transition-colors duration-200 group-hover:text-gray-200">Get help with your queries</p>
                          </div>
                        </div>
                      </div>

                      {/* Code Generator Tool */}
                      <div
                        key="code-generator"
                        className="relative backdrop-blur-sm rounded-xl p-3 border border-purple-400/20 hover:border-green-400/50 transition-all duration-200 ease-out cursor-pointer group overflow-hidden hover:scale-[1.02]"
                        style={{
                          background: "rgba(139, 92, 246, 0.05)",
                        }}
                        onClick={() => toast.success("Code Generator coming soon!")}
                        title="Code Generator - Generate code snippets and programming solutions"
                      >
                          {/* Hover glow effect */}
                          <div className="absolute inset-0 bg-green-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl"></div>

                          <div className="flex items-center gap-3 relative z-10">
                            <div className="text-green-400 text-lg transition-transform duration-200 group-hover:scale-110">💻</div>
                            <div>
                              <h4 className="text-white font-medium text-sm transition-colors duration-200">Code Generator</h4>
                              <p className="text-gray-300 text-xs transition-colors duration-200 group-hover:text-gray-200">Generate code snippets</p>
                            </div>
                          </div>
                        </div>

                      {/* Study Planner Tool */}
                      <div
                        key="study-planner"
                        className="relative backdrop-blur-sm rounded-xl p-3 border border-purple-400/20 hover:border-blue-400/50 transition-all duration-200 ease-out cursor-pointer group overflow-hidden hover:scale-[1.02]"
                        style={{
                          background: "rgba(139, 92, 246, 0.05)",
                        }}
                        onClick={() => toast.success("Study Planner coming soon!")}
                      >
                          {/* Hover glow effect */}
                          <div className="absolute inset-0 bg-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl"></div>

                          <div className="flex items-center gap-3 relative z-10">
                            <div className="text-blue-400 text-lg transition-transform duration-200 group-hover:scale-110">📚</div>
                            <div>
                              <h4 className="text-white font-medium text-sm transition-colors duration-200">Study Planner</h4>
                              <p className="text-gray-300 text-xs transition-colors duration-200 group-hover:text-gray-200">Plan your learning journey</p>
                            </div>
                          </div>
                        </div>

                      {/* Note Taking Tool */}
                      <div
                        key="note-taking"
                        className="relative backdrop-blur-sm rounded-xl p-3 border border-purple-400/20 hover:border-yellow-400/50 transition-all duration-200 ease-out cursor-pointer group overflow-hidden hover:scale-[1.02]"
                        style={{
                          background: "rgba(139, 92, 246, 0.05)",
                        }}
                        onClick={() => toast.success("Note Taking coming soon!")}
                      >
                          {/* Hover glow effect */}
                          <div className="absolute inset-0 bg-yellow-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200 rounded-xl"></div>

                          <div className="flex items-center gap-3 relative z-10">
                            <div className="text-yellow-400 text-lg transition-transform duration-200 group-hover:scale-110">📝</div>
                            <div>
                              <h4 className="text-white font-medium text-sm transition-colors duration-200">Note Taking</h4>
                              <p className="text-gray-300 text-xs transition-colors duration-200 group-hover:text-gray-200">Save and organize your insights</p>
                            </div>
                          </div>
                        </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        onClose={() => setConfirmModal({ ...confirmModal, isOpen: false })}
        onConfirm={confirmDelete}
        title={`Delete ${confirmModal.type === 'guru' ? 'Guru' : 'Chat'}`}
        message={`Are you sure you want to delete "${confirmModal.name}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        type="danger"
      />

      {/* Rename Modal */}
      <RenameModal
        isOpen={renameModal.isOpen}
        onClose={closeRenameModal}
        onConfirm={handleRenameChat}
        title="Rename Chat"
        currentName={renameModal.currentName}
        placeholder="Enter new chat name..."
        confirmText="Rename"
        cancelText="Cancel"
      />
    </>
  );
};

export default LeftSidebar;
