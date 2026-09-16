import React from 'react';

interface AuthInputProps {
  type: 'text' | 'email' | 'password';
  name: string;
  placeholder: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  required?: boolean;
  error?: string;
  disabled?: boolean;
  autoComplete?: string;
  className?: string;
  label?: string;
}

const AuthInput: React.FC<AuthInputProps> = ({
  type,
  name,
  placeholder,
  value,
  onChange,
  required = false,
  error,
  disabled = false,
  autoComplete,
  className = '',
  label
}) => {


  return (
    <div className={`${className}`}>
      {/* Label (matching CodePen style) */}
      {label && (
        <label className="
          block mt-[16px] sm:mt-[30px] text-[13px] sm:text-[16px] font-medium
          text-glass font-poppins tracking-[0.5px]
        ">
          {label}
        </label>
      )}

      <div className="relative">
        <input
          type={type}
          name={name}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
          required={required}
          disabled={disabled}
          autoComplete={autoComplete}
          className={`
            block h-[42px] sm:h-[50px] w-full mt-1 sm:mt-2
            bg-glass-input
            rounded-[3px]
            px-[8px] sm:px-[10px] py-0
            text-[13px] sm:text-[14px] font-light
            text-glass placeholder:text-placeholder
            font-poppins tracking-[0.5px]
            outline-none border-none
            transition-all duration-200
            disabled:opacity-50 disabled:cursor-not-allowed
            touch-target
          `}
        />


      </div>

      {/* Error Message */}
      {error && (
        <p className="text-red-400 text-xs sm:text-sm font-medium mt-2 font-poppins animate-mobile-slide-up">
          {error}
        </p>
      )}
    </div>
  );
};

export default AuthInput;
