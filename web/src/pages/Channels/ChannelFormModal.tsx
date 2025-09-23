import { Modal } from '../../components/ui/modal';
import Input from '../../components/form/input/InputField';
import Label from '../../components/form/Label';
import Button from '../../components/ui/button/Button';
import React, { useState, useEffect } from 'react';
import axios from '../../api/axios';
import { useTranslation } from 'react-i18next';

interface ChannelFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onChannelCreated: () => void;
  editingChannel: Channel | null;
}

interface Channel {
  id: number;
  name: string;
  description: string;
  picture: string;
  pictureFile?: File | null;
  verified: boolean;
  role: string;
  subscribers_count: number;
}

const ChannelFormModal: React.FC<ChannelFormModalProps> = ({ isOpen, onClose, onChannelCreated, editingChannel }) => {
  const { t } = useTranslation();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [picture, setPicture] = useState('');
  const [pictureFile, setPictureFile] = useState<File | null>(null);
  const [picturePreview, setPicturePreview] = useState<string | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      if (editingChannel) {
        setName(editingChannel.name);
        setDescription(editingChannel.description);
        setPicture(editingChannel.picture);
        setPictureFile(null);
        setPicturePreview(editingChannel.picture);

      } else {
        setName('');
        setDescription('');
        setPicture('');
        setPictureFile(null);
        setPicturePreview(null);

      }
    }
  }, [isOpen, editingChannel]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    if (pictureFile) {
      formData.append('picture', pictureFile);
    } else if (picture) {
      formData.append('picture_url', picture); // Send URL if no new file
    }

    try {
      if (editingChannel) {
        await axios.put(`/api/v1/channels/${editingChannel.id}/`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      } else {
        await axios.post('/api/v1/channels/default/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      }
      onChannelCreated();
      onClose();
    } catch (err) {
      setError(t('channel_form_modal.failed_to_perform_action', { action: editingChannel ? t('channel_form_modal.update') : t('channel_form_modal.create') }));
      console.error(t('channel_form_modal.error_performing_action', { action: editingChannel ? t('channel_form_modal.updating') : t('channel_form_modal.creating') }), err);
    } finally {
      setLoading(false);
    }
  };

  return (
    
    <Modal isOpen={isOpen} onClose={onClose} isFullscreen={false} className="relative w-full rounded-3xl bg-white  dark:bg-gray-900  max-w-[584px] p-5 lg:p-10">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <p className="text-red-500 text-sm">{error}</p>}

        <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
          {editingChannel ? t('channel_form_modal.edit_channel') : t('channel_form_modal.create_new_channel')}
        </h2>

        <div>
          <Label htmlFor="name">{t('channel_form_modal.channel_name')}</Label>
          <Input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="description">{t('channel_form_modal.description')}</Label>
          <Input
            id="description"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div>
          <Label htmlFor="picture">{t('channel_form_modal.picture')}</Label>
          <input
            id="picture"
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                setPictureFile(file);
                setPicturePreview(URL.createObjectURL(file));
              } else {
                setPictureFile(null);
                setPicturePreview(null);
              }
            }}
            className="block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 dark:text-gray-400 focus:outline-none dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400"
          />
          {picturePreview && (
            <div className="mt-2">
              <img src={picturePreview} alt={t('channel_form_modal.picture_preview')} className="w-24 h-24 object-cover rounded-md" />
            </div>
          )}
        </div>

        <Button type="submit" disabled={loading}>
          {loading ? (editingChannel ? t('channel_form_modal.updating') : t('channel_form_modal.creating')) : (editingChannel ? t('channel_form_modal.update_channel') : t('channel_form_modal.create_channel'))}
        </Button>
      </form>
    </Modal>
  );
};

export default ChannelFormModal;