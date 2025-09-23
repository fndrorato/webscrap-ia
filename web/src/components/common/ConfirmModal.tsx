import React from 'react';
import { Modal } from '../ui/modal';

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  confirmButtonDisabled?: boolean;
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Sim',
  cancelText = 'Não',
  confirmButtonDisabled = false,
}) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} className="w-96 p-6 rounded-lg shadow-lg bg-white dark:bg-gray-900">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{title}</h3>
      <p className="text-sm text-gray-700 dark:text-gray-300 mb-6">
        {message}
      </p>
      <div className="flex justify-end gap-3">
        <button
          className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
          onClick={onClose}
        >
          {cancelText}
        </button>
        <button
          className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={onConfirm}
          disabled={confirmButtonDisabled}
        >
          {confirmText}
        </button>
      </div>
    </Modal>
  );
};

export default ConfirmModal;