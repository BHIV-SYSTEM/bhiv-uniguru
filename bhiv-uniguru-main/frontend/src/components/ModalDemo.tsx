import React, { useState } from 'react';
import ConfirmationModal from './ConfirmationModal';
import { faTrash, faExclamationTriangle, faInfoCircle } from '@fortawesome/free-solid-svg-icons';

const ModalDemo: React.FC = () => {
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    type: 'danger' | 'warning' | 'info';
    title: string;
    message: string;
    icon: any;
  }>({
    isOpen: false,
    type: 'danger',
    title: '',
    message: '',
    icon: faTrash
  });

  const showDeleteModal = () => {
    setModalState({
      isOpen: true,
      type: 'danger',
      title: 'Delete Chat',
      message: 'Are you sure you want to delete "My Chat Session"? This action cannot be undone.',
      icon: faTrash
    });
  };

  const showWarningModal = () => {
    setModalState({
      isOpen: true,
      type: 'warning',
      title: 'Warning',
      message: 'This action may have unintended consequences. Are you sure you want to proceed?',
      icon: faExclamationTriangle
    });
  };

  const showInfoModal = () => {
    setModalState({
      isOpen: true,
      type: 'info',
      title: 'Information',
      message: 'This is an informational modal. Would you like to continue?',
      icon: faInfoCircle
    });
  };

  const handleConfirm = () => {
    console.log('Action confirmed!');
    alert('Action confirmed!');
  };

  const closeModal = () => {
    setModalState({ ...modalState, isOpen: false });
  };

  return (
    <div className="p-8 space-y-4">
      <h2 className="text-2xl font-bold text-white mb-6">Confirmation Modal Demo</h2>
      
      <div className="space-y-4">
        <button
          onClick={showDeleteModal}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
        >
          Show Delete Modal
        </button>
        
        <button
          onClick={showWarningModal}
          className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors"
        >
          Show Warning Modal
        </button>
        
        <button
          onClick={showInfoModal}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          Show Info Modal
        </button>
      </div>

      <ConfirmationModal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        onConfirm={handleConfirm}
        title={modalState.title}
        message={modalState.message}
        type={modalState.type}
        icon={modalState.icon}
      />
    </div>
  );
};

export default ModalDemo;
