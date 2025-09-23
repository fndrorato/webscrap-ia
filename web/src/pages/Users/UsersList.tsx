import React, { useState, useEffect } from 'react';
import axios from '../../api/axios';
import Badge from '../../components/ui/badge/Badge';
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import { PencilIcon, TrashBinIcon } from '../../icons';
import { useTranslation } from 'react-i18next';
import UserFormModal from './UserFormModal';
import ConfirmModal from '../../components/common/ConfirmModal';
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from '../../components/ui/table';

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

const UsersList: React.FC = () => {
  const { t } = useTranslation();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<User | null>(null);
 
   const fetchUsers = async () => {
     setLoading(true);
     setError(null);
     try {
       const response = await axios.get('/api/v1/users/');
       setUsers(response.data);
     } catch (err) {
       setError('Failed to fetch users.');
       console.error('Error fetching users:', err);
     } finally {
       setLoading(false);
     }
   };
 
   useEffect(() => {
     fetchUsers();
   }, []);
 
   const handleOpenModal = (user: User | null = null) => {
     setEditingUser(user);
     setIsModalOpen(true);
   };
 
   const handleCloseModal = () => {
     setEditingUser(null);
     setIsModalOpen(false);
   };

 
   const handleUserCreated = () => {
    fetchUsers();
  };

  const handleDeleteClick = (user: User) => {
    setUserToDelete(user);
    setIsDeleteModalOpen(true);
  };

  const handleDeleteUser = async () => {
    if (userToDelete) {
      setIsDeleting(true);
      setDeleteError(null);
      try {
        await axios.delete(`/api/v1/users/${userToDelete.id}/`);
        fetchUsers();
        setIsDeleteModalOpen(false);
        setUserToDelete(null);
      } catch (error) {
        console.error('Error deleting user:', error);
        setDeleteError(t('failedToDeleteUser'));
      } finally {
        setIsDeleting(false);
      }
    }
  };

  if (loading) {
    return <div>{t('loadingUsers')}</div>;
  }

  if (error) {
    return <div>{t('error')}: {error}</div>;
  }

  return (
    <>
      
      <PageBreadcrumb pageTitle={t('usersList')} />
      <div className="p-2">
        {deleteError && (
          <div className="text-red-500 text-sm mb-4">{deleteError}</div>
        )}

        <button
          onClick={() => handleOpenModal(null)}
          className="inline-flex items-center justify-center gap-2 rounded-lg transition  px-4 py-3 text-sm bg-brand-500 text-white shadow-theme-xs hover:bg-brand-600 disabled:bg-brand-300 mb-4"
        >
          {t('newUser')}
        </button>
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03]">
          <div className="max-w-full overflow-x-auto">
            <Table>
              <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
                <TableRow>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('username')}</TableCell>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('email')}</TableCell>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('firstName')}</TableCell>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('lastName')}</TableCell>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('active')}</TableCell>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('group')}</TableCell>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('actions')}</TableCell>
                </TableRow>
              </TableHeader>
              <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">{user.username}</TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">{user.email}</TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">{user.first_name}</TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">{user.last_name}</TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                      <Badge size="sm" color={user.is_active ? 'success' : 'error'}>
                        {user.is_active ? t('active') : t('inactive')}
                      </Badge>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">{user.group_name}</TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleOpenModal(user)}
                          className="text-blue-500 hover:text-blue-700"
                        >
                          <PencilIcon className="w-5 h-5" />
                        </button>
                        <button
                          className="text-red-500 hover:text-red-700"
                          onClick={() => handleDeleteClick(user)}
                        >
                          <TrashBinIcon className="w-5 h-5" />
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </div>

      <UserFormModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onUserCreated={handleUserCreated}
        editingUser={editingUser}
      />

      <ConfirmModal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleDeleteUser}
        title={t('confirmExclusion')}
        message={t('confirmDeleteUser', { username: userToDelete?.username })}
        confirmText={isDeleting ? t('deleting') : t('yes')}
        confirmButtonDisabled={isDeleting}
      />
    </>

  );
};

export default UsersList;