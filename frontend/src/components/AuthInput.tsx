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
    <div className={`mb-4 ${className}`}>
      {/* Label */}
      {label && (
        <label className="block text-xs font-medium text-[#525252] mb-1.5 font-carbon tracking-[0.16px]">
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
            block h-12 w-full
            bg-[#f4f4f4]
            rounded-none
            px-4 py-2.5
            text-sm font-normal
            text-[#161616] placeholder:text-[#8c8c8c]
            font-carbon tracking-[0.16px]
            border-b ${error ? "border-b-2 border-[#da1e28]" : "border-[#8c8c8c] focus:border-b-2 focus:border-[#0f62fe]"}
            outline-none
            transition-all duration-150
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        />
      </div>

      {/* Error Message */}
      {error && (
        <p className="text-[#da1e28] text-xs font-normal mt-1 font-carbon">
          {error}
        </p>
      )}
    </div>
  );
};

export default AuthInput;
