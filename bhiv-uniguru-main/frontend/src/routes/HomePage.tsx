// "use client";

import React, { useRef, useState } from "react";
import i18n from "../i18n";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faRocket,
  faBrain
} from "@fortawesome/free-solid-svg-icons";
import BHI from "../assets/blackhole-logo.png";
import uniLogo from "../assets/uni-logo.png";
import { useAuth } from "../context/AuthContext";
// import StarsCanvas from "../components/StarBackground";
const guruLogo = "/guru.png";

interface HomePageProps {
  onChatStarted: () => void;
}

const HomePage: React.FC<HomePageProps> = ({ onChatStarted }) => {
  const [isLetChatVisible, setIsLetChatVisible] = useState(true);
  const welcomeContainerRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();
  const { isLoggedIn, isAuthLoading } = useAuth();

  // Simple language helper to hardcode localized strings without expanding i18n resources
  const L = (en: string, hi: string, mr: string) => (i18n.language === 'hi' ? hi : i18n.language === 'mr' ? mr : en);

  const buttonClasses = [
    "group relative px-8 py-4 bg-transparent border-2 border-purple-400 text-purple-400",
    "font-bold text-lg rounded-lg hover:text-white hover:border-transparent",
    "transition-all duration-300 ease-out overflow-hidden",
    "shadow-[0_0_20px_rgba(147,51,234,0.3)]",
    "hover:shadow-[0_0_40px_rgba(147,51,234,0.8),0_0_60px_rgba(59,130,246,0.4)]",
    "backdrop-blur-sm"
  ].join(" ");

  const handleLetChatClick = () => {
    if (isAuthLoading || !isLoggedIn) {
      navigate("/login");
      return;
    }
    setIsLetChatVisible(false);
    onChatStarted();
    navigate("/chatpage");
  };

  return (
    <div className="relative min-h-screen">
      {/* Mobile Layout - WITH CONTEXT & BETTER POSITIONING */}
      <main className="block sm:hidden">
        <div className="h-screen flex flex-col p-4 pt-20 overflow-hidden">
          {/* Header with Context */}
          <div className="text-center flex-shrink-0 mb-6">
            <img src={uniLogo} alt="UniGuru" className="w-20 h-20 mx-auto mb-3" />
            <h1
              className="text-4xl font-bold bg-clip-text text-transparent mb-2"
              style={{
                fontFamily: "inknut",
                background: "linear-gradient(135deg, #b18615, #d4a01c, #f7c52d, #d4a01c, #b18615)",
                backgroundClip: "text",
                WebkitBackgroundClip: "text"
              }}
            >
              UniGuru
            </h1>
            <p className="text-base text-gray-200 font-light mb-3">{L('AI Learning Platform', 'एआई लर्निंग प्लेटफॉर्म', 'एआय शिक्षण प्लॅटफॉर्म')}</p>

            {/* Context Box */}
            <div className="bg-white/5 backdrop-blur-xl rounded-xl p-3 border border-purple-400/20 mb-4">
              <p className="text-sm text-gray-100 leading-relaxed">
                {L(
                  'Welcome to UniGuru! ',
                  'UniGuru में आपका स्वागत है! ',
                  'UniGuru मध्ये आपले स्वागत आहे! '
                )}
                <span className="text-purple-400 font-semibold">{L('Create your own AI mentors', 'अपने AI मेंटर्स बनाएं', 'आपले AI गुरु तयार करा')}</span>
                {L(' and start learning with experts in any field', ' और किसी भी विषय के विशेषज्ञों के साथ सीखना शुरू करें', ' आणि कोणत्याही क्षेत्रातील तज्ञांसोबत शिकायला सुरुवात करा')}
              </p>
            </div>
          </div>

          {/* Features - Centered */}
          <div className="flex-1 flex flex-col justify-center min-h-0">
            <div className="space-y-3 mb-4">
              <div className="flex items-center space-x-3 p-3 bg-white/5 rounded-xl border border-purple-400/20">
                <img src={guruLogo} alt="Create" className="w-8 h-8 flex-shrink-0" />
                <div>
                  <h3 className="text-base font-bold text-white">{L('Create Your Guru', 'अपना गुरु बनाएं', 'आपला गुरू तयार करा')}</h3>
                  <p className="text-xs text-gray-300">{L('Math professor, scientist, code mentor - any expert', 'गणित प्रोफेसर, वैज्ञानिक, कोड मेंटर - कोई भी विशेषज्ञ', 'गणित प्राध्यापक, वैज्ञानिक, कोड मार्गदर्शक - कोणताही तज्ज्ञ')}</p>
                </div>
              </div>

              <div className="flex items-center space-x-3 p-3 bg-white/5 rounded-xl border border-blue-400/20">
                <FontAwesomeIcon icon={faBrain} className="text-blue-400 text-xl w-8 flex-shrink-0" />
                <div>
                  <h3 className="text-base font-bold text-white">{L('AI Roleplay', 'एआई रोलप्ले', 'एआय भूमिका')}</h3>
                  <p className="text-xs text-gray-300">{L('Your mentor thinks and responds like a real expert', 'आपका मेंटर एक वास्तविक विशेषज्ञ की तरह सोचता और जवाब देता है', 'तुमचा गुरु खऱ्या तज्ञासारखा विचार करतो आणि प्रतिसाद देतो')}</p>
                </div>
              </div>

              <div className="flex items-center space-x-3 p-3 bg-white/5 rounded-xl border border-green-400/20">
                <FontAwesomeIcon icon={faRocket} className="text-green-400 text-xl w-8 flex-shrink-0" />
                <div>
                  <h3 className="text-base font-bold text-white">{L('Learn Faster', 'तेजी से सीखें', 'लवकर शिका')}</h3>
                  <p className="text-xs text-gray-300">{L('Get personalized insights and authentic knowledge', 'व्यक्तिगत अंतर्दृष्टि और प्रामाणिक ज्ञान प्राप्त करें', 'वैयक्तिक अंतर्दृष्टी आणि अस्सल ज्ञान मिळवा')}</p>
                </div>
              </div>
            </div>

            {/* CTA Button - Moved Up Here */}
            <div className="text-center">
              {isLetChatVisible && (
                <button
                  onClick={handleLetChatClick}
                  className={buttonClasses}
                  style={{ fontFamily: "Inter, system-ui, sans-serif", fontWeight: "600", letterSpacing: "0.05em" }}
                >
                  {/* Animated background fill */}
                  <div className="absolute inset-0 bg-gradient-to-r from-purple-600 via-blue-600 to-cyan-600
                                transform scale-x-0 group-hover:scale-x-100
                                transition-transform duration-300 ease-out origin-left"></div>

                  {/* Button content */}
                  <div className="relative z-10 flex items-center justify-center gap-3">
                    <div className="w-0 h-0 border-l-[8px] border-l-purple-400 group-hover:border-l-white
                                  border-t-[6px] border-t-transparent
                                  border-b-[6px] border-b-transparent
                                  transition-colors duration-300"></div>
                    <span className="tracking-wide">START CREATING</span>
                  </div>

                  {/* Corner accents */}
                  <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-purple-400 group-hover:border-white transition-colors duration-300"></div>
                  <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-purple-400 group-hover:border-white transition-colors duration-300"></div>
                  <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-purple-400 group-hover:border-white transition-colors duration-300"></div>
                  <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-purple-400 group-hover:border-white transition-colors duration-300"></div>
                </button>
              )}
            </div>
          </div>

          {/* Bottom Examples */}
          <div className="text-center flex-shrink-0 pb-4">
            <p className="text-xs text-gray-400 mb-2">{L('Popular: Math • Science • Coding • Languages', 'लोकप्रिय: गणित • विज्ञान • कोडिंग • भाषाएँ', 'लोकप्रिय: गणित • विज्ञान • कोडिंग • भाषा')}</p>
          </div>
        </div>
      </main>

      {/* Desktop Layout - Original */}
      <main className="hidden sm:flex flex-col items-center justify-center min-h-screen text-center p-4 pt-20 relative z-10">
        <div
          ref={welcomeContainerRef}
          className="welcome-container p-8 max-w-6xl mx-auto relative w-full"
        >
          {/* Main Logo/Icon */}
          <div className="mb-4 flex justify-center">
            <div className="relative group">
              <img
                src={uniLogo}
                alt="UniGuru"
                className="w-36 h-36 sm:w-44 sm:h-44 mx-auto mb-3 animate-float drop-shadow-2xl group-hover:scale-105 transition-all duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-full blur-lg -z-10"></div>
            </div>
          </div>

          {/* Main Heading */}
          <h1
            className="text-3xl sm:text-4xl lg:text-5xl font-bold bg-clip-text text-transparent mb-3 bg-gradient-to-r from-yellow-600 via-yellow-500 to-yellow-400 drop-shadow-lg"
            style={{
              fontFamily: "inknut",
              background: "linear-gradient(135deg, #b18615, #d4a01c, #f7c52d, #d4a01c, #b18615)",
              backgroundClip: "text",
              WebkitBackgroundClip: "text"
            }}
          >
            UniGuru
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg lg:text-xl text-gray-200 mb-4 font-light max-w-3xl mx-auto leading-relaxed">
            {L('Create AI Mentors Who Roleplay as Real Experts', 'ऐसे एआई मेंटर्स बनाएं जो वास्तविक विशेषज्ञों जैसा रोलप्ले करें', 'खरे तज्ञांसारखी भूमिका निभावणारे एआय गुरु तयार करा')}
          </p>

          {/* Main Description */}
          <div className="max-w-3xl mx-auto mb-6">
            <p className="text-sm sm:text-base lg:text-lg text-gray-100 leading-relaxed mb-4 font-light">
              {L('Welcome to UniGuru! Start your learning journey by creating your own ', 'UniGuru में आपका स्वागत है! अपनी सीखने की यात्रा की शुरुआत अपने ', 'UniGuru मध्ये आपले स्वागत आहे! आपली शिकण्याची यात्रा सुरू करा आपल्या ')}
              <span className="text-purple-400 font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">{L('AI Gurus', 'एआई गुरुओं', 'एआय गुरूं')}</span>
              {L('. Whether you need a mathematician, scientist, or philosopher, your AI mentors will guide you with personalized, expert-level knowledge. Let\'s begin your adventure in learning!', ' बनाकर। चाहे आपको गणितज्ञ, वैज्ञानिक या दार्शनिक की आवश्यकता हो, आपके एआई मेंटर्स व्यक्तिगत और विशेषज्ञ-स्तरीय ज्ञान के साथ आपका मार्गदर्शन करेंगे। आइए सीखने की आपकी यात्रा शुरू करें!', ' तयार करून. तुम्हाला गणितज्ञ, वैज्ञानिक किंवा तत्त्वज्ञ हवा असो, तुमचे एआय गुरु वैयक्तिक, तज्ञ-स्तरीय ज्ञानासह तुम्हाला मार्गदर्शन करतील. चला शिकण्याचा तुमचा प्रवास सुरू करूया!')}
            </p>
          </div>

          {/* Interactive Feature Cards - Hover to reveal */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6 max-w-4xl mx-auto">
            <div className="group backdrop-blur-xl bg-white/5 rounded-xl p-4 border border-purple-400/20 hover:border-purple-400/60 hover:bg-white/10 transition-all duration-300 cursor-pointer text-center hover:scale-105 hover:shadow-lg hover:shadow-purple-500/20">
              <div className="flex justify-center mb-2">
                <img src={guruLogo} alt="Guru" className="w-5 h-5 group-hover:scale-110 transition-all duration-300 drop-shadow-sm" />
              </div>
              <h3 className="text-sm font-bold text-white mb-1">{L('Create', 'बनाएं', 'तयार करा')}</h3>
              <p className="text-xs text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                {L('Define any expert mentor', 'किसी भी विशेषज्ञ मेंटर को परिभाषित करें', 'कोणताही तज्ज्ञ गुरु परिभाषित करा')}
              </p>
            </div>

            <div className="group backdrop-blur-xl bg-white/5 rounded-xl p-4 border border-blue-400/20 hover:border-blue-400/60 hover:bg-white/10 transition-all duration-300 cursor-pointer text-center hover:scale-105 hover:shadow-lg hover:shadow-blue-500/20">
              <div className="flex justify-center mb-2">
                <FontAwesomeIcon icon={faBrain} className="text-blue-400 text-xl group-hover:scale-110 group-hover:text-blue-300 transition-all duration-300" />
              </div>
              <h3 className="text-sm font-bold text-white mb-1">{L('Roleplay', 'रोलप्ले', 'भूमिका')}</h3>
              <p className="text-xs text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                {L('AI embodies their expertise', 'एआई उनकी विशेषज्ञता को आत्मसात करता है', 'एआय त्यांच्या तज्ज्ञतेला मूर्त रूप देतो')}
              </p>
            </div>

            <div className="group backdrop-blur-xl bg-white/5 rounded-xl p-4 border border-green-400/20 hover:border-green-400/60 hover:bg-white/10 transition-all duration-300 cursor-pointer text-center hover:scale-105 hover:shadow-lg hover:shadow-green-500/20">
              <div className="flex justify-center mb-2">
                <FontAwesomeIcon icon={faRocket} className="text-green-400 text-xl group-hover:scale-110 group-hover:text-green-300 transition-all duration-300" />
              </div>
              <h3 className="text-sm font-bold text-white mb-1">{L('Learn', 'सीखें', 'शिका')}</h3>
              <p className="text-xs text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                {L('Get authentic insights', 'प्रामाणिक अंतर्दृष्टि प्राप्त करें', 'अस्सल अंतर्दृष्टी मिळवा')}
              </p>
            </div>
          </div>

          {/* Popular Guru Types - Compact */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-300 mb-3 text-center">{L('Popular Mentor Types', 'लोकप्रिय मेंटर प्रकार', 'लोकप्रिय मेंटर प्रकार')}</h3>
            <div className="flex flex-wrap justify-center gap-2 max-w-3xl mx-auto">
              {[
                "Math Professor", "Scientist", "Philosopher",
                "Historian", "Code Mentor", "Language Tutor"
              ].map((guru, index) => (
                <span
                  key={index}
                  className="px-3 py-1.5 text-xs bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-full text-gray-200 border border-purple-400/30 hover:border-purple-400/60 hover:text-white hover:bg-gradient-to-r hover:from-purple-500/40 hover:to-blue-500/40 transition-all duration-300 cursor-pointer backdrop-blur-sm hover:scale-105"
                >
                  {guru}
                </span>
              ))}
            </div>
          </div>

          {/* CTA Button - Custom Neon Style */}
          <div className="flex justify-center mt-4">
            {isLetChatVisible && (
              <button
                onClick={handleLetChatClick}
                className={[
                  "group relative px-8 py-4 bg-transparent border-2",
                  "border-purple-400 text-purple-400",
                  "font-bold text-lg rounded-lg hover:text-white hover:border-transparent",
                  "transition-all duration-300 ease-out overflow-hidden",
                  "shadow-[0_0_20px_rgba(147,51,234,0.3)]",
                  "hover:shadow-[0_0_40px_rgba(147,51,234,0.8),0_0_60px_rgba(59,130,246,0.4)]",
                  "backdrop-blur-sm"
                ].join(" ")}
                style={{ fontFamily: "Inter, system-ui, sans-serif", fontWeight: "600", letterSpacing: "0.05em" }}
              >
                {/* Animated background fill */}
                <div className="absolute inset-0 bg-gradient-to-r from-purple-600 via-blue-600 to-cyan-600
                              transform scale-x-0 group-hover:scale-x-100
                              transition-transform duration-300 ease-out origin-left"></div>

                {/* Button content */}
                <div className="relative z-10 flex items-center justify-center gap-3">
                  <div className="w-0 h-0 border-l-[8px] border-l-purple-400 group-hover:border-l-white
                                border-t-[6px] border-t-transparent
                                border-b-[6px] border-b-transparent
                                transition-colors duration-300"></div>
                  <span className="tracking-wide">START CREATING</span>
                </div>

                {/* Corner accents */}
                <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-purple-400 group-hover:border-white transition-colors duration-300"></div>
                <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 border-purple-400 group-hover:border-white transition-colors duration-300"></div>
                <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 border-purple-400 group-hover:border-white transition-colors duration-300"></div>
                <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-purple-400 group-hover:border-white transition-colors duration-300"></div>
              </button>
            )}
          </div>
        </div>
      </main>

      {/* Footer with blackhole logo - Hidden on mobile */}
      <footer className="absolute bottom-5 right-5 z-10 hidden sm:block">
        <a 
          href="https://blackholeinfiverse.com/" 
          target="_blank" 
          rel="noopener noreferrer"
          className="block hover:scale-105 transition-transform duration-200"
        >
          <img src={BHI} alt="BHI Logo" className="h-12" />
        </a>
      </footer>
    </div>
  );
};

export default HomePage;
