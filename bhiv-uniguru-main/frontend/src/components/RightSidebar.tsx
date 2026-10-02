import React, { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTimes, faChevronDown, faChevronUp } from "@fortawesome/free-solid-svg-icons";
import BubblyButton from "./BubblyButton";

interface RightSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const RightSidebar: React.FC<RightSidebarProps> = ({ isOpen, onClose }) => {
  const [isChatHistoryExpanded, setIsChatHistoryExpanded] = useState(true);

  const toggleChatHistory = () => {
    setIsChatHistoryExpanded(!isChatHistoryExpanded);
  };

  // Mock chat history data
  const chatHistory = [
    { id: 1, title: "Previous conversation about React", date: "Today" },
    { id: 2, title: "Help with TypeScript interfaces", date: "Yesterday" },
    { id: 3, title: "CSS Grid layout questions", date: "2 days ago" },
    { id: 4, title: "JavaScript async/await", date: "3 days ago" },
    { id: 5, title: "Database design patterns", date: "1 week ago" },
  ];

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Right Sidebar */}
      <div
        className={`fixed top-0 right-0 h-full w-80 transform transition-transform duration-300 z-50 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
        style={{
          background: "linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-end p-6">
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <FontAwesomeIcon icon={faTimes} size="lg" />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="px-6 pb-4">
          <BubblyButton
            variant="success"
            className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-full"
          >
            <span className="font-medium">New Chat</span>
          </BubblyButton>
        </div>

        {/* Chat History Section */}
        <div className="px-6">
          <button
            onClick={toggleChatHistory}
            className="w-full flex items-center justify-between text-white py-3 px-2 hover:bg-gray-700 hover:bg-opacity-30 rounded transition-colors"
          >
            <span className="font-medium text-lg">Chat History</span>
            <FontAwesomeIcon
              icon={isChatHistoryExpanded ? faChevronUp : faChevronDown}
              className="text-gray-400"
            />
          </button>

          {/* Chat History List */}
          {isChatHistoryExpanded && (
            <div className="mt-4 space-y-2">
              {chatHistory.map((chat) => (
                <div
                  key={chat.id}
                  className="p-3 text-gray-300 hover:bg-gray-700 hover:bg-opacity-30 rounded-lg cursor-pointer transition-colors group"
                >
                  <div className="text-sm font-medium text-white truncate">
                    {chat.title}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">{chat.date}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer space */}
        <div className="absolute bottom-0 left-0 right-0 p-4">
          <div className="text-xs text-gray-500 text-center">
            Manage your conversations
          </div>
        </div>
      </div>
    </>
  );
};

export default RightSidebar;
