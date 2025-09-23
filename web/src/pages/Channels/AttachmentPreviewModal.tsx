import React, { useState, useEffect } from 'react';
import { Modal } from '../../components/ui/modal';
import { useTranslation } from 'react-i18next';

interface AttachmentPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  files: File[];
  onSend: (messageText: string, attachments: File[]) => void;
  loading: boolean;
}

const AttachmentPreviewModal: React.FC<AttachmentPreviewModalProps> = ({
  isOpen,
  onClose,
  files,
  onSend,
  loading,
}) => {
  const { t } = useTranslation();
  const [messageText, setMessageText] = useState('');
  const [currentFileIndex, setCurrentFileIndex] = useState(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (files.length > 0) {
      const currentFile = files[currentFileIndex];
      const url = URL.createObjectURL(currentFile);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setPreviewUrl(null);
    }
  }, [files, currentFileIndex]);

  if (!isOpen || files.length === 0) {
    return null;
  }

  const currentFile = files[currentFileIndex];

  const handleSend = () => {
    onSend(messageText, files);
    onClose(); // Close the modal immediately after sending
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="w-11/12 md:w-1/2 lg:w-1/3 p-4 rounded-lg shadow-lg bg-white dark:bg-gray-900">
      <div className="flex flex-col">
        <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">{t('attachment_preview_modal.title')}</h2>
        <div className="mb-4">
          <div className="relative flex items-center justify-center">
            {files.length > 1 && (
              <button
                onClick={() => setCurrentFileIndex(prev => (prev === 0 ? files.length - 1 : prev - 1))}
                className="absolute left-0 top-1/2 -translate-y-1/2 bg-gray-800 bg-opacity-50 text-white p-2 rounded-full z-10"
              >
                &#10094;
              </button>
            )}
            {currentFile.type.startsWith('image/') && (
              <img src={previewUrl || ''} alt="Preview" className="max-w-full h-auto rounded-md mx-auto" />
            )}
            {currentFile.type.startsWith('video/') && (
              <video src={previewUrl || ''} controls className="max-w-full max-h-64 rounded-md mx-auto"></video>
            )}
            {!currentFile.type.startsWith('image/') && !currentFile.type.startsWith('video/') && (
              <p className="text-gray-700 dark:text-gray-300">{t('attachment_preview_modal.unsupported_type')}</p>
            )}
            {files.length > 1 && (
              <button
                onClick={() => setCurrentFileIndex(prev => (prev === files.length - 1 ? 0 : prev + 1))}
                className="absolute right-0 top-1/2 -translate-y-1/2 bg-gray-800 bg-opacity-50 text-white p-2 rounded-full z-10"
              >
                &#10095;
              </button>
            )}
          </div>
          {files.length > 1 && (
            <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-2">
              {currentFileIndex + 1} / {files.length}
            </p>
          )}
        </div>
        <input
          type="text"
          placeholder={t('attachment_preview_modal.add_a_message')}
          className="w-full p-2 border border-gray-300 rounded-md mb-4 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500"
          value={messageText}
          onChange={(e) => setMessageText(e.target.value)}
        />
        <div className="flex justify-end space-x-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
          >
            {t('attachment_preview_modal.cancel')}
          </button>
          <button
            type="button"
            onClick={handleSend}
            disabled={loading}
            className={`px-4 py-2 rounded-md ${loading ? 'bg-blue-300 cursor-not-allowed' : 'bg-blue-500 text-white hover:bg-blue-600'}`}
          >
            {loading ? t('attachment_preview_modal.sending') : t('attachment_preview_modal.send')}
          </button>
        </div>
      </div>
    </Modal>
  );
};

export default AttachmentPreviewModal;