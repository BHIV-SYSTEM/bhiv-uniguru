import React from 'react';

interface AuthCardProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
  className?: string;
}

const AuthCard: React.FC<AuthCardProps> = ({
  children,
  title,
  subtitle,
  className = ''
}) => {
  return (
    <div className={`w-full ${className}`}>
      {/* Carbon Tile Card */}
      <div className="w-full">
        {/* Header */}
        <div className="mb-6">
          <h3 className="text-xl sm:text-2xl font-normal text-[#161616] tracking-tight font-carbon">
            {title}
          </h3>
          {subtitle && (
            <p className="text-[#525252] text-xs sm:text-sm mt-1 font-carbon">
              {subtitle}
            </p>
          )}
        </div>

        {/* Content */}
        <div className="space-y-4">
          {children}
        </div>
      </div>
    </div>
  );
};

export default AuthCard;
