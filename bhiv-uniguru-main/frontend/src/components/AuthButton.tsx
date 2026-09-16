import React from 'react';
import LoadingSpinner from './LoadingSpinner';

interface AuthButtonProps {
  type?: 'button' | 'submit' | 'reset';
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: 'primary' | 'social';
  className?: string;
}

const AuthButton: React.FC<AuthButtonProps> = ({
  type = 'button',
  children,
  onClick,
  disabled = false,
  loading = false,
  variant = 'primary',
  className = ''
}) => {
  const baseClasses = `
    font-poppins tracking-[0.5px]
    outline-none border-none
    cursor-pointer
    transition-all duration-200
    disabled:opacity-50 disabled:cursor-not-allowed
  `;

  const variantClasses = {
    primary: `
      mt-3 sm:mt-6 w-full
      bg-white text-button
      py-[10px] sm:py-[15px] px-4
      text-[14px] sm:text-[18px] font-semibold
      rounded-[5px]
      flex items-center justify-center
      hover:bg-gray-100
      touch-target
    `,
    social: `
      bg-glass-social text-text-social
      w-[150px] rounded-[3px]
      py-[5px] px-[10px] pb-[10px] pl-[5px]
      text-center
      hover:bg-glass-socialHover
      touch-target
    `
  };

  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      className={`
        ${baseClasses}
        ${variantClasses[variant]}
        ${className}
      `}
    >
      {loading && (
        <div className="mr-2">
          <LoadingSpinner size="small" variant="default" />
        </div>
      )}
      {children}
    </button>
  );
};

export default AuthButton;
