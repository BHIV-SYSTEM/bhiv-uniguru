import React, { useState, useRef, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronRight,
  faEdit,
  faTrash,
  faChevronDown,
  faChevronUp,
  faEllipsisV
} from "@fortawesome/free-solid-svg-icons";
import toast from "react-hot-toast";
import { useAuth } from "../context/AuthContext";
import { useGuru } from "../context/GuruContext";
import { useChat } from "../context/ChatContext";
import { createNewGuru, createCustomGuru } from "../helpers/api-communicator";
const guruLogo = "/guru.png";
import BubblyButton from "./BubblyButton";
import RenameModal from "./RenameModal";

interface GuruSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

interface GuruFormData {
  name: string;
  subject: string;
  description: string;
}

const GuruSidebar: React.FC<GuruSidebarProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const { gurus, addGuru, removeGuru, selectedGuru, refreshGurus, selectGuru } = useGuru();
  const { createNewChatManually, getChatsByGuru, selectChat, currentChatId, deleteChat, renameChat } = useChat();


  const [showCreateForm, setShowCreateForm] = useState(false);
  const [isGuruListExpanded, setIsGuruListExpanded] = useState(true);
  const [isChatListExpanded, setIsChatListExpanded] = useState(true);
  const [formData, setFormData] = useState<GuruFormData>({
    name: "",
    subject: "",
    description: ""
  });

  // Helper function to check if form is valid
  const isFormValid = () => {
    const valid = formData.name.trim() !== "" && 
                  formData.subject.trim() !== "" && 
                  formData.description.trim() !== "";
    console.log('Form validation check:', {
      name: formData.name.trim(),
      subject: formData.subject.trim(), 
      description: formData.description.trim(),
      valid
    });
    return valid;
  };
  const [isCreating, setIsCreating] = useState(false);
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [showChatMenu, setShowChatMenu] = useState<string | null>(null);

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
  const sidebarRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (_event: MouseEvent) => {
      if (showChatMenu) {
        setShowChatMenu(null);
      }
    };

    if (showChatMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showChatMenu]);

  // Close sidebar when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;

      // Don't close if clicking on the Tools toggle button or Guru Manager toggle button
      if (target.closest('[title="Tools"]') || target.closest('[title="Manage Gurus"]')) {
        return;
      }

      if (sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen, onClose]);

  // Close chat menu when clicking elsewhere
  useEffect(() => {
    const handleClickOutside = (_event: MouseEvent) => {
      if (showChatMenu) {
        setShowChatMenu(null);
      }
    };

    if (showChatMenu) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showChatMenu]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    console.log(`Field ${name} updated:`, value, 'Form valid:', isFormValid());
  };

  const handleCreateGuru = async () => {
    if (!user) {
      return;
    }

    // Force validation check - especially for mobile
    const nameValid = formData.name.trim().length > 0;
    const subjectValid = formData.subject.trim().length > 0;
    const descriptionValid = formData.description.trim().length > 0;

    console.log('Validation check:', { nameValid, subjectValid, descriptionValid });

    if (!nameValid || !subjectValid || !descriptionValid) {
      const missingFields = [];
      if (!nameValid) missingFields.push('Guru Name');
      if (!subjectValid) missingFields.push('Subject');
      if (!descriptionValid) missingFields.push('Description');

      toast.error(`Required: ${missingFields.join(', ')}`, {
        duration: 4000,
        position: 'top-center',
        style: {
          fontSize: '14px',
          padding: '10px 14px',
          maxWidth: '300px',
          zIndex: 99999,
          marginTop: '60px',
          backgroundColor: '#ef4444',
          color: 'white',
          fontWeight: '500'
        }
      });
      return;
    }

    setIsCreating(true);
    toast.loading("Creating your guru...", { id: "create-guru" });

    try {
      let newGuruResponse;

      // Try to use the custom guru API first, fall back to basic if it fails
      try {
        newGuruResponse = await createCustomGuru(
          user.id,
          formData.name.trim(),
          formData.subject.trim(),
          formData.description.trim()
        );
      } catch (customError) {
        console.log("Custom guru API not available, using basic guru creation");
        newGuruResponse = await createNewGuru(user.id);
      }

      // Create the guru object with form data
      console.log("Guru creation response:", newGuruResponse);

      const newGuru = {
        id: newGuruResponse.chatbot?._id || newGuruResponse.guru?.id || newGuruResponse.id,
        name: newGuruResponse.chatbot?.name || formData.name.trim(),
        subject: newGuruResponse.chatbot?.subject || formData.subject.trim(),
        description: newGuruResponse.chatbot?.description || formData.description.trim(),
        userid: user.id
      };

      // Add to context
      addGuru(newGuru);

      // Make the new guru active immediately
      selectGuru(newGuru);
      // Refresh the guru list to make sure UI is updated
      try {
        await refreshGurus();
      } catch (refreshError) {
        console.log("Could not refresh guru list:", refreshError);
      }

      // Reset form
      setFormData({ name: "", subject: "", description: "" });
      setShowCreateForm(false);

      toast.success(`Guru "${newGuru.name}" created successfully!`, { id: "create-guru" });
      console.log("Guru created successfully:", newGuru);
    } catch (error) {
      console.error("Error creating guru:", error);
      toast.error("Failed to create guru. Please try again.", { id: "create-guru" });
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteGuru = async (guruId: string) => {
    const guruToDelete = gurus.find(g => g.id === guruId);
    const guruName = guruToDelete?.name || "guru";

    if (window.confirm(`Are you sure you want to delete "${guruName}"? This action cannot be undone.`)) {
      toast.loading(`Deleting ${guruName}...`, { id: "delete-guru" });

      try {
        await removeGuru(guruId);
        toast.success(`${guruName} deleted successfully`, {
          id: "delete-guru",
          icon: '🗑️'
        });
      } catch (error) {
        console.error("Error deleting guru:", error);
        toast.error(`Failed to delete ${guruName}. Please try again.`, { id: "delete-guru" });
      }
    }
  };

  // const handleSelectGuru = (guru: any) => {
  //   setSelectedGuru(guru);
  //   // Removed duplicate toast - handled by handleGuruSelect
  // };

  const handleCreateNewChat = async () => {
    if (!selectedGuru) {
      toast.error("Please select a guru first", {
        icon: '🧙‍♂️'
      });
      return;
    }

    setIsCreatingChat(true);
    toast.loading("Creating new chat...", { id: "create-chat" });

    try {
      await createNewChatManually(selectedGuru.id);
      toast.success("New chat created! 🎉", {
        id: "create-chat",
        icon: '💬'
      });
    } catch (error) {
      console.error("Error creating new chat:", error);
      toast.error("Failed to create new chat. Please try again.", { id: "create-chat" });
    } finally {
      setIsCreatingChat(false);
    }
  };

  const toggleGuruList = () => {
    setIsGuruListExpanded(!isGuruListExpanded);
  };

  const toggleChatList = () => {
    setIsChatListExpanded(!isChatListExpanded);
  };

  
  const handleChatSelect = (chatId: string) => {
    selectChat(chatId);
    // Removed excessive toast notification for chat selection
  };

  const handleGuruSelect = (guru: any) => {
    selectGuru(guru);
    // Show a subtle toast only for guru switching
    toast.success(`Switched to ${guru.name}`, {
      duration: 1000, // Shorter duration
      icon: '🧙‍♂️'
    });
  };

  const handleDeleteChat = async (chatId: string, chatTitle: string) => {
    setShowChatMenu(null);

    if (window.confirm(`Are you sure you want to delete "${chatTitle}"? This action cannot be undone.`)) {
      toast.loading(`Deleting "${chatTitle}"...`, { id: "delete-chat" });

      try {
        await deleteChat(chatId);

        toast.success(`🎉 "${chatTitle}" deleted successfully!`, {
          id: "delete-chat",
          icon: '🗑️',
          duration: 3000
        });

      } catch (error) {
        console.error("Error deleting chat:", error);

        let errorMessage = `Failed to delete "${chatTitle}". Please try again.`;
        if (error instanceof Error) {
          errorMessage = `Failed to delete "${chatTitle}": ${error.message}`;
        }

        toast.error(errorMessage, {
          id: "delete-chat",
          duration: 5000
        });
      }
    }
  };

  const openRenameModal = (chatId: string, currentName: string) => {
    setRenameModal({
      isOpen: true,
      chatId,
      currentName
    });
    setShowChatMenu(null);
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

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Guru Sidebar */}
      <div
        ref={sidebarRef}
        className={`guru-sidebar fixed top-16 right-0 h-[calc(100vh-4rem)] w-1/4 min-w-80 transform transition-all duration-300 ease-in-out z-[60] ${
          isOpen ? "translate-x-0 opacity-100" : "translate-x-full opacity-0"
        } backdrop-blur-xl border-l border-purple-400/20 shadow-2xl`}
        style={{
          background: "linear-gradient(180deg, rgba(147, 51, 234, 0.08) 0%, rgba(126, 34, 206, 0.06) 30%, rgba(107, 33, 168, 0.05) 70%, rgba(88, 28, 135, 0.04) 100%)",
          backdropFilter: "blur(25px) saturate(120%)",
          borderLeft: "1px solid rgba(147, 51, 234, 0.15)",
          boxShadow: "0 25px 50px -12px rgba(147, 51, 234, 0.1), 0 0 0 1px rgba(147, 51, 234, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.05)",
          zIndex: 60 // Ensure sidebar is above other elements including navbar
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between p-6 border-b border-purple-400/20 backdrop-blur-sm"
          style={{
            background: "rgba(147, 51, 234, 0.05)",
            borderBottom: "1px solid rgba(147, 51, 234, 0.1)",
          }}
        >
          <h2 className="text-xl font-bold flex items-center gap-2">
            <img src={guruLogo} alt="Guru" className="w-6 h-6 drop-shadow-lg" />
            <span className="bg-gradient-to-r from-purple-300 to-purple-500 bg-clip-text text-transparent">Chat & Guru Manager</span>
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="text-purple-300 hover:text-white transition-all duration-200 p-2 rounded-full hover:bg-purple-400/10 hover:scale-110"
              title="Close Manager"
            >
              <FontAwesomeIcon icon={faChevronRight} size="lg" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Action Buttons */}
          <div className="flex gap-2">
            <BubblyButton
              onClick={() => setShowCreateForm(!showCreateForm)}
              variant="primary"
              className="flex-1 flex items-center justify-center gap-2 sm:gap-3 py-3 px-4 font-medium text-sm sm:text-base touch-target"
            >
              <span>Create Guru</span>
            </BubblyButton>
          </div>

          {/* Create Guru Form */}
          {showCreateForm && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleCreateGuru();
              }}
              className="backdrop-blur-sm rounded-lg p-3 sm:p-4 space-y-3 sm:space-y-4 border border-purple-400/30 animate-mobile-slide-up"
              style={{
                background: "rgba(147, 51, 234, 0.04)",
                boxShadow: "0 8px 32px rgba(147, 51, 234, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.03)",
              }}
            >
              <h3 className="text-base sm:text-lg font-semibold text-white">Create New Guru</h3>

              <div>
                <label className="block text-xs sm:text-sm font-medium text-purple-300 mb-2">
                  Guru Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="Enter guru name..."
                  required
                  className="w-full px-3 py-2.5 sm:py-2 border border-purple-400/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all backdrop-blur-sm text-sm sm:text-base touch-target"
                  style={{
                    background: "rgba(147, 51, 234, 0.03)",
                  }}
                />
              </div>

              <div>
                <label className="block text-xs sm:text-sm font-medium text-purple-300 mb-2">
                  Subject/Expertise *
                </label>
                <input
                  type="text"
                  name="subject"
                  value={formData.subject}
                  onChange={handleInputChange}
                  placeholder="e.g., Math, Physics, Programming..."
                  required
                  className="w-full px-3 py-2.5 sm:py-2 border border-purple-400/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all backdrop-blur-sm text-sm sm:text-base touch-target"
                  style={{
                    background: "rgba(147, 51, 234, 0.03)",
                  }}
                />
              </div>

              <div>
                <label className="block text-xs sm:text-sm font-medium text-purple-300 mb-2">
                  Description *
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  rows={2}
                  placeholder="Describe your guru's personality and expertise..."
                  required
                  minLength={1}
                  className="w-full px-3 py-2.5 sm:py-2 border border-purple-400/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all resize-none backdrop-blur-sm text-sm sm:text-base touch-target"
                  style={{
                    background: "rgba(147, 51, 234, 0.03)",
                  }}
                />
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end space-y-2 sm:space-y-0 sm:space-x-3 pt-2">
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2.5 sm:py-2 text-purple-300 hover:text-white transition-colors rounded-lg hover:bg-purple-400/10 text-sm sm:text-base touch-target"
                >
                  Cancel
                </button>
                <BubblyButton
                  type="submit"
                  disabled={isCreating || formData.name.length === 0 || formData.subject.length === 0 || formData.description.length === 0}
                  variant="primary"
                  className="px-6 py-2.5 sm:py-2 font-medium text-sm sm:text-base touch-target"
                >
                  {isCreating ? "Creating..." : "Create Guru"}
                </BubblyButton>
              </div>
            </form>
          )}

          {/* My Gurus Section */}
          <div className="space-y-3 sm:space-y-4">
            <button
              onClick={toggleGuruList}
              className="w-full flex items-center justify-between text-white py-2.5 sm:py-2 px-2 hover:bg-purple-400/10 rounded transition-colors touch-target"
            >
              <span className="font-medium text-base sm:text-lg">My Gurus ({gurus?.length || 0})</span>
              <FontAwesomeIcon
                icon={isGuruListExpanded ? faChevronUp : faChevronDown}
                className="text-purple-300 text-sm sm:text-base"
              />
            </button>

            {isGuruListExpanded && (
              <div className="space-y-2">

                {!gurus || gurus.length === 0 ? (
                  <div className="text-gray-300 text-center py-4">
                    <img src={guruLogo} alt="Guru" className="w-6 h-6 sm:w-8 sm:h-8 mx-auto mb-2" />
                    <p className="text-sm sm:text-base">No gurus created yet</p>
                    <p className="text-xs sm:text-sm">Create your first guru to get started!</p>
                  </div>
                ) : (
                  gurus?.map((guru) => (
                    <div
                      key={guru.id}
                      className={`backdrop-blur-sm rounded-lg p-3 border transition-all duration-300 cursor-pointer touch-target
                        hover:scale-[1.02] ${
                        selectedGuru?.id === guru.id
                          ? "border-purple-400/50 shadow-lg shadow-purple-500/20"
                          : "border-purple-400/30 hover:border-purple-400/50"
                      }`}
                      style={{
                        background: selectedGuru?.id === guru.id
                          ? "rgba(147, 51, 234, 0.08)"
                          : "rgba(147, 51, 234, 0.03)",
                        boxShadow: selectedGuru?.id === guru.id
                          ? "0 8px 32px rgba(147, 51, 234, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.05)"
                          : "0 4px 16px rgba(147, 51, 234, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.02)",
                      }}
                      onClick={() => handleGuruSelect(guru)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <img src={guruLogo} alt="Guru" className="w-3.5 h-3.5 sm:w-4 sm:h-4 flex-shrink-0" />
                            <h4 className="font-medium text-white text-xs sm:text-sm truncate">{guru.name}</h4>
                          </div>
                          <p className="text-xs text-gray-300 mb-1 truncate">{guru.subject}</p>
                          {guru.description && (
                            <p className="text-xs text-gray-400 line-clamp-2 hidden sm:block">{guru.description}</p>
                          )}
                        </div>
                        <div className="flex items-center gap-1 ml-2 flex-shrink-0">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              // TODO: Implement edit functionality
                              console.log("Edit guru:", guru.id);
                            }}
                            className="p-1.5 sm:p-1 text-purple-300 hover:text-blue-400 transition-colors rounded hover:bg-purple-400/10 touch-target"
                            title="Edit guru"
                          >
                            <FontAwesomeIcon icon={faEdit} className="text-xs" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteGuru(guru.id);
                            }}
                            className="p-1.5 sm:p-1 text-purple-300 hover:text-red-400 transition-colors rounded hover:bg-purple-400/10 touch-target"
                            title="Delete guru"
                          >
                            <FontAwesomeIcon icon={faTrash} className="text-xs" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )) || []
                )}
              </div>
            )}
          </div>

          {/* Chat Sessions Section */}
          {selectedGuru && (
            <div className="border-t border-purple-400/20 pt-4 sm:pt-6">
              {/* New Chat Button */}
              <BubblyButton
                onClick={handleCreateNewChat}
                disabled={isCreatingChat}
                variant="secondary"
                className="w-full flex items-center justify-center gap-2 sm:gap-3 py-3 px-4 font-medium text-sm sm:text-base touch-target mb-4"
              >
                <span>{isCreatingChat ? "Creating..." : "New Chat"}</span>
              </BubblyButton>

              {/* Chat Sessions List */}
              <div>
                <button
                  onClick={toggleChatList}
                  className="flex items-center justify-between w-full text-left mb-3 sm:mb-4 text-purple-300 hover:text-white transition-colors py-2 touch-target"
                >
                  <span className="text-base sm:text-lg font-semibold">
                    Chat Sessions ({getChatsByGuru(selectedGuru.id).length})
                  </span>
                  <FontAwesomeIcon
                    icon={isChatListExpanded ? faChevronUp : faChevronDown}
                    className="text-sm sm:text-base"
                  />
                </button>

                {isChatListExpanded && (
                  <div className="space-y-2 max-h-60 overflow-y-auto mobile-scroll" style={{ position: 'relative', zIndex: 1 }}>
                    {getChatsByGuru(selectedGuru.id).length === 0 ? (
                      <div className="text-gray-300 text-center py-4">
                        <p className="text-sm sm:text-base">No chat sessions yet</p>
                        <p className="text-xs sm:text-sm">Create your first chat to get started!</p>
                      </div>
                    ) : (
                      getChatsByGuru(selectedGuru.id).map((chat) => (
                        <div
                          key={chat.id}
                          className={`backdrop-blur-sm rounded-lg p-3 border transition-all duration-300 relative group
                            hover:scale-[1.02] ${
                            currentChatId === chat.id
                              ? "border-purple-400/50 shadow-lg shadow-purple-500/20"
                              : "border-purple-400/30 hover:border-purple-400/50"
                          }`}
                          style={{
                            background: currentChatId === chat.id
                              ? "rgba(147, 51, 234, 0.08)"
                              : "rgba(147, 51, 234, 0.03)",
                            boxShadow: currentChatId === chat.id
                              ? "0 8px 32px rgba(147, 51, 234, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.05)"
                              : "0 4px 16px rgba(147, 51, 234, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.02)",
                            zIndex: showChatMenu === chat.id ? 70 : 1 // Higher z-index when menu is open
                          }}
                        >
                          <div className="flex items-start justify-between">
                            <div
                              className="flex-1 min-w-0 cursor-pointer"
                              onClick={() => handleChatSelect(chat.id)}
                            >
                              <h4 className="font-medium text-white text-xs sm:text-sm truncate mb-1">
                                {chat.title}
                              </h4>
                              <div className="flex items-center gap-2 text-xs text-gray-400">
                                <span>💬 {chat.messageCount} messages</span>
                                <span>•</span>
                                <span>{new Date(chat.lastActivity).toLocaleDateString()}</span>
                              </div>
                            </div>

                            {/* Chat Menu Button */}
                            <div className="relative" style={{ zIndex: showChatMenu === chat.id ? 80 : 10 }}>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setShowChatMenu(showChatMenu === chat.id ? null : chat.id);
                                }}
                                className="p-2 text-gray-400 hover:text-white transition-all duration-200 opacity-0 group-hover:opacity-100 focus:opacity-100 hover:bg-purple-400/20 rounded-md"
                                title="Chat options"
                              >
                                <FontAwesomeIcon icon={faEllipsisV} className="text-sm" />
                              </button>

                              {/* Chat Menu Dropdown */}
                              {showChatMenu === chat.id && (
                                <div
                                  className="absolute right-0 top-8 bg-gray-900 border border-purple-400/40 rounded-lg shadow-2xl min-w-36 backdrop-blur-sm"
                                  style={{
                                    background: "rgba(17, 24, 39, 0.98)",
                                    boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.2)",
                                    zIndex: 99999,
                                    pointerEvents: 'auto'
                                  }}
                                >
                                  <button
                                    onClick={(e) => {
                                      e.preventDefault();
                                      e.stopPropagation();
                                      openRenameModal(chat.id, chat.title);
                                    }}
                                    className="w-full px-4 py-3 text-left text-sm text-gray-300 hover:text-white hover:bg-purple-600/30 transition-all duration-200 flex items-center gap-3 first:rounded-t-lg"
                                  >
                                    <FontAwesomeIcon icon={faEdit} className="text-sm text-blue-400" />
                                    <span>Rename</span>
                                  </button>
                                  <div className="border-t border-gray-700/50"></div>
                                  <button
                                    onClick={(e) => {
                                      e.preventDefault();
                                      e.stopPropagation();
                                      handleDeleteChat(chat.id, chat.title);
                                    }}
                                    className="w-full px-4 py-3 text-left text-sm text-red-400 hover:text-red-300 hover:bg-red-600/30 transition-all duration-200 flex items-center gap-3 last:rounded-b-lg font-medium"
                                  >
                                    <FontAwesomeIcon icon={faTrash} className="text-sm text-red-500" />
                                    <span>Delete</span>
                                  </button>
                                </div>
                              )}
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
        </div>
      </div>

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

export default GuruSidebar;
