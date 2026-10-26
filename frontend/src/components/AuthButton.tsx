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
  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      className={`
        w-full min-h-[48px] px-4 py-3
        ${variant === 'primary' ? 'cds-btn-primary justify-center' : 'cds-btn-secondary justify-center'}
        font-carbon text-sm font-normal tracking-[0.16px]
        rounded-none cursor-pointer
        disabled:opacity-50 disabled:cursor-not-allowed
        transition-colors duration-150
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
