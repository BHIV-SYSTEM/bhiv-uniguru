import React, { useState, useEffect, useRef } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faEdit, faTimes } from '@fortawesome/free-solid-svg-icons';

interface RenameModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (newName: string) => void;
  title: string;
  currentName: string;
  placeholder?: string;
  confirmText?: string;
  cancelText?: string;
}

const RenameModal: React.FC<RenameModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  currentName,
  placeholder = "Enter new name...",
  confirmText = 'Rename',
  cancelText = 'Cancel'
}) => {
  const [newName, setNewName] = useState(currentName);
  const inputRef = useRef<HTMLInputElement>(null);

  // Reset the input when modal opens/closes or currentName changes
  useEffect(() => {
    if (isOpen) {
      setNewName(currentName);
      // Focus the input after a short delay to ensure modal is rendered
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
          inputRef.current.select();
        }
      }, 100);
    }
  }, [isOpen, currentName]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = newName.trim();
    if (trimmedName && trimmedName !== currentName) {
      onConfirm(trimmedName);
    }
    onClose();
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  const isValid = newName.trim().length > 0;
  const hasChanged = newName.trim() !== currentName;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      onClick={handleBackdropClick}
      onKeyDown={handleKeyDown}
    >
      <div 
        className="relative w-full max-w-md mx-auto bg-gray-900 rounded-2xl border border-purple-500/20 shadow-2xl transform transition-all duration-300 scale-100"
        style={{
          background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.95), rgba(31, 41, 55, 0.95))',
        }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white transition-colors rounded-full hover:bg-gray-700/50"
        >
          <FontAwesomeIcon icon={faTimes} size="sm" />
        </button>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6">
          {/* Icon */}
          <div className="flex items-center justify-center w-16 h-16 mx-auto mb-4 rounded-full bg-gray-800/50">
            <FontAwesomeIcon 
              icon={faEdit} 
              className="text-2xl text-purple-400"
            />
          </div>

          {/* Title */}
          <h3 className="text-xl font-semibold text-white text-center mb-2">
            {title}
          </h3>

          {/* Input Field */}
          <div className="mb-6">
            <input
              ref={inputRef}
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={placeholder}
              className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all duration-200"
              maxLength={100}
            />
            <div className="flex justify-between items-center mt-2">
              <span className="text-xs text-gray-400">
                {newName.length}/100 characters
              </span>
              {!isValid && (
                <span className="text-xs text-red-400">
                  Name cannot be empty
                </span>
              )}
            </div>
          </div>

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 text-gray-300 bg-gray-700/50 hover:bg-gray-600/50 rounded-xl transition-all duration-200 font-medium border border-gray-600/50 hover:border-gray-500/50"
            >
              {cancelText}
            </button>
            <button
              type="submit"
              disabled={!isValid || !hasChanged}
              className="flex-1 px-4 py-3 text-white bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-xl transition-all duration-200 font-medium focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900"
            >
              {confirmText}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RenameModal;
