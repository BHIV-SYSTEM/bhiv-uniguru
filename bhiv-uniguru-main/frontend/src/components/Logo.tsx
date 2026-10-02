import React from "react";
import { useNavigate } from "react-router-dom";
import uniguru from "../assets/uni-logo.png";

interface LogoProps {
  className?: string;
  size?: "small" | "medium" | "large";
  showText?: boolean;
}

const Logo: React.FC<LogoProps> = ({ 
  className = "", 
  size = "medium", 
  showText = true 
}) => {
  const navigate = useNavigate();

  const sizeClasses = {
    small: "w-8 h-8",
    medium: "w-10 h-10 sm:w-12 sm:h-12",
    large: "w-16 h-16"
  };

  const textSizeClasses = {
    small: "text-lg",
    medium: "text-xl sm:text-2xl",
    large: "text-3xl"
  };

  return (
    <div
      className={`flex items-center space-x-3 cursor-pointer group ${className}`}
      onClick={() => navigate("/")}
    >
      <img
        src={uniguru}
        alt="UniGuru Logo"
        className={`${sizeClasses[size]} object-contain group-hover:scale-105 transition-transform duration-200`}
      />
      {showText && (
        <h1 
          className={`${textSizeClasses[size]} font-bold bg-clip-text text-transparent`}
          style={{
            background: "linear-gradient(135deg, #b18615, #d4a01c, #f7c52d, #d4a01c, #b18615)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text"
          }}
        >
          UniGuru
        </h1>
      )}
    </div>
  );
};

export default Logo;
