import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faRobot, faCog, faArrowLeft } from "@fortawesome/free-solid-svg-icons";
import toast from "react-hot-toast";
// BubblyButton removed for IBM Carbon
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
        <div className="cds-tile bg-white border border-[#e0e0e0] p-8 rounded-none shadow-none font-carbon">
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
            <button
              onClick={() => navigate("/chatpage")}
              className="cds-btn-secondary text-xs"
              style={{ minHeight: "40px", padding: "8px 16px" }}
            >
              <FontAwesomeIcon icon={faArrowLeft} className="text-xs mr-2" />
              <span>Back to Workspace</span>
            </button>
          </div>
          {/* Header */}
          <div className="text-left mb-10 pb-6 border-b border-[#e0e0e0]">
            <div className="text-xs font-semibold uppercase tracking-wider text-[#0f62fe] mb-1">
              Platform Utilities & Capabilities
            </div>
            <h1 className="text-3xl sm:text-4xl font-light text-[#161616] tracking-tight">
              UniGuru Native Tools
            </h1>
            <p className="text-[#525252] text-sm sm:text-base mt-2 tracking-[0.16px]">
              Specialized research, civilizational epistemology, and model tuning capabilities.
            </p>
          </div>

          {/* Tools Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Sanskrit Knowledge Decoder Tool */}
            <div className="cds-tile bg-white border border-[#e0e0e0] p-6 col-span-1 md:col-span-2 rounded-none">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-[#f4f4f4] border border-[#e0e0e0] flex items-center justify-center text-xl text-[#0f62fe] font-bold rounded-none">
                    ॐ
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-semibold text-[#161616] tracking-tight">
                        Sanskrit Knowledge Decoder
                      </h2>
                      <span className="text-[11px] px-2 py-0.5 bg-[#edf5ff] text-[#0f62fe] border border-[#d0e2ff] font-semibold tracking-wider">
                        ACTIVE RUNTIME
                      </span>
                    </div>
                    <p className="text-[#525252] text-xs tracking-[0.16px]">UniGuru Native Civilizational Intelligence Capability</p>
                  </div>
                </div>
              </div>
              <p className="text-[#525252] mb-6 text-sm leading-relaxed tracking-[0.16px]">
                Decode Sanskrit concepts through canonical epistemological pipelines — Śabda, Dhātu, Vyākaraṇa (Pāṇini), Nirukta, Bīja, Tattva, Śakti, and 35 knowledge layers verified against source provenance and replay safety.
              </p>
              <button
                className="cds-btn-primary text-xs"
                style={{ minHeight: "44px", padding: "10px 20px" }}
                onClick={() => navigate("/sanskrit-decoder")}
              >
                Launch Decoder Engine ॐ
              </button>
            </div>
            {/* Select Model Tool */}
            <div className="cds-tile bg-white border border-[#e0e0e0] p-6 rounded-none transition-colors">
              <div className="flex items-center mb-4">
                <FontAwesomeIcon icon={faRobot} className="text-2xl text-blue-500 mr-3" />
                <h2 className="text-base font-semibold text-[#161616]">Select Model</h2>
              </div>
              <p className="text-[#525252] text-sm mb-4 tracking-[0.16px]">
                Choose from different AI models to customize your chat experience and get responses tailored to your needs.
              </p>
              <button
                className="cds-btn-secondary text-xs"
                style={{ minHeight: "40px", padding: "8px 16px" }}
                onClick={() => {
                  toast.success("Model configuration coming soon!", {
                    icon: '🤖',
                    duration: 3000
                  });
                }}
              >
                Configure Model
              </button>
            </div>

            {/* Scrape Data Tool */}
            <div className="cds-tile bg-white border border-[#e0e0e0] p-6 rounded-none transition-colors">
              <div className="flex items-center mb-4">
                <FontAwesomeIcon icon={faCog} className="text-2xl text-green-500 mr-3" />
                <h2 className="text-base font-semibold text-[#161616]">Scrape Data</h2>
              </div>
              <p className="text-[#525252] text-sm mb-4 tracking-[0.16px]">
                Extract and analyze data from various sources to enhance your learning and research capabilities.
              </p>
              <button
                className="cds-btn-secondary text-xs"
                style={{ minHeight: "40px", padding: "8px 16px" }}
                onClick={() => {
                  toast.success("Data scraping feature coming soon!", {
                    icon: '🔧',
                    duration: 3000
                  });
                }}
              >
                Start Scraping
              </button>
            </div>
          </div>

          {/* Coming Soon Section */}
          <div className="mt-12">
            <h3 className="text-lg font-semibold text-[#161616] mb-4 text-left border-t border-[#e0e0e0] pt-8">Upcoming Platform Extensions</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="cds-tile bg-[#f4f4f4] border border-[#e0e0e0] p-4 text-left rounded-none">
                <div className="text-gray-500 mb-2">📊</div>
                <h4 className="text-[#161616] font-medium text-sm">Analytics Dashboard</h4>
                <p className="text-[#525252] text-xs mt-1">Track your learning progress</p>
              </div>
              <div className="cds-tile bg-[#f4f4f4] border border-[#e0e0e0] p-4 text-left rounded-none">
                <div className="text-gray-500 mb-2">🔧</div>
                <h4 className="text-[#161616] font-medium text-sm">Custom Integrations</h4>
                <p className="text-[#525252] text-xs mt-1">Connect external services</p>
              </div>
              <div className="cds-tile bg-[#f4f4f4] border border-[#e0e0e0] p-4 text-left rounded-none">
                <div className="text-gray-500 mb-2">📝</div>
                <h4 className="text-[#161616] font-medium text-sm">Note Taking</h4>
                <p className="text-[#525252] text-xs mt-1">Save and organize your insights</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ToolsPage;
