
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHome, faArrowLeft, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import BubblyButton from "../components/BubblyButton";
import uniguru from "../assets/uni-logo.png";

const NotFoundPage = () => {
  const navigate = useNavigate();
  const { isLoggedIn } = useAuth();

  return (
    <div className="relative min-h-screen flex items-center justify-center">
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
            className="text-6xl sm:text-8xl text-yellow-500 mb-4" 
          />
        </div>

        {/* 404 Text */}
        <div className="mb-8">
          <h2 className="text-6xl sm:text-8xl font-bold text-white mb-4">
            404
          </h2>
          <h3 className="text-2xl sm:text-3xl font-semibold text-gray-300 mb-4">
            Page Not Found
          </h3>
          <p className="text-lg text-gray-400 mb-2">
            Oops! The page you're looking for doesn't exist.
          </p>
          <p className="text-base text-gray-500">
            It might have been moved, deleted, or you entered the wrong URL.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <BubblyButton
            onClick={() => navigate("/")}
            variant="primary"
            className="flex items-center space-x-2 px-6 py-3 text-base font-medium"
          >
            <FontAwesomeIcon icon={faHome} className="text-sm" />
            <span>Go Home</span>
          </BubblyButton>

          <BubblyButton
            onClick={() => navigate(-1)}
            variant="secondary"
            className="flex items-center space-x-2 px-6 py-3 text-base font-medium"
          >
            <FontAwesomeIcon icon={faArrowLeft} className="text-sm" />
            <span>Go Back</span>
          </BubblyButton>
        </div>

        {/* Additional Help */}
        <div className="mt-12 p-6 bg-gray-900/30 backdrop-blur-sm border border-gray-700 rounded-lg">
          <h4 className="text-lg font-semibold text-white mb-3">
            Need Help?
          </h4>
          <p className="text-gray-300 text-sm mb-4">
            If you believe this is an error, you can try these options:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div className="flex items-center space-x-2 text-gray-400">
              <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
              <span>Check the URL for typos</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-400">
              <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
              <span>Try refreshing the page</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-400">
              <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
              <span>Go back to the homepage</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-400">
              <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
              <span>Contact support if needed</span>
            </div>
          </div>
        </div>

        {/* Quick Navigation */}
        <div className="mt-8">
          <p className="text-gray-500 text-sm mb-4">Quick Navigation:</p>
          <div className="flex flex-wrap justify-center gap-3">
            <button
              onClick={() => navigate("/")}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors border border-gray-700 hover:border-gray-600 rounded-full"
            >
              Home
            </button>
            <button
              onClick={() => navigate(isLoggedIn ? "/chatpage" : "/login")}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors border border-gray-700 hover:border-gray-600 rounded-full"
            >
              Chat
            </button>
            <button
              onClick={() => navigate("/login")}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors border border-gray-700 hover:border-gray-600 rounded-full"
            >
              Login
            </button>
            <button
              onClick={() => navigate("/signup")}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors border border-gray-700 hover:border-gray-600 rounded-full"
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
