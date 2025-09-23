// Remove duplicate React import since it's already imported below
import { Modal } from '../../components/ui/modal';
import Input from '../../components/form/input/InputField';
import Label from '../../components/form/Label';
import Select from '../../components/form/Select';
import Button from '../../components/ui/button/Button';
import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import axios from '../../api/axios';

interface UserFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUserCreated: () => void;
  editingUser: User | null;
}

interface User {
  id: number;
  username: string;
  email: string;
  group_id_read: number;
  first_name: string;
  last_name: string;
  is_active: boolean;
  group_name: string;
}

interface Group {
  id: number;
  name: string;
}

const UserFormModal: React.FC<UserFormModalProps> = ({ isOpen, onClose, onUserCreated, editingUser }) => {
  const { t } = useTranslation();

  const [email, setEmail] = useState('');
  const [groupId, setGroupId] = useState<number | string>('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchGroups();
      if (editingUser) {
        setEmail(editingUser.email);
        setGroupId(editingUser.group_id_read.toString());
        setFirstName(editingUser.first_name);
        setLastName(editingUser.last_name);
        setIsActive(editingUser.is_active);
      } else {
        setEmail('');
        setGroupId('');
        setFirstName('');
        setLastName('');
        setIsActive(true);
      }
    }
  }, [isOpen, editingUser]);

  const fetchGroups = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/v1/groups/');
      setGroups(response.data);
    } catch (err) {
      setError(t('failedToFetchGroups'));
      console.error('Error fetching groups:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const userData = {
      username: email,
      email,
      password: 'watz123', // Consider handling password more securely
      group_id: Number(groupId),
      first_name: firstName,
      last_name: lastName,
      is_active: isActive,
    };

    try {
      if (editingUser) {
        await axios.put(`/api/v1/users/${editingUser.id}/`, userData);
      } else {
        await axios.post('/api/v1/users/', userData);
      }
      onUserCreated();
      onClose();
    } catch (err) {
      setError(t(editingUser ? 'failedToUpdateUser' : 'failedToCreateUser'));
      console.error(`Error ${editingUser ? 'updating' : 'creating'} user:`, err);
    } finally {
      setLoading(false);
    }
  };

  const groupOptions = groups.map(group => ({ value: group.id.toString(), label: group.name }));

  return (
    
    <Modal isOpen={isOpen} onClose={onClose} isFullscreen={false} className="relative w-full rounded-3xl bg-white  dark:bg-gray-900  max-w-[584px] p-5 lg:p-10">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <p className="text-red-500 text-sm">{t('error')}: {error}</p>}

        <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
          {t(editingUser ? 'editUser' : 'createNewUser')}
        </h2>

        <div>
          <Label htmlFor="email">{t('email')}</Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="group">{t('group')}</Label>
          <Select
            options={groupOptions}
            value={groupId.toString()}
            onChange={(value: string) => setGroupId(value)}
            placeholder={t('selectAGroup')}
          />
        </div>
        <div>
          <Label htmlFor="firstName">{t('firstName')}</Label>
          <Input
            id="firstName"
            type="text"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="lastName">{t('lastName')}</Label>
          <Input
            id="lastName"
            type="text"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
          />
        </div>
        <div className="flex items-center">
          <input
            type="checkbox"
            id="isActive"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="mr-2"
          />
          <Label htmlFor="isActive">{t('isActive')}</Label>
        </div>
        <Button type="submit" disabled={loading}>
          {loading ? t(editingUser ? 'updating' : 'creating') : t(editingUser ? 'updateUser' : 'createUser')}
        </Button>
      </form>
    </Modal>
  );
};

export default UserFormModal;