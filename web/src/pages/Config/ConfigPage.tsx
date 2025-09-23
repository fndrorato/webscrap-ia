import useSessionSocket from '../../hooks/useSessionSocket';
import { useEffect, useState } from 'react';
import QRCode from 'react-qr-code';
import { PencilIcon, PlayIcon, ArrowPathIcon, StopIcon, ArrowLeftOnRectangleIcon, TrashIcon, QrCodeIcon } from '@heroicons/react/24/outline';
import { format } from 'date-fns';
import { useTranslation } from 'react-i18next';

import PageBreadcrumb from '../../components/common/PageBreadCrumb';
import SessionFormModal from '../../components/common/SessionFormModal';
import axios from '../../api/axios';
import { Modal } from '../../components/ui/modal';
import Button from '../../components/ui/button/Button';
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from '../../components/ui/table';

interface SessionStatus {
  id: number;
  code: string;
  name: string;
}

interface SessionData {
  id: number;
  name: string;
  user: string;
  status: SessionStatus;
  me_id: string;
  me_push_name: string;
  config: string;
  created_at: string;
  updated_at: string;
}

export default function ConfigPage() {
  const { t } = useTranslation();
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalState, setModalState] = useState<{ isOpen: boolean; session: SessionData | null }>({ isOpen: false, session: null });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<SessionData | null>(null);

  const fetchSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get<SessionData[]>('/api/v1/sessions/');
      setSessions(response.data);
    } catch (err) {
      console.error('Error fetching sessions:', err);
      setError(t('failedToLoadSessions'));
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCreateSessionModal = () => {
    setModalState({ isOpen: true, session: null });
  };

  const handleOpenEditSessionModal = (session: SessionData) => {
    setModalState({ isOpen: true, session: session });
  };

  const handleDeleteSession = (session: SessionData) => {
    setSessionToDelete(session);
    setShowDeleteConfirm(true);
  };

  const confirmDeleteSession = async () => {
    if (sessionToDelete) {
      try {
        await axios.delete(`/api/v1/sessions/${sessionToDelete.id}/`);
        fetchSessions();
        setShowDeleteConfirm(false);
        setSessionToDelete(null);
      } catch (error) {
        console.error('Error deleting session:', error);
        // Handle error, e.g., show a toast notification
      }
    }
  };

  const handleCloseModal = () => {
    setModalState({ isOpen: false, session: null });
  };

  const handleCreateSession = async (name: string, webhookUrl: string, webhookEvents: string[], id?: number) => {
    try {
      setLoading(true);
      setError(null);
      if (id) {
        await axios.put(`/api/v1/sessions/${id}/`, { name, webhook_url: webhookUrl, webhook_events: webhookEvents });
        setModalState({ isOpen: false, session: null });
      } else {
        await axios.post('/api/v1/sessions/', { name, webhook_url: webhookUrl, webhook_events: webhookEvents });
        setModalState({ isOpen: false, session: null });
      }
      fetchSessions(); // Recarrega as sessões após a criação/atualização
    } catch (err) {
      setError(t(id ? 'failedToUpdateSession' : 'failedToCreateSession'));
      console.error(`Error ${id ? 'updating' : 'creating'} session:`, err);
    } finally {
      setLoading(false);
    }
  };

  const [showQrCodeModal, setShowQrCodeModal] = useState(false);
  const [qrCodeImage, setQrCodeImage] = useState('');
  const [isLoadingQrCode, setIsLoadingQrCode] = useState(false);
  const [qrCodeError, setQrCodeError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [qrCodeSessionName, setQrCodeSessionName] = useState('');

  const handleSessionAction = async (sessionName: string, action: 'start' | 'restart' | 'stop' | 'logout') => {
    setActionError(null);
    try {
      const response = await axios.post(`/api/v1/sessions/${sessionName}/${action}/`);
      if (response.status !== 200) {
        setActionError(response.data.error || t(`failedTo${action.charAt(0).toUpperCase() + action.slice(1)}Session`));
      }
      fetchSessions();
    } catch (err: any) {
      console.error(`Error ${action}ing session:`, err);
      setActionError(err.response?.data?.error || t('failedToPerformAction'));
    }
  };

  const handleShowQrCode = async (sessionName: string) => {
    setIsLoadingQrCode(true);
    setShowQrCodeModal(true); // Open modal with loading state
    setQrCodeImage(''); // Clear previous QR code
    setQrCodeSessionName(sessionName);
    try {
      const response = await axios.get(`/api/v1/sessions/${sessionName}/auth/`);
      if (response.status === 200 && response.data && response.data.qr_code_value) {
        try {
            setQrCodeImage(response.data.qr_code_value);
            setQrCodeError('');
        } catch (qrError) {
            console.error('Error generating QR code:', qrError);
            setQrCodeImage('');
            setQrCodeError(t('failedToGenerateQrCodeImage'));
        }
      } else if (response.data && response.data.error) {
        setQrCodeImage('');
        setQrCodeError(response.data.error);
      } else {
        setQrCodeImage('');
        setQrCodeError(t('unknownErrorOccurred'));
      }
    } catch (err: any) {
      console.error('Failed to fetch QR code:', err);
      setQrCodeImage('');
      setQrCodeError(err.response?.data?.error || t('failedToConnectToServer'));
    } finally {
      setIsLoadingQrCode(false);
    }
  };

  useSessionSocket((data) => {
    // Atualiza a sessão no estado React com os novos dados recebidos do WS
    console.log(data)
    setSessions((prevSessions) =>
      prevSessions.map((session) =>
        session.name === data.session
          ? { ...session, status: { ...session.status, code: data.status, name: data.status.replace(/_/g, ' ') } }
          : session
      )
    );
  });  

  useEffect(() => {
    fetchSessions();
  }, []);

  if (loading) {
    return <div>{t('loadingSessions')}</div>;
  }

  if (error) {
    return <div>{t('error')}: {error}</div>;
  }

  return (
    <>
      <PageBreadcrumb pageTitle={t('sessionConfigurations')} />
      <div className="p-2">
        <button
          onClick={handleOpenCreateSessionModal}
          className="inline-flex items-center justify-center gap-2 rounded-lg transition  px-4 py-3 text-sm bg-brand-500 text-white shadow-theme-xs hover:bg-brand-600 disabled:bg-brand-300 mb-4"
        >
          {t('startNewSession')}
        </button>
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/[0.05] dark:bg-white/[0.03]">
          <div className="max-w-full overflow-x-auto">
            <Table>
              <TableHeader className="border-b border-gray-100 dark:border-white/[0.05]">
                <TableRow>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('name')}</TableCell>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('phone')}</TableCell>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('status')}</TableCell>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('createdAt')}</TableCell>
                  <TableCell isHeader className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">{t('actions')}</TableCell>
                </TableRow>
              </TableHeader>
              <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
                {actionError && (
                  <TableRow>
                    <td colSpan={6} className="px-4 py-3 text-red-500 text-center text-theme-sm dark:text-red-400">
                      Error: {actionError}
                    </td>
                  </TableRow>
                )}

                {sessions.map((session) => (
                  <TableRow key={session.id}>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">{session.name}</TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">{`${session.me_id} (${session.me_push_name})`}</TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                      <div className="flex items-center gap-2">
                        {session.status.name}
                        {session.status.code === 'scan_qr_code' && (
                          <button
                            title={t('showQrCode')}
                            className="p-1 rounded-full border border-gray-500 hover:bg-gray-300 dark:hover:bg-white/[0.05]"
                            onClick={() => handleShowQrCode(session.name)}
                          >
                            <QrCodeIcon className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                          </button>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">{format(new Date(session.created_at), 'dd/MM/yyyy HH:mm:ss')}</TableCell>
                    <TableCell className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400">
                      <div className="flex items-center space-x-2">
                        <button title={t('edit')} className="p-2 rounded-full border border-gray-500 hover:bg-gray-300 dark:hover:bg-white/[0.05]" onClick={() => handleOpenEditSessionModal(session)}>
                          <PencilIcon className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                        </button>
                        <button title={t('start')} className="p-2 rounded-full border border-gray-500 hover:bg-gray-300 dark:hover:bg-white/[0.05]" onClick={() => handleSessionAction(session.name, 'start')}>
                          <PlayIcon className="w-5 h-5 text-green-500" />
                        </button>                        
                        <button title={t('restart')} className="p-2 rounded-full border border-gray-500 hover:bg-gray-300 dark:hover:bg-white/[0.05]" onClick={() => handleSessionAction(session.name, 'restart')}>
                          <ArrowPathIcon className="w-5 h-5 text-blue-500" />
                        </button>
                        <button title={t('stop')} className="p-2 rounded-full border border-gray-500 hover:bg-gray-300 dark:hover:bg-white/[0.05]" onClick={() => handleSessionAction(session.name, 'stop')}>
                          <StopIcon className="w-5 h-5 text-red-500" />
                        </button>
                        <button title={t('logout')} className="p-2 rounded-full border border-gray-500 hover:bg-gray-300 dark:hover:bg-white/[0.05]" onClick={() => handleSessionAction(session.name, 'logout')}>
                          <ArrowLeftOnRectangleIcon className="w-5 h-5 text-yellow-500" />
                        </button>
                        <button title={t('delete')} className="p-2 rounded-full border border-gray-500 hover:bg-gray-300 dark:hover:bg-white/[0.05]" onClick={() => handleDeleteSession(session)}>
                          <TrashIcon className="w-5 h-5 text-gray-500 dark:text-gray-400" />
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
      <SessionFormModal
        isOpen={modalState.isOpen}
        onClose={handleCloseModal}
        onSubmit={handleCreateSession}
        session={modalState.session}
      />

      {/* Delete Confirmation Modal */}
      <Modal isOpen={showDeleteConfirm} onClose={() => setShowDeleteConfirm(false)} isFullscreen={false} className="relative w-full rounded-3xl bg-white dark:bg-gray-900 max-w-[400px] p-5 lg:p-10">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">{t('confirmDeletion')}</h2>
        <p className="text-gray-600 dark:text-gray-300 mb-6">
          {t('confirmDeleteSessionMessage', { sessionName: sessionToDelete?.name })}
        </p>
        <div className="flex justify-end space-x-4">
          <Button onClick={() => setShowDeleteConfirm(false)} className="bg-gray-300 text-gray-800 hover:bg-gray-400 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600">
            {t('cancel')}
          </Button>
          <Button onClick={confirmDeleteSession} className="bg-red-500 text-white hover:bg-red-600">
            {t('delete')}
          </Button>
        </div>
      </Modal>

      {showQrCodeModal && (
        <Modal isOpen={showQrCodeModal} onClose={() => setShowQrCodeModal(false)}>
            <div className="p-6">
              <h3 className="text-lg font-medium mb-4 text-gray-900 dark:text-white">{t('qrCodeForSession', { sessionName: qrCodeSessionName })}</h3>
              <div className="flex flex-col items-center justify-center">
                {isLoadingQrCode ? (
                  <div className="flex items-center justify-center h-64 w-64 bg-gray-100 rounded-lg">
                    <ArrowPathIcon className="h-8 w-8 animate-spin text-gray-400" />
                  </div>
                ) : qrCodeError ? (
                  <div className="flex flex-col items-center justify-center h-64 w-64 bg-red-50 rounded-lg p-4">
                      <p className="text-red-600 text-center">{t('error')}: {qrCodeError}</p>
                    </div>
                  ) : qrCodeImage ? (
                    <QRCode value={qrCodeImage} size={256} level="H" />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-64 w-64 bg-gray-100 rounded-lg p-4">
                      <p className="text-gray-500 text-center">{t('noQrCodeAvailable')}</p>
                    </div>
                  )}
                </div>
                <div className="flex justify-end mt-4">
                  <Button onClick={() => setShowQrCodeModal(false)} className="bg-gray-300 text-gray-800 hover:bg-gray-400 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600">
                    {t('close')}
                  </Button>
                </div>
              </div>
          </Modal>
        )}

        <SessionFormModal
          isOpen={modalState.isOpen}
          onClose={handleCloseModal}
          onSubmit={handleCreateSession}
          session={modalState.session}
        />

        {/* Delete Confirmation Modal */}
        <Modal isOpen={showDeleteConfirm} onClose={() => setShowDeleteConfirm(false)} isFullscreen={false} className="relative w-full rounded-3xl bg-white dark:bg-gray-900 max-w-[400px] p-5 lg:p-10">
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">Confirm Deletion</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-6">
            Are you sure you want to delete session "{sessionToDelete?.name}"? This action cannot be undone.
          </p>
          <div className="flex justify-end space-x-4">
            <Button onClick={() => setShowDeleteConfirm(false)} className="bg-gray-300 text-gray-800 hover:bg-gray-400 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600">
              Cancel
            </Button>
            <Button onClick={confirmDeleteSession} className="bg-red-500 text-white hover:bg-red-600">
              Delete
            </Button>
          </div>
        </Modal>
      </>
    );
  }