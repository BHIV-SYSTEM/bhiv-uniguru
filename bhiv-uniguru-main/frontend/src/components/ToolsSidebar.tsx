import React, { useState, useRef, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faChevronLeft,
  faTools,
  faRobot,
  faCog,
  faChevronDown,
  faChevronUp
} from "@fortawesome/free-solid-svg-icons";
import toast from "react-hot-toast";
import BubblyButton from "./BubblyButton";

interface ToolsSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const ToolsSidebar: React.FC<ToolsSidebarProps> = ({ isOpen, onClose }) => {
  const [isToolsExpanded, setIsToolsExpanded] = useState(true);
  const sidebarRef = useRef<HTMLDivElement>(null);

  const toggleTools = () => {
    setIsToolsExpanded(!isToolsExpanded);
  };

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

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Tools Sidebar */}
      <div
        ref={sidebarRef}
        className={`fixed top-16 left-0 h-[calc(100vh-4rem)] w-1/4 min-w-80 transform transition-all duration-300 ease-in-out z-40 ${
          isOpen ? "translate-x-0 opacity-100" : "-translate-x-full opacity-0"
        } backdrop-blur-xl border-r border-yellow-400/20 shadow-2xl`}
        style={{
          background: "linear-gradient(180deg, rgba(251, 191, 36, 0.08) 0%, rgba(245, 158, 11, 0.06) 30%, rgba(217, 119, 6, 0.05) 70%, rgba(180, 83, 9, 0.04) 100%)",
          backdropFilter: "blur(25px) saturate(120%)",
          borderRight: "1px solid rgba(251, 191, 36, 0.15)",
          boxShadow: "0 25px 50px -12px rgba(251, 191, 36, 0.1), 0 0 0 1px rgba(251, 191, 36, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.05)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between p-4 sm:p-6 border-b border-yellow-400/20 backdrop-blur-sm mobile:pt-6"
          style={{
            background: "rgba(251, 191, 36, 0.05)",
            borderBottom: "1px solid rgba(251, 191, 36, 0.1)",
          }}
        >
          <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
            <FontAwesomeIcon icon={faTools} className="text-yellow-400 drop-shadow-lg text-base sm:text-lg" />
            <span className="bg-gradient-to-r from-yellow-300 to-yellow-500 bg-clip-text text-transparent">Tools</span>
          </h2>
          <button
            onClick={onClose}
            className="text-yellow-300 hover:text-white transition-all duration-200 p-2 rounded-full hover:bg-yellow-400/10 hover:scale-110 touch-target"
            title="Close Tools"
          >
            <FontAwesomeIcon icon={faChevronLeft} size="lg" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 sm:space-y-6 mobile-scroll">
          {/* Available Tools Section */}
          <div>
            <button
              onClick={toggleTools}
              className="flex items-center justify-between w-full text-left mb-3 sm:mb-4 text-yellow-300 hover:text-white transition-colors py-2 touch-target"
            >
              <span className="text-base sm:text-lg font-semibold">Available Tools</span>
              <FontAwesomeIcon icon={isToolsExpanded ? faChevronUp : faChevronDown} className="text-sm sm:text-base" />
            </button>

            {isToolsExpanded && (
              <div className="space-y-3 sm:space-y-4 animate-mobile-fade-in">
                {/* Select Model Tool */}
                <div
                  className="backdrop-blur-sm rounded-lg p-3 sm:p-4 border border-yellow-400/30 hover:border-yellow-400/50 transition-all duration-300 hover:scale-[1.02] touch-target"
                  style={{
                    background: "rgba(251, 191, 36, 0.04)",
                    boxShadow: "0 8px 32px rgba(251, 191, 36, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.03)",
                  }}
                >
                  <div className="flex items-center mb-2 sm:mb-3">
                    <FontAwesomeIcon icon={faRobot} className="text-lg sm:text-xl text-yellow-400 mr-2 sm:mr-3" />
                    <h3 className="text-base sm:text-lg font-semibold text-white">Select Model</h3>
                  </div>
                  <p className="text-gray-200 text-xs sm:text-sm mb-2 sm:mb-3 leading-relaxed">
                    Choose from different AI models to customize your chat experience and get responses tailored to your needs.
                  </p>
                  <BubblyButton
                    variant="secondary"
                    className="px-3 py-2 sm:py-1.5 text-xs sm:text-sm touch-target"
                    onClick={() => {
                      toast.success("Model configuration coming soon!", {
                        icon: '🤖',
                        duration: 3000
                      });
                    }}
                  >
                    Configure Model
                  </BubblyButton>
                </div>

                {/* Scrape Data Tool */}
                <div className="bg-gray-800/30 rounded-lg p-4 border border-gray-700 hover:border-gray-600 transition-all">
                  <div className="flex items-center mb-3">
                    <FontAwesomeIcon icon={faCog} className="text-xl text-green-500 mr-3" />
                    <h3 className="text-lg font-semibold text-white">Scrape Data</h3>
                  </div>
                  <p className="text-gray-300 text-sm mb-3">
                    Extract and analyze data from various sources to enhance your learning and research capabilities.
                  </p>
                  <BubblyButton
                    variant="success"
                    className="px-3 py-1.5 text-sm"
                    onClick={() => {
                      toast.success("Data scraping feature coming soon!", {
                        icon: '🔧',
                        duration: 3000
                      });
                    }}
                  >
                    Start Scraping
                  </BubblyButton>
                </div>
              </div>
            )}
          </div>

          {/* Coming Soon Section */}
          <div>
            <h3 className="text-lg font-semibold text-yellow-300 mb-4">Coming Soon</h3>
            <div className="space-y-3">
              <div
                className="backdrop-blur-sm border border-yellow-400/20 rounded-lg p-3 transition-all duration-300 hover:scale-[1.02]"
                style={{
                  background: "rgba(251, 191, 36, 0.03)",
                  boxShadow: "0 4px 16px rgba(251, 191, 36, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.02)",
                }}
              >
                <div className="flex items-center gap-3">
                  <div className="text-yellow-400 text-lg">📊</div>
                  <div>
                    <h4 className="text-white font-medium text-sm">Analytics Dashboard</h4>
                    <p className="text-gray-300 text-xs">Track your learning progress</p>
                  </div>
                </div>
              </div>
              <div
                className="backdrop-blur-sm border border-yellow-400/20 rounded-lg p-3 transition-all duration-300 hover:scale-[1.02]"
                style={{
                  background: "rgba(251, 191, 36, 0.03)",
                  boxShadow: "0 4px 16px rgba(251, 191, 36, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.02)",
                }}
              >
                <div className="flex items-center gap-3">
                  <div className="text-yellow-400 text-lg">🔧</div>
                  <div>
                    <h4 className="text-white font-medium text-sm">Custom Integrations</h4>
                    <p className="text-gray-300 text-xs">Connect external services</p>
                  </div>
                </div>
              </div>
              <div
                className="backdrop-blur-sm border border-yellow-400/20 rounded-lg p-3 transition-all duration-300 hover:scale-[1.02]"
                style={{
                  background: "rgba(251, 191, 36, 0.03)",
                  boxShadow: "0 4px 16px rgba(251, 191, 36, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.02)",
                }}
              >
                <div className="flex items-center gap-3">
                  <div className="text-yellow-400 text-lg">📝</div>
                  <div>
                    <h4 className="text-white font-medium text-sm">Note Taking</h4>
                    <p className="text-gray-300 text-xs">Save and organize your insights</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          className="absolute bottom-0 left-0 right-0 p-4 border-t border-yellow-400/20 backdrop-blur-sm"
          style={{
            background: "rgba(251, 191, 36, 0.04)",
            borderTop: "1px solid rgba(251, 191, 36, 0.1)",
          }}
        >
          <div className="text-xs text-gray-300 text-center">
            Enhance your UniGuru experience
          </div>
        </div>
      </div>
    </>
  );
};

export default ToolsSidebar;
