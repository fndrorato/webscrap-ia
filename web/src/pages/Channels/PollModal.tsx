import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Modal } from '../../components/ui/modal';

interface PollModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSendPoll: (question: string, options: string[]) => void;
}

const PollModal: React.FC<PollModalProps> = ({
  isOpen,
  onClose,
  onSendPoll,
}) => {
  const { t } = useTranslation();

  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState<string[]>(['', '']); // Start with two empty options

  const handleAddOption = () => {
    if (options.length < 10) {
      setOptions([...options, '']);
    }
  };

  const handleOptionChange = (index: number, value: string) => {
    const newOptions = [...options];
    newOptions[index] = value;
    setOptions(newOptions);
  };

  const handleRemoveOption = (index: number) => {
    const newOptions = options.filter((_, i) => i !== index);
    setOptions(newOptions);
  };

  const handleSend = () => {
    const filteredOptions = options.filter(option => option.trim() !== '');
    const uniqueOptions = new Set(filteredOptions);

    if (question.trim() === '') {
      alert(t('poll_modal.question_empty_error'));
      return;
    }

    if (filteredOptions.length < 2) {
      alert(t('poll_modal.min_options_error'));
      return;
    }

    if (uniqueOptions.size !== filteredOptions.length) {
      alert(t('poll_modal.duplicate_options_error'));
      return;
    }

    onSendPoll(question, filteredOptions);
    setQuestion('');
    setOptions(['', '']);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} className="w-11/12 md:w-1/2 lg:w-1/3 p-4 rounded-lg shadow-lg bg-white dark:bg-gray-900">
      <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">{t('poll_modal.create_poll')}</h2>
      <div className="mb-4">
        <label htmlFor="poll-question" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{t('poll_modal.poll_question')}</label>
        <input
          id="poll-question"
          type="text"
          placeholder={t('poll_modal.type_poll_question_placeholder')}
          className="w-full p-2 border border-gray-300 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{t('poll_modal.vote_options')}</label>
        {options.map((option, index) => (
          <div key={index} className="flex items-center mb-2">
            <input
              type="text"
              placeholder={t('poll_modal.option_placeholder', { index: index + 1 })}
              className="w-full p-2 border border-gray-300 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 mr-2"
              value={option}
              onChange={(e) => handleOptionChange(index, e.target.value)}
            />
            {options.length > 2 && (
              <button
                type="button"
                onClick={() => handleRemoveOption(index)}
                className="px-3 py-2 bg-red-500 text-white rounded-md hover:bg-red-600"
              >
                {t('poll_modal.remove')}
              </button>
            )}
          </div>
        ))}
        {options.length < 10 && (
          <button
            type="button"
            onClick={handleAddOption}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 mt-2"
          >
            {t('poll_modal.add_option')}
          </button>
        )}
      </div>
      <div className="flex justify-end space-x-2">
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
        >
          {t('poll_modal.cancel')}
        </button>
        <button
          type="button"
          onClick={handleSend}
          className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600"
        >
          {t('poll_modal.create_poll')}
        </button>
      </div>
    </Modal>
  );
};

export default PollModal;