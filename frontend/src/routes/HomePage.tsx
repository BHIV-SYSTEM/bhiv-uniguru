import React, { useState } from "react";
import i18n from "../i18n";
import { useNavigate } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowRight,
  faBrain,
  faLayerGroup,
  faBookOpen,
  faCheck,
  faCode,
  faMicroscope,
  faAtom
} from "@fortawesome/free-solid-svg-icons";
import BHI from "../assets/blackhole-logo.png";
import uniLogo from "../assets/uni-logo.png";
import { useAuth } from "../context/AuthContext";

interface HomePageProps {
  onChatStarted: () => void;
}

const HomePage: React.FC<HomePageProps> = ({ onChatStarted }) => {
  const [selectedTab, setSelectedTab] = useState<number>(0);
  const navigate = useNavigate();
  const { isLoggedIn, isAuthLoading } = useAuth();

  // Language helper strictly localized without breaking i18n
  const L = (en: string, hi: string, mr: string) => (i18n.language === 'hi' ? hi : i18n.language === 'mr' ? mr : en);

  const handleLetChatClick = () => {
    if (isAuthLoading || !isLoggedIn) {
      navigate("/login");
      return;
    }
    onChatStarted();
    navigate("/chatpage");
  };

  const mentorPresets = [
    {
      category: L("STEM & Mathematics", "गणित और विज्ञान", "गणित आणि विज्ञान"),
      title: L("Advanced Mathematics Professor", "उन्नत गणित प्रोफेसर", "प्रगत गणित प्राध्यापक"),
      tagline: L("Rigorous calculus, linear algebra, and discrete math instruction.", "कलन, रेखीय बीजगणित और विविक्त गणित का गहन मार्गदर्शन।", "कलन, रेखीय बीजगणित आणि विविक्त गणिताचे सखोल मार्गदर्शन."),
      icon: faAtom,
      topics: ["Multivariable Calculus", "Linear Algebra", "Proof Verification", "Number Theory"]
    },
    {
      category: L("Computer Science", "कंप्यूटर विज्ञान", "संगणक विज्ञान"),
      title: L("Systems Architect & Code Mentor", "सिस्टम्स आर्किटेक्ट और कोड मेंटर", "सिस्टम आर्किटेक्ट आणि कोड मेंटर"),
      tagline: L("Production engineering, algorithmic complexity, and idiomatic clean code.", "उत्पादन इंजीनियरिंग, एल्गोरिदमिक जटिलता और स्वच्छ कोड।", "प्रॉडक्शन अभियांत्रिकी, अल्गोरिदमिक जटिलता आणि स्वच्छ कोड."),
      icon: faCode,
      topics: ["Distributed Systems", "Data Structures", "TypeScript & Rust", "API Architecture"]
    },
    {
      category: L("Ancient Sciences & Sanskrit", "प्राचीन विज्ञान और संस्कृत", "प्राचीन विज्ञान आणि संस्कृत"),
      title: L("Sanskrit Epistemology Decoder", "संस्कृत ज्ञानमीमांसा डिकोडर", "संस्कृत ज्ञानमीमांसा डिकोडर"),
      tagline: L("Authentic Vedic epistemology, grammatical parsing, and root analysis.", "प्रामाणिक वैदिक ज्ञानमीमांसा, व्याकरण और मूल धातु विश्लेषण।", "अस्सल वैदिक ज्ञानमीमांसा, व्याकरण आणि मूळ धातू विश्लेषण."),
      icon: faBookOpen,
      topics: ["Sanskrit Grammar", "Tantra & Epistemology", "Etymology (Nirukta)", "Logic (Nyaya)"]
    },
    {
      category: L("Sciences & Physics", "भौतिकी और विज्ञान", "भौतिकशास्त्र आणि विज्ञान"),
      title: L("Theoretical Physics Mentor", "सैद्धांतिक भौतिकी मेंटर", "सैद्धांतिक भौतिकशास्त्र मार्गदर्शक"),
      tagline: L("Conceptual clarity, thought experiments, and mathematical models.", "वैचारिक स्पष्टता, विचार प्रयोग और गणितीय मॉडल।", "वैचारिक स्पष्टता, विचार प्रयोग आणि गणितीय मॉडेल्स."),
      icon: faMicroscope,
      topics: ["Classical Mechanics", "Quantum States", "Thermodynamics", "Relativity"]
    }
  ];

  return (
    <div className="w-full bg-[#ffffff] text-[#161616] font-carbon pt-24 sm:pt-28">
      {/* 2. Hero Section (IBM Carbon Display 60-76px weight 300) */}
      <section className="relative px-6 sm:px-12 lg:px-16 pt-8 pb-20 border-b border-[#e0e0e0] max-w-[1584px] mx-auto">
        <div className="max-w-4xl">
          {/* Eyebrow */}
          <div className="text-sm font-normal text-[#525252] mb-4 tracking-[0.16px]">
            {L("Curated Artificial Intelligence Platform", "क्यूरेटेड कृत्रिम बुद्धिमत्ता प्लेटफॉर्म", "क्युरेटेड कृत्रिम बुद्धिमत्ता व्यासपीठ")}
          </div>

          {/* Display Headline - Weight 300, Carbon signature */}
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-light text-[#161616] tracking-[-0.4px] leading-[1.15] mb-6">
            {L("Create mentors who think,", "ऐसे मेंटर्स बनाएं जो सोचें,", "असे गुरू तयार करा जे विचार करतील,")}{" "}
            <span className="font-light text-[#0f62fe]">
              {L("teach, and reason.", "सिखाएं और समझें।", "शिकवतील आणि समजून घेतील.")}
            </span>
          </h1>

          {/* Subhead */}
          <p className="text-lg sm:text-xl font-normal text-[#525252] leading-relaxed max-w-3xl mb-8 tracking-[0.16px]">
            {L(
              "UniGuru transforms domain knowledge into precise, authoritative AI mentors. Define any specialist — mathematicians, software architects, or ancient epistemologists — and master complex subjects with zero distraction.",
              "UniGuru विषय ज्ञान को सटीक, प्रामाणिक AI मेंटर्स में बदलता है। किसी भी विशेषज्ञ को परिभाषित करें — गणितज्ञ, सॉफ्टवेयर आर्किटेक्ट, या प्राचीन ज्ञानशास्त्री — और बिना किसी व्यवधान के जटिल विषयों में महारत हासिल करें।",
              "UniGuru ज्ञानक्षेत्राचे अचूक, अधिकृत AI गुरूंमध्ये रूपांतर करते. कोणत्याही तज्ञाची व्याख्या करा — गणितज्ञ, सॉफ्टवेअर आर्किटेक्ट, किंवा प्राचीन ज्ञानशास्त्रज्ञ — आणि जटिल विषयांवर प्रभुत्व मिळवा."
            )}
          </p>

          {/* Carbon Primary & Secondary Action CTAs */}
          <div className="flex flex-wrap items-center gap-4 pt-2">
            <button
              onClick={handleLetChatClick}
              className="cds-btn-primary"
              style={{ padding: "14px 28px", fontSize: "15px" }}
            >
              <span>{L("Start Learning Now", "सीखना शुरू करें", "शिकायला सुरुवात करा")}</span>
              <FontAwesomeIcon icon={faArrowRight} className="text-sm" />
            </button>

            <button
              onClick={() => navigate("/about")}
              className="cds-btn-secondary text-white"
              style={{ padding: "14px 24px", fontSize: "15px", color: "#ffffff" }}
            >
              <span style={{ color: "#ffffff" }}>{L("Explore System Architecture", "सिस्टम आर्किटेक्चर देखें", "सिस्टम आर्किटेक्चर पहा")}</span>
            </button>
          </div>
        </div>

        {/* Decorative Grid Specs watermark in background */}
        <div className="mt-12 pt-8 border-t border-[#e0e0e0] grid grid-cols-2 md:grid-cols-4 gap-6 text-xs text-[#525252]">
          <div>
            <div className="text-2xl font-light text-[#161616] mb-1">0–4px</div>
            <div>Deliberate flat geometry</div>
          </div>
          <div>
            <div className="text-2xl font-light text-[#0f62fe] mb-1">100%</div>
            <div>Curriculum ground truth</div>
          </div>
          <div>
            <div className="text-2xl font-light text-[#161616] mb-1">Plex Sans</div>
            <div>Precision typographic system</div>
          </div>
          <div>
            <div className="text-2xl font-light text-[#161616] mb-1">Enterprise</div>
            <div>Carbon Design compliance</div>
          </div>
        </div>
      </section>

      {/* 3. Feature Card Grid (Thin-bordered tiles with 0px radius, no drop shadow) */}
      <section className="px-6 sm:px-12 lg:px-16 py-20 max-w-[1584px] mx-auto border-b border-[#e0e0e0]">
        <div className="mb-12">
          <div className="text-sm font-normal text-[#525252] mb-2 tracking-[0.16px]">
            {L("Core Capabilities", "मुख्य क्षमताएं", "मुख्य क्षमता")}
          </div>
          <h2 className="text-3xl sm:text-4xl font-normal text-[#161616] tracking-tight">
            {L("Engineered for cognitive depth and rigorous comprehension", "संज्ञानात्मक गहराई और कठोर समझ के लिए निर्मित", "सखोल समज आणि ज्ञानासाठी तयार केलेले")}
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-0 border-t border-l border-[#e0e0e0]">
          {/* Tile 1 */}
          <div className="cds-tile p-8 border-r border-b border-[#e0e0e0] hover:bg-[#f4f4f4] transition-colors flex flex-col justify-between min-h-[280px]">
            <div>
              <div className="w-10 h-10 bg-[#f4f4f4] border border-[#e0e0e0] flex items-center justify-center mb-6">
                <FontAwesomeIcon icon={faBrain} className="text-[#0f62fe] text-lg" />
              </div>
              <h3 className="text-xl font-normal text-[#161616] mb-3">
                {L("Roleplay Mentorship", "रोलप्ले मेंटरशिप", "भूमिका मार्गदर्शन")}
              </h3>
              <p className="text-sm font-normal text-[#525252] leading-relaxed tracking-[0.16px]">
                {L(
                  "Configure mentors with customized pedagogies, tone, and rigor. Experience natural dialogue that tests your assumptions and checks comprehension.",
                  "अनुकूलित शिक्षण विधियों, लहजे और गंभीरता के साथ मेंटर्स को कॉन्फ़िगर करें। स्वाभाविक बातचीत का अनुभव करें जो आपकी समझ की परीक्षा लेती है।",
                  "सानुकूलित अध्यापन पद्धती, संवादशैली आणि सखोलतेसह गुरू कॉन्फिगर करा. तुमच्या समजुतीची चाचणी घेणारा नैसर्गिक संवाद अनुभवा."
                )}
              </p>
            </div>
            <div className="pt-6 text-xs text-[#0f62fe] font-medium flex items-center gap-2">
              <span>{L("Learn more", "और जानें", "अधिक जाणून घ्या")}</span>
              <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
            </div>
          </div>

          {/* Tile 2 */}
          <div className="cds-tile p-8 border-r border-b border-[#e0e0e0] hover:bg-[#f4f4f4] transition-colors flex flex-col justify-between min-h-[280px]">
            <div>
              <div className="w-10 h-10 bg-[#f4f4f4] border border-[#e0e0e0] flex items-center justify-center mb-6">
                <FontAwesomeIcon icon={faLayerGroup} className="text-[#0f62fe] text-lg" />
              </div>
              <h3 className="text-xl font-normal text-[#161616] mb-3">
                {L("Grounded Curriculum Truth", "प्रामाणिक पाठ्यक्रम सत्य", "अधिकृत अभ्यासक्रम सत्यता")}
              </h3>
              <p className="text-sm font-normal text-[#525252] leading-relaxed tracking-[0.16px]">
                {L(
                  "Responses draw from canonical knowledge graphs and textbook verified sources, preventing hallucination and ensuring academic fidelity.",
                  "प्रतिक्रियाएं प्रामाणिक ज्ञान ग्राफ़ और पाठ्यपुस्तक सत्यापित स्रोतों से ली जाती हैं, जिससे भ्रांतियों से बचा जाता है और अकादमिक निष्ठा सुनिश्चित होती है।",
                  "प्रतिसाद अधिकृत ज्ञान आलेख आणि पाठ्यपुस्तक पडताळणीतून येतात, ज्यामुळे अचूकता आणि शैक्षणिक विश्वासार्हता टिकून राहते."
                )}
              </p>
            </div>
            <div className="pt-6 text-xs text-[#0f62fe] font-medium flex items-center gap-2">
              <span>{L("Verified retrieval", "सत्यापित पुनर्प्राप्ति", "पडताळलेली माहिती")}</span>
              <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
            </div>
          </div>

          {/* Tile 3 */}
          <div className="cds-tile p-8 border-r border-b border-[#e0e0e0] hover:bg-[#f4f4f4] transition-colors flex flex-col justify-between min-h-[280px]">
            <div>
              <div className="w-10 h-10 bg-[#f4f4f4] border border-[#e0e0e0] flex items-center justify-center mb-6">
                <FontAwesomeIcon icon={faBookOpen} className="text-[#0f62fe] text-lg" />
              </div>
              <h3 className="text-xl font-normal text-[#161616] mb-3">
                {L("Sanskrit Knowledge Decoder", "संस्कृत ज्ञान डिकोडर", "संस्कृत ज्ञान डिकोडर")}
              </h3>
              <p className="text-sm font-normal text-[#525252] leading-relaxed tracking-[0.16px]">
                {L(
                  "Native Sanskrit epistemological decoder unravels traditional sutras, shlokas, and terminology into intuitive modern formulations.",
                  "मूल संस्कृत ज्ञानमीमांसा डिकोडर पारंपरिक सूत्रों, श्लोकों और शब्दावली को सहज आधुनिक व्याख्याओं में प्रस्तुत करता है।",
                  "मूळ संस्कृत ज्ञानमीमांसा डिकोडर पारंपारिक सूत्रे, श्लोक आणि संकल्पना आधुनिक स्वरूपात सहज समजावून देतो."
                )}
              </p>
            </div>
            <div className="pt-6 text-xs text-[#0f62fe] font-medium flex items-center gap-2">
              <span>{L("Explore decoder", "डिकोडर देखें", "डिकोडर पहा")}</span>
              <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
            </div>
          </div>
        </div>
      </section>

      {/* 4. Product Tab Strip & Showcase (Carbon Product Tabs) */}
      <section className="bg-[#f4f4f4] px-6 sm:px-12 lg:px-16 py-20 border-b border-[#e0e0e0]">
        <div className="max-w-[1584px] mx-auto">
          <div className="mb-8">
            <div className="text-sm font-normal text-[#525252] mb-2 tracking-[0.16px]">
              {L("Mentor Archetypes", "मेंटर प्रकार", "मार्गदर्शक प्रकार")}
            </div>
            <h2 className="text-3xl sm:text-4xl font-normal text-[#161616] tracking-tight">
              {L("Interactive disciplines ready to converse", "संवाद के लिए तैयार परस्पर संवादात्मक विषय", "संवादासाठी सज्ज असलेले विविध विषय")}
            </h2>
          </div>

          {/* Carbon Horizontal Tab Strip */}
          <div className="flex border-b border-[#e0e0e0] overflow-x-auto mb-8 bg-white">
            {mentorPresets.map((preset, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedTab(idx)}
                className={`cds-tab whitespace-nowrap ${selectedTab === idx ? "cds-tab-active" : ""}`}
              >
                {preset.category}
              </button>
            ))}
          </div>

          {/* Active Tab Showcase Tile */}
          <div className="cds-tile p-8 sm:p-12 border border-[#e0e0e0] bg-white">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
              <div className="lg:col-span-7">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-[#f4f4f4] border border-[#e0e0e0] text-xs text-[#525252] mb-4">
                  <FontAwesomeIcon icon={mentorPresets[selectedTab].icon} className="text-[#0f62fe]" />
                  <span>{mentorPresets[selectedTab].category}</span>
                </div>
                <h3 className="text-2xl sm:text-3xl font-light text-[#161616] mb-4">
                  {mentorPresets[selectedTab].title}
                </h3>
                <p className="text-base text-[#525252] leading-relaxed mb-6 tracking-[0.16px]">
                  {mentorPresets[selectedTab].tagline}
                </p>
                <div className="grid grid-cols-2 gap-3 mb-8">
                  {mentorPresets[selectedTab].topics.map((topic, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-[#161616]">
                      <FontAwesomeIcon icon={faCheck} className="text-[#24a148] text-xs" />
                      <span>{topic}</span>
                    </div>
                  ))}
                </div>
                <button
                  onClick={handleLetChatClick}
                  className="cds-btn-primary"
                >
                  <span>{L("Create this Mentor", "यह मेंटर बनाएं", "हा गुरू तयार करा")}</span>
                  <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
                </button>
              </div>

              <div className="lg:col-span-5 bg-[#f4f4f4] border border-[#e0e0e0] p-6">
                <div className="text-xs text-[#525252] uppercase tracking-wider mb-3">Sample Interaction</div>
                <div className="p-4 bg-white border border-[#e0e0e0] mb-3 text-xs leading-relaxed text-[#161616]">
                  <span className="font-semibold text-[#0f62fe]">Student:</span> "Can you derive the proof from first principles without skipping the convergence constraint?"
                </div>
                <div className="p-4 bg-white border border-[#e0e0e0] text-xs leading-relaxed text-[#525252]">
                  <span className="font-semibold text-[#161616]">Guru:</span> "Certainly. Let's observe the boundary condition where epsilon approaches zero. Notice how the series remains bounded..."
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. Enterprise Partner / Domain Marquee (Carbon Logo Tiles) */}
      <section className="px-6 sm:px-12 lg:px-16 py-16 max-w-[1584px] mx-auto border-b border-[#e0e0e0]">
        <div className="text-xs uppercase tracking-wider text-[#8c8c8c] mb-6 font-medium">
          {L("Academic and Technical Focus Disciplines", "शैक्षणिक और तकनीकी विशेषज्ञता के क्षेत्र", "शैक्षणिक आणि तांत्रिक विषयांचे क्षेत्र")}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-0 border-t border-l border-[#e0e0e0]">
          {["Mathematics", "Computer Science", "Vedic Epistemology", "Theoretical Physics", "Linguistics", "System Architecture"].map((disc, idx) => (
            <div
              key={idx}
              className="cds-tile p-6 border-r border-b border-[#e0e0e0] flex items-center justify-center text-center text-xs font-normal text-[#525252] hover:bg-[#f4f4f4] transition-colors"
            >
              {disc}
            </div>
          ))}
        </div>
      </section>

      {/* 6. CTA Banner (IBM Blue #0f62fe full bleed banner as specified in DESIGN.md) */}
      <section className="bg-[#0f62fe] text-white py-16 px-6 sm:px-12 lg:px-16">
        <div className="max-w-[1584px] mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          <div>
            <h2 className="text-3xl sm:text-4xl font-light tracking-tight mb-2">
              {L("Begin interacting with specialized mentors today.", "आज ही विशेष मेंटर्स के साथ सीखना शुरू करें।", "आजच विशेष गुरूंशी संवाद साधायला सुरुवात करा.")}
            </h2>
            <p className="text-white/80 text-base max-w-2xl font-light">
              {L("No complex setup required. Create custom mentors or launch from curated presets in seconds.", "किसी जटिल सेटअप की आवश्यकता नहीं। कस्टम मेंटर्स बनाएं या सेकंडों में प्रीसेट से शुरू करें।", "कोणत्याही गुंतागुंतीच्या सेटअपची गरज नाही. काही सेकंदात आपले गुरू तयार करा.")}
            </p>
          </div>
          <div className="flex-shrink-0">
            <button
              onClick={handleLetChatClick}
              className="bg-white text-[#0f62fe] hover:bg-[#f4f4f4] px-8 py-4 text-sm font-normal rounded-none inline-flex items-center gap-3 transition-colors shadow-none"
            >
              <span>{L("Launch Workspace", "वर्कस्पेस खोलें", "वर्कस्पेस सुरू करा")}</span>
              <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
            </button>
          </div>
        </div>
      </section>

      {/* 7. Carbon Charcoal Footer (Inverse Canvas #161616 with high-contrast text) */}
      <footer className="bg-[#161616] text-[#f4f4f4] px-6 sm:px-12 lg:px-16 pt-16 pb-12">
        <div className="max-w-[1584px] mx-auto grid grid-cols-1 md:grid-cols-4 gap-12 border-b border-[#393939] pb-12">
          {/* Brand Col */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <img src={uniLogo} alt="UniGuru" className="w-8 h-8 object-contain" />
              <span className="text-white text-lg font-light tracking-wider">UniGuru</span>
            </div>
            <p className="text-xs text-[#c6c6c6] leading-relaxed max-w-xs">
              Enterprise educational AI powered by grounded curriculum graphs and pedagogical personas.
            </p>
            <div className="pt-2">
              <a
                href="https://blackholeinfiverse.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block hover:opacity-80 transition-opacity"
              >
                <img src={BHI} alt="Blackhole Infiverse" className="h-8 object-contain" />
              </a>
            </div>
          </div>

          {/* Col 2 */}
          <div>
            <h4 className="text-xs uppercase tracking-wider text-white mb-4 font-semibold">Platform</h4>
            <ul className="space-y-2.5 text-xs text-[#f4f4f4]">
              <li><button onClick={handleLetChatClick} className="text-[#f4f4f4] hover:text-white transition-colors">Roleplay Mentors</button></li>
              <li><button onClick={handleLetChatClick} className="text-[#f4f4f4] hover:text-white transition-colors">Custom Personas</button></li>
              <li><button onClick={() => navigate("/about")} className="text-[#f4f4f4] hover:text-white transition-colors">Curriculum Retrieval</button></li>
              <li><button onClick={() => navigate("/about")} className="text-[#f4f4f4] hover:text-white transition-colors">Sanskrit Decoder</button></li>
            </ul>
          </div>

          {/* Col 3 */}
          <div>
            <h4 className="text-xs uppercase tracking-wider text-white mb-4 font-semibold">Design & Architecture</h4>
            <ul className="space-y-2.5 text-xs text-[#f4f4f4]">
              <li><span className="text-[#f4f4f4]">Carbon Design System</span></li>
              <li><span className="text-[#f4f4f4]">IBM Plex Sans Typography</span></li>
              <li><span className="text-[#f4f4f4]">Flat 0px Geometry</span></li>
              <li><span className="text-[#f4f4f4]">Single Accent Blue #0f62fe</span></li>
            </ul>
          </div>

          {/* Col 4 */}
          <div>
            <h4 className="text-xs uppercase tracking-wider text-white mb-4 font-semibold">Access</h4>
            <ul className="space-y-2.5 text-xs text-[#f4f4f4]">
              <li><button onClick={() => navigate("/login")} className="text-[#f4f4f4] hover:text-white transition-colors">Sign In</button></li>
              <li><button onClick={() => navigate("/signup")} className="text-[#f4f4f4] hover:text-white transition-colors">Create Account</button></li>
              <li><button onClick={() => navigate("/about")} className="text-[#f4f4f4] hover:text-white transition-colors">Documentation</button></li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="max-w-[1584px] mx-auto pt-8 flex flex-col sm:flex-row items-center justify-between text-xs text-[#c6c6c6] gap-4">
          <div>
            © {new Date().getFullYear()} UniGuru. All rights reserved. Faithfully adhering to DESIGN.md specification.
          </div>
          <div className="flex items-center gap-6">
            <span className="text-[#c6c6c6] hover:text-white cursor-pointer" onClick={() => navigate("/about")}>Privacy</span>
            <span className="text-[#c6c6c6] hover:text-white cursor-pointer" onClick={() => navigate("/about")}>Terms</span>
            <span className="text-[#c6c6c6] hover:text-white cursor-pointer" onClick={() => navigate("/about")}>Security</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default HomePage;

