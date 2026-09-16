import React from 'react';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large' | 'xl';
  variant?: 'default' | 'dots' | 'pulse' | 'orbit' | 'gradient-ring';
  text?: string;
  fullScreen?: boolean;
  className?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  variant = 'default',
  text,
  fullScreen = false,
  className = ''
}) => {
  const getSizeClasses = () => {
    switch (size) {
      case 'small':
        return 'w-4 h-4';
      case 'medium':
        return 'w-8 h-8';
      case 'large':
        return 'w-12 h-12';
      case 'xl':
        return 'w-16 h-16';
      default:
        return 'w-8 h-8';
    }
  };

  const getTextSize = () => {
    switch (size) {
      case 'small':
        return 'text-xs';
      case 'medium':
        return 'text-sm';
      case 'large':
        return 'text-base';
      case 'xl':
        return 'text-lg';
      default:
        return 'text-sm';
    }
  };

  const renderSpinner = () => {
    const sizeClasses = getSizeClasses();
    
    switch (variant) {
      case 'dots':
        return (
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-gradient-to-r from-purple-400 to-blue-400 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-gradient-to-r from-blue-400 to-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-2 h-2 bg-gradient-to-r from-cyan-400 to-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
        );

      case 'pulse':
        return (
          <div className={`${sizeClasses} bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400 rounded-full animate-pulse`}></div>
        );

      case 'orbit':
        return (
          <div className={`${sizeClasses} relative`}>
            <div className="absolute inset-0 rounded-full border-2 border-transparent bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400 animate-spin">
              <div className="absolute inset-1 rounded-full bg-black"></div>
            </div>
            <div className="absolute top-0 left-1/2 w-1 h-1 bg-white rounded-full transform -translate-x-1/2 animate-ping"></div>
          </div>
        );

      case 'gradient-ring':
        return (
          <div className={`${sizeClasses} relative`}>
            <div className="absolute inset-0 rounded-full bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400 animate-spin">
              <div className="absolute inset-1 rounded-full bg-black"></div>
            </div>
            <div className="absolute inset-2 rounded-full bg-gradient-to-r from-purple-300 via-blue-300 to-cyan-300 animate-pulse"></div>
          </div>
        );

      default:
        return (
          <div className={`${sizeClasses} border-2 border-transparent bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400 rounded-full animate-spin`}>
            <div className="absolute inset-1 rounded-full bg-black"></div>
          </div>
        );
    }
  };

  const content = (
    <div className={`flex flex-col items-center justify-center space-y-3 ${className}`}>
      <div className="relative">
        {renderSpinner()}
      </div>
      {text && (
        <p className={`${getTextSize()} text-gray-300 font-medium animate-pulse`}>
          {text}
        </p>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
        <div className="bg-glass-card backdrop-blur-xl rounded-xl p-8 border border-glass-border shadow-glass">
          {content}
        </div>
      </div>
    );
  }

  return content;
};

export default LoadingSpinner;
