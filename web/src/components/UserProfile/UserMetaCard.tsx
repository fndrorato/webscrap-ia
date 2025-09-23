import { useState } from 'react';
import { Modal } from "../ui/modal"; // Corrected Modal import
import Button from "../ui/button/Button";
import Input from "../form/input/InputField";
import Label from "../form/Label";
import { useAuth } from '../../context/AuthContext';
import axios from '../../api/axios';
import { useTranslation } from 'react-i18next';

export default function UserMetaCard() {
  const { user, updateUser } = useAuth();
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);
  const [showChangePhotoModal, setShowChangePhotoModal] = useState(false);
  const { t } = useTranslation();

  const handleOpenChangePasswordModal = () => setShowChangePasswordModal(true);
  const handleCloseChangePasswordModal = () => setShowChangePasswordModal(false);

  const handleOpenChangePhotoModal = () => setShowChangePhotoModal(true);
  const handleCloseChangePhotoModal = () => setShowChangePhotoModal(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [photoMessage, setPhotoMessage] = useState<{ type: string; text: string } | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);

      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    } else {
      setSelectedFile(null);
      setPhotoPreview(null);
    }
  };

  const handleChangePhoto = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setPhotoMessage({ type: 'error', text: t('pleaseSelectFile') });
      return;
    }

    setPhotoLoading(true);
    setPhotoMessage(null);

    const formData = new FormData();
    formData.append('photo', selectedFile);

    try {
      const response = await axios.patch('/api/v1/user/photo/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setPhotoMessage({ type: 'success', text: response.data.message || t('profilePhotoUpdated') });
      if (response.data.photo) {
        updateUser({ photo: response.data.photo });
      }
      handleCloseChangePhotoModal();
    } catch (error: any) {
      setPhotoMessage({ type: 'error', text: error.response?.data?.message || t('failedToUpdatePhoto') });
    } finally {
      setPhotoLoading(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    setLoading(true);

    if (newPassword !== confirmNewPassword) {
      setMessage({ type: 'error', text: t('passwordsDoNotMatch') });
      setLoading(false);
      return;
    }

    try {
      // Replace with your actual API call
      await axios.patch('/api/v1/user/change-password/', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setMessage({ type: 'success', text: t('passwordChanged') });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
      handleCloseChangePasswordModal();
    } catch (error: any) {
      setMessage({ type: 'error', text: error.response?.data?.detail || t('failedToChangePassword') });
    }
    setLoading(false);
  };
  return (
    <>
      <div className="p-5 border border-gray-200 rounded-2xl dark:border-gray-800 lg:p-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-col items-center w-full gap-6 xl:flex-row">
            <div className="w-20 h-20 overflow-hidden border border-gray-200 rounded-full dark:border-gray-800">
              <img
                src={user?.photo || '/images/user/default.png'}
                alt={t('userProfile')}
                className="h-20 w-20 rounded-full object-cover cursor-pointer"
                onClick={handleOpenChangePhotoModal}
              />
            </div>
            <div className="order-3 xl:order-2">
              <h4 className="mb-2 text-lg font-semibold text-center text-gray-800 dark:text-white/90 xl:text-left">
                {user?.firstName} {user?.lastName}
              </h4>
            </div>

          </div>
          <button
            onClick={handleOpenChangePasswordModal}
            className="flex w-1/4 items-center justify-center gap-2 rounded-full border border-gray-300 bg-white px-4 py-3 text-sm font-medium text-gray-700 shadow-theme-xs hover:bg-gray-50 hover:text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-white/[0.03] dark:hover:text-gray-200 lg:inline-flex"
          >
            {t('changePassword')}
          </button>
        </div>
      </div>
      

      <Modal isOpen={showChangePasswordModal} onClose={handleCloseChangePasswordModal} isFullscreen={false} className="relative w-full rounded-3xl bg-white  dark:bg-gray-900  max-w-[584px] p-5 lg:p-10">
         <form onSubmit={handleChangePassword} className="space-y-4">
           {message?.text && <p className={`text-sm ${message?.type === 'success' ? 'text-green-500' : 'text-red-500'}`}>{message.text}</p>}
 
           <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
             {t('changePassword')}
           </h2>
 
           <div>
             <Label htmlFor="currentPassword">{t('currentPassword')}</Label>
             <Input
               id="currentPassword"
               type="password"
               value={currentPassword}
               onChange={(e) => setCurrentPassword(e.target.value)}
               required
             />
           </div>
           <div>
             <Label htmlFor="newPassword">{t('newPassword')}</Label>
             <Input
               id="newPassword"
               type="password"
               value={newPassword}
               onChange={(e) => setNewPassword(e.target.value)}
               required
             />
           </div>
           <div>
             <Label htmlFor="confirmNewPassword">{t('confirmNewPassword')}</Label>
             <Input
               id="confirmNewPassword"
               type="password"
               value={confirmNewPassword}
               onChange={(e) => setConfirmNewPassword(e.target.value)}
               required
             />
           </div>
           <div className="flex justify-end space-x-2">
             <Button type="button" onClick={handleCloseChangePasswordModal} variant="outline">
               {t('cancel')}
             </Button>
             <Button type="submit" disabled={loading}>
               {loading ? t('saving') : t('save')}
             </Button>
           </div>
         </form>
       </Modal>

       <Modal isOpen={showChangePhotoModal} onClose={handleCloseChangePhotoModal} isFullscreen={false} className="relative w-full rounded-3xl bg-white dark:bg-gray-900 max-w-[584px] p-5 lg:p-10">
         <form onSubmit={handleChangePhoto} className="space-y-4">
           {photoMessage?.text && <p className={`text-sm ${photoMessage?.type === 'success' ? 'text-green-500' : 'text-red-500'}`}>{photoMessage.text}</p>}

           <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
             {t('changeProfilePhoto')}
           </h2>

           <div>
             <Label htmlFor="photoUpload">{t('uploadNewPhoto')}</Label>
             <Input
               id="photoUpload"
               type="file"
               onChange={handleFileChange}
               accept="image/*"
             />
           </div>

           {photoPreview && (
             <div>
               <Label>{t('photoPreview')}</Label>
               <img src={photoPreview} alt="Photo Preview" className="mt-2 w-32 h-32 object-cover rounded-full" />
             </div>
           )}

           <div className="flex justify-end space-x-2">
             <Button type="button" onClick={handleCloseChangePhotoModal} variant="outline">
               {t('cancel')}
             </Button>
             <Button type="submit" disabled={photoLoading}>
               {photoLoading ? t('saving') : t('saveChanges')}
             </Button>
           </div>
         </form>
       </Modal>
     </>
  );
}
