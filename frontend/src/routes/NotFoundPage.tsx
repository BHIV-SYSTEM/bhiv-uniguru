
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHome, faArrowLeft, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
// BubblyButton removed
import uniguru from "../assets/uni-logo.png";

const NotFoundPage = () => {
  const navigate = useNavigate();
  const { isLoggedIn } = useAuth();

  return (
    <div className="relative min-h-screen bg-white text-[#161616] font-carbon flex items-center justify-center">
      {/* Content */}
      <div className="relative z-10 text-center px-4 max-w-2xl mx-auto">
        {/* Logo */}
        <div className="flex items-center justify-center mb-8">
          <img
            src={uniguru}
            alt="UniGuru Logo"
            className="w-16 h-16 sm:w-20 sm:h-20 object-contain mr-4"
          />
          <h1 className="text-3xl sm:text-4xl font-bold bg-clip-text text-transparent"
              style={{
                background: "linear-gradient(135deg, #b18615, #d4a01c, #f7c52d, #d4a01c, #b18615)",
                backgroundClip: "text",
                WebkitBackgroundClip: "text"
              }}>
            UniGuru
          </h1>
        </div>

        {/* 404 Icon */}
        <div className="mb-8">
          <FontAwesomeIcon 
            icon={faExclamationTriangle} 
            className="text-6xl sm:text-8xl text-[#0f62fe] mb-4" 
          />
        </div>

        {/* 404 Text */}
        <div className="mb-8">
          <h2 className="text-6xl sm:text-8xl font-light text-[#161616] mb-4 tracking-tight">
            404
          </h2>
          <h3 className="text-xl sm:text-2xl font-semibold text-[#161616] mb-4">
            Page Not Found
          </h3>
          <p className="text-lg text-[#525252] mb-2">
            Oops! The page you're looking for doesn't exist.
          </p>
          <p className="text-base text-[#8d8d8d]">
            It might have been moved, deleted, or you entered the wrong URL.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
          <button
            onClick={() => navigate(isLoggedIn ? "/chatpage" : "/")}
            className="cds-btn-primary text-xs"
            style={{ minHeight: "44px", padding: "10px 20px" }}
          >
            <FontAwesomeIcon icon={faHome} className="mr-2" />
            <span>{isLoggedIn ? "Go to Workspace" : "Go Home"}</span>
          </button>

          <button
            onClick={() => navigate(-1)}
            className="cds-btn-secondary text-xs"
            style={{ minHeight: "44px", padding: "10px 20px" }}
          >
            <FontAwesomeIcon icon={faArrowLeft} className="mr-2" />
            <span>Go Back</span>
          </button>
        </div>

        {/* Additional Help */}
        <div className="mt-10 p-6 cds-tile bg-[#f4f4f4] border border-[#e0e0e0] text-left rounded-none">
          <h4 className="text-sm font-semibold text-[#161616] mb-2 tracking-[0.16px]">
            Resolution Guidelines
          </h4>
          <p className="text-[#525252] text-xs mb-4 tracking-[0.16px]">
            If this endpoint was referenced from curriculum, verify the following:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-[#525252]">
            <div className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 bg-[#0f62fe] rounded-none"></span>
              <span>Check URL path spelling</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 bg-[#0f62fe] rounded-none"></span>
              <span>Refresh active session state</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 bg-[#0f62fe] rounded-none"></span>
              <span>Navigate back to home registry</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-1.5 h-1.5 bg-[#0f62fe] rounded-none"></span>
              <span>Contact system administrator</span>
            </div>
          </div>
        </div>

        {/* Quick Navigation */}
        <div className="mt-8 text-center">
          <p className="text-[#525252] text-xs mb-3 tracking-[0.16px]">Quick Navigation</p>
          <div className="flex flex-wrap justify-center gap-2">
            <button
              onClick={() => navigate("/")}
              className="px-3 py-1.5 text-xs text-[#161616] hover:bg-[#e0e0e0] transition-colors border border-[#e0e0e0] rounded-none bg-white"
            >
              Overview
            </button>
            <button
              onClick={() => navigate(isLoggedIn ? "/chatpage" : "/login")}
              className="px-3 py-1.5 text-xs text-[#161616] hover:bg-[#e0e0e0] transition-colors border border-[#e0e0e0] rounded-none bg-white"
            >
              Workspace
            </button>
            <button
              onClick={() => navigate("/login")}
              className="px-3 py-1.5 text-xs text-[#161616] hover:bg-[#e0e0e0] transition-colors border border-[#e0e0e0] rounded-none bg-white"
            >
              Login
            </button>
            <button
              onClick={() => navigate("/signup")}
              className="px-3 py-1.5 text-xs text-[#161616] hover:bg-[#e0e0e0] transition-colors border border-[#e0e0e0] rounded-none bg-white"
            >
              Sign Up
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
