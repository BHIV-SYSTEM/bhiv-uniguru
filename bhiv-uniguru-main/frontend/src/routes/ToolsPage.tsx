import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRobot, faCog, faTools, faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import toast from "react-hot-toast";
import BubblyButton from "../components/BubblyButton";
import LoadingSpinner from "../components/LoadingSpinner";

const ToolsPage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);

  // Simulate loading for better UX
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 600);

    return () => clearTimeout(timer);
  }, []);

  if (isLoading) {
    return (
      <div className="relative min-h-screen flex items-center justify-center">
        <div className="bg-glass-card backdrop-blur-xl rounded-xl p-8 border border-glass-border shadow-glass">
          <LoadingSpinner
            size="large"
            variant="gradient-ring"
            text="Loading tools..."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Back Button */}
          <div className="mb-6">
            <BubblyButton
              onClick={() => navigate("/chatpage")}
              variant="primary"
              className="flex items-center space-x-2 px-4 py-2 text-sm font-medium"
            >
              <FontAwesomeIcon icon={faArrowLeft} className="text-sm" />
              <span>Back to Chat</span>
            </BubblyButton>
          </div>
          {/* Header */}
          <div className="text-center mb-12">
            <div className="flex items-center justify-center mb-4">
              <FontAwesomeIcon icon={faTools} className="text-4xl text-yellow-500 mr-3" />
              <h1 className="text-4xl font-bold bg-gradient-to-r from-yellow-400 via-yellow-500 to-yellow-600 bg-clip-text text-transparent">
                Tools
              </h1>
            </div>
            <p className="text-gray-300 text-lg">
              Enhance your UniGuru experience with these powerful tools
            </p>
          </div>

          {/* Tools Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Sanskrit Knowledge Decoder Tool */}
            <div className="bg-purple-950/30 backdrop-blur-sm border border-purple-600/50 rounded-lg p-6 hover:bg-purple-900/40 transition-all duration-200 col-span-1 md:col-span-2 shadow-lg shadow-purple-950/50">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className="w-10 h-10 rounded-lg bg-purple-800 flex items-center justify-center text-xl text-purple-200 mr-3 font-bold">
                    ॐ
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                      Sanskrit Knowledge Decoder
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-700 font-medium">
                        LIVE FEATURE
                      </span>
                    </h2>
                    <p className="text-purple-300 text-xs">UniGuru Native Civilizational Intelligence Capability</p>
                  </div>
                </div>
              </div>
              <p className="text-gray-300 mb-4 text-sm leading-relaxed">
                Decode Sanskrit concepts through their own epistemology — Śabda, Dhātu, Vyākaraṇa (Pāṇini), Nirukta, Bīja, Tattva, Śakti, and 35 civilizational knowledge layers backed by evidence classification and deterministic replay.
              </p>
              <BubblyButton
                variant="primary"
                className="px-6 py-2.5 font-semibold text-sm"
                style={{
                  background: 'linear-gradient(135deg, #7c3aed, #4c1d95)',
                  color: 'white'
                }}
                onClick={() => navigate("/sanskrit-decoder")}
              >
                Launch Decoder Engine ॐ
              </BubblyButton>
            </div>
            {/* Select Model Tool */}
            <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6 hover:bg-gray-800/50 transition-all duration-200">
              <div className="flex items-center mb-4">
                <FontAwesomeIcon icon={faRobot} className="text-2xl text-blue-500 mr-3" />
                <h2 className="text-xl font-semibold text-white">Select Model</h2>
              </div>
              <p className="text-gray-300 mb-4">
                Choose from different AI models to customize your chat experience and get responses tailored to your needs.
              </p>
              <BubblyButton
                variant="primary"
                className="px-4 py-2"
                style={{
                  background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
                  color: 'white'
                }}
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
            <div className="bg-gray-900/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6 hover:bg-gray-800/50 transition-all duration-200">
              <div className="flex items-center mb-4">
                <FontAwesomeIcon icon={faCog} className="text-2xl text-green-500 mr-3" />
                <h2 className="text-xl font-semibold text-white">Scrape Data</h2>
              </div>
              <p className="text-gray-300 mb-4">
                Extract and analyze data from various sources to enhance your learning and research capabilities.
              </p>
              <BubblyButton
                variant="success"
                className="px-4 py-2"
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

          {/* Coming Soon Section */}
          <div className="mt-12">
            <h3 className="text-2xl font-semibold text-white mb-6 text-center">Coming Soon</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-gray-900/30 backdrop-blur-sm border border-gray-800 rounded-lg p-4 text-center">
                <div className="text-gray-500 mb-2">📊</div>
                <h4 className="text-white font-medium">Analytics Dashboard</h4>
                <p className="text-gray-400 text-sm mt-1">Track your learning progress</p>
              </div>
              <div className="bg-gray-900/30 backdrop-blur-sm border border-gray-800 rounded-lg p-4 text-center">
                <div className="text-gray-500 mb-2">🔧</div>
                <h4 className="text-white font-medium">Custom Integrations</h4>
                <p className="text-gray-400 text-sm mt-1">Connect external services</p>
              </div>
              <div className="bg-gray-900/30 backdrop-blur-sm border border-gray-800 rounded-lg p-4 text-center">
                <div className="text-gray-500 mb-2">📝</div>
                <h4 className="text-white font-medium">Note Taking</h4>
                <p className="text-gray-400 text-sm mt-1">Save and organize your insights</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ToolsPage;
