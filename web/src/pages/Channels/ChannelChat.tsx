import React, { useRef, useState, useEffect } from 'react';
import axios from '../../api/axios';
import { useParams } from 'react-router-dom';
import AttachmentPreviewModal from './AttachmentPreviewModal';
import PollModal from './PollModal';
import { Modal } from '../../components/ui/modal';
import { useTranslation } from 'react-i18next';

// Assuming Channel interface is defined here or imported from a common types file
interface Channel {
  id: number;
  name: string;
  picture: string;
  // Add other properties of Channel if they exist
}

export interface Post {
  id: number;
  author: string;
  author_name: string;
  message_type: string;
  status: string;
  text: string | null;
  mimetype: string | null;
  file_url: string | null;
  file_name: string | null;
  response_message_id: number | null;
  created_at: string;
  updated_at: string | null;
  poll_name: string | null;
  poll_options: { text: string; votes: number }[] | null;
}

interface ChannelChatProps {
  channel: Channel | null;
  posts: Post[];
  setPosts: React.Dispatch<React.SetStateAction<Post[]>>;
}

const ChannelChat: React.FC<ChannelChatProps> = ({ channel, posts, setPosts }) => {
  const { t } = useTranslation();
  const [openDropdownId, setOpenDropdownId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpenDropdownId(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [dropdownRef]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [posts]);
  const { channelId: channelIdParam } = useParams<{ channelId: string }>();
  const channelId = channelIdParam ? channelIdParam : null;

  const [messageText, setMessageText] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isPollModalOpen, setIsPollModalOpen] = useState(false);
  const [editingPostId, setEditingPostId] = useState<number | null>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [postToDelete, setPostToDelete] = useState<Post | null>(null);

  // Effect to revoke object URL for selected file when it changes or component unmounts
  useEffect(() => {
    return () => {
      selectedFiles.forEach(file => URL.revokeObjectURL(URL.createObjectURL(file)));
    };
  }, [selectedFiles]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const files = Array.from(event.target.files);
      const newFiles = files.slice(0, 10 - selectedFiles.length);
      setSelectedFiles(prevFiles => [...prevFiles, ...newFiles]);
      setIsModalOpen(true);
    }
  };

  const handleSendPoll = async (question: string, options: string[]) => {
    setLoading(true);

    if (!channelId) {
      console.error(t('channel_chat.channel_id_missing'));
      setLoading(false);
      return;
    }

    const formData = new FormData();
    formData.append('channel_id', channelId.toString());
    formData.append('poll_name', question);
    formData.append('poll_options', JSON.stringify(options));

    try {
      const response = await axios.post(`/api/v1/posts/channel/send_message/${channelId}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.data.status_code !== 200) {
        alert(`${t('channel_chat.error_sending_poll')}: ${response.data.detail}`);
      } else {
        setPosts(prevPosts => [...prevPosts, response.data.post]);
        setIsPollModalOpen(false);
      }
    } catch (err: any) {
      console.error(t('channel_chat.error_sending_poll_console'), err);
      alert(`${t('channel_chat.error_sending_poll')}: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSendAttachment = async (messageText: string, attachments: File[]) => {
    setLoading(true); // Activate loading indicator for attachment process

    if (!channelId) {
      console.error(t('channel_chat.channel_id_missing'));
      setLoading(false);
      return;
    }

    try {
      for (const attachment of attachments) {
        const formData = new FormData();
        formData.append('channel_id', channelId.toString());
        formData.append('message_text', messageText);
        formData.append('attachment', attachment);

        const response = await axios.post(`/api/v1/posts/channel/send_message/${channelId}/`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        if (response.data.status_code !== 200) {
          alert(`${t('channel_chat.error_sending_attachment')}: ${response.data.detail}`);
          // If one fails, we might want to stop or continue, for now, we alert and continue
        } else {
          setPosts(prevPosts => [...prevPosts, response.data.post]);
        }
      }
      setMessageText('');
      setSelectedFiles([]);
      setIsModalOpen(false);
    } catch (err: any) {
      console.error(t('channel_chat.error_sending_attachment_console'), err);
      alert(`${t('channel_chat.error_sending_attachment')}: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoading(false); // Deactivate loading indicator
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!messageText.trim() || loading) return;

    setLoading(true);
    try {
      if (editingPostId) {
        if (!channel?.id) {
          console.error(t('channel_chat.channel_id_missing'));
          setLoading(false);
          return;
        }        
        // Handle edit action
        console.log(t('channel_chat.editing_post', { editingPostId, messageText }));
        const formData = new FormData();
        formData.append('message_text', messageText);
        formData.append('session', 'default'); // se necessário

        const response = await axios.put(
          `/api/v1/posts/channel/update_message/${channel.id}/${editingPostId}/`,
          formData,
          {
            headers: { 'Content-Type': 'multipart/form-data' }
          }
        );
        
        if (response.data.status_code === 200) {
          setPosts(prevPosts =>
            prevPosts.map(post =>
              post.id === editingPostId
                ? { ...post, text: response.data.post.text, updated_at: response.data.post.updated_at } // Assuming author_name doesn't change on edit
                : post
            )
          );
        } else {
          alert(`${t('channel_chat.error_updating_message')}: ${response.data.detail}`);
        }
      } else {
        // Handle new message action
        if (!channel?.id) {
          console.error(t('channel_chat.channel_id_missing'));
          setLoading(false);
          return;
        }

        const formData = new FormData();
        formData.append('channel_id', channel.id.toString());
        formData.append('message_text', messageText);

        const response = await axios.post(`/api/v1/posts/channel/send_message/${channel.id}/`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });

        if (response.data.status_code !== 200) {
          alert(`Erro ao enviar mensagem: ${response.data.detail}`);
        } else {
          setPosts(prevPosts => [...prevPosts, response.data.post]);
        }
      }
      setMessageText('');
      setEditingPostId(null);
    } catch (error: any) {
      console.error(t('channel_chat.error_handling_message'), error);
      alert(`${t('channel_chat.error_sending_message')}: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePost = async (postId: number) => {
    setIsDeleteModalOpen(false);
    setLoading(true);

    if (!channel?.id) {
      console.error(t('channel_chat.channel_id_missing'));
      setLoading(false);
      return;
    }

    try {
      const response = await axios.delete(
        `/api/v1/posts/channel/delete_message/${channel.id}/${postId}/`
      );

      if (response.data.status_code === 200) {
        // Refresh the page on successful deletion
        window.location.reload();
      } else {
        alert(`${t('channel_chat.error_deleting_message')}: ${response.data.detail}`);
      }
    } catch (error: any) {
      console.error(t('channel_chat.error_deleting_message_console'), error);
      alert(`${t('channel_chat.error_deleting_message')}: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative !max-h-[calc(100vh-170px)] overflow-y-auto flex flex-col rounded-xl overflow-hidden border border-gray-200 dark:border-gray-800 bg-white dark:bg-white/[0.03] font-inter">
      {/* Top Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-white/[0.03] rounded-t-xl">
        <div className="flex items-center gap-3">
          <img
            src={channel?.picture || "https://placehold.co/200x200/cccccc/333333?text=Avatar"}
            alt="avatar"
            className="w-10 h-10 rounded-full object-cover"
          />
          <div>
            <h5 className="text-sm font-medium text-gray-800 dark:text-white/90">{channel?.name || t('channel_chat.loading')}</h5>
          </div>
        </div>
      </div>

      {/* Scrollable Message Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6 custom-scrollbar">
        {posts.map((post) => (
          <div key={post.id} className={`flex items-start gap-3 max-w-[70%] rounded-lg relative ${post.status === 'deleted' ? 'opacity-60' : ''}`}>
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold text-xs">
              {post.author_name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0,2)}
            </div>
            <div className="relative">
              <div className="bg-gray-100 dark:bg-white/10 rounded-lg px-4 py-2 pr-10">
                {post.file_url && (
                  <div className="mb-2">
                    {post.mimetype?.startsWith('image/') ? (
                      <img src={post.file_url} alt={post.file_name || t('channel_chat.image')} className="max-w-full max-h-64 rounded" />
                    ) : post.mimetype?.startsWith('video/') ? (
                      <video controls className="max-w-full max-h-64 rounded">
                        <source src={post.file_url} type={post.mimetype} />
                      </video>
                    ) : (
                      <a href={post.file_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
                        {post.file_name || t('channel_chat.download_file')}
                      </a>
                    )}
                  </div>
                )}
                {post.message_type === 'poll' && post.poll_name && post.poll_options ? (
                  <div className="mb-2">
                    <p className="font-semibold text-gray-800 dark:text-white mb-2">{post.poll_name}</p>
                    <div className="space-y-2">
                    {(() => {
                      const totalVotes = post.poll_options.reduce((sum, option) => sum + option.votes, 0);
                      return post.poll_options.map((option, idx) => (
                        <div key={idx} className="flex flex-col">
                          <div className="flex justify-between items-center">
                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{option.text}</span>
                            <span className="text-xs text-gray-500 dark:text-gray-400">{option.votes} {t('channel_chat.votes')} ({totalVotes > 0 ? ((option.votes / totalVotes) * 100).toFixed(0) : 0}%)</span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 mt-1">
                            <div
                              className="bg-blue-600 h-2.5 rounded-full"
                              style={{ width: `${totalVotes > 0 ? (option.votes / totalVotes) * 100 : 0}%` }}
                            ></div>
                          </div>
                        </div>
                      ));
                    })()}
                  </div>
                  </div>
                ) : post.text && (
                  <p className={`text-sm ${post.status === 'deleted' ? 'text-red-500 dark:text-red-400' : 'text-gray-800 dark:text-white'}`}>
                    {post.text}
                  </p>
                )}
                {post.status === 'deleted' && (
                  <p className="text-xs text-red-500 dark:text-red-400 mt-1">{t('channel_chat.message_deleted')}</p>
                )}
              </div>
              <span className="block mt-1 text-xs text-gray-400">
                {post.author_name}, {new Date(post.updated_at || post.created_at).toLocaleString()}
              </span>
              {post.status !== 'deleted' && (
                <div className="absolute top-2 right-2 z-50">
                  <button
                    className="text-gray-500 hover:text-gray-700 focus:outline-none"
                    onClick={() => setOpenDropdownId(openDropdownId === post.id ? null : post.id)}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" className="w-6 h-6">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM12.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM18.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0z" />
                    </svg>
                  </button>
                  {openDropdownId === post.id && (
                    <div ref={dropdownRef} className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-10">
                      <button
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
                        onClick={() => {
                          setMessageText(post.text || '');
                          setEditingPostId(post.id);
                          setOpenDropdownId(null);
                        }}
                      >
                        {t('channel_chat.edit')}
                      </button>
                      <button
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 w-full text-left"
                        onClick={() => {
                          setPostToDelete(post);
                          setIsDeleteModalOpen(true);
                          setOpenDropdownId(null);
                        }}
                      >
                        {t('channel_chat.delete')}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {/* Adicione um div vazio no final para rolar até ele */}
        <div ref={messagesEndRef} />

      </div>

      {/* Footer */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center justify-between gap-3 p-4 border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-white/[0.03] rounded-b-xl"
      >
        <div className="relative w-full">
          <input
            type="text"
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            placeholder={editingPostId ? t('channel_chat.editing_message') : t('channel_chat.type_a_message')}
            className="w-full rounded-full border border-gray-300 dark:border-gray-700 bg-transparent px-4 py-2 text-sm text-gray-800 placeholder:text-gray-400 dark:text-white/90 dark:placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <label htmlFor="fileInput" className="cursor-pointer text-gray-400 hover:text-gray-600">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13.5" />
          </svg>
        </label>
        <input type="file" id="fileInput" onChange={handleFileChange} className="hidden" multiple accept="image/*,video/*" />

        <button
          type="button"
          onClick={() => setIsPollModalOpen(true)}
          className="cursor-pointer text-gray-400 hover:text-gray-600"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.5l6.75 6.75L21 6.75" />
          </svg>
        </button>

        <AttachmentPreviewModal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setSelectedFiles([]); // Clear selected files when modal is closed
          }}
          files={selectedFiles}
          onSend={handleSendAttachment} // This function will need to be updated to handle multiple files
          loading={loading}
        />

        <PollModal
          isOpen={isPollModalOpen}
          onClose={() => setIsPollModalOpen(false)}
          onSendPoll={handleSendPoll}
        />

        {/* Delete Confirmation Modal */}
        {isDeleteModalOpen && postToDelete && (
          <Modal isOpen={isDeleteModalOpen} onClose={() => setIsDeleteModalOpen(false)} className="w-96 p-6 rounded-lg shadow-lg bg-white dark:bg-gray-900">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Confirmar Exclusão</h3>
            <p className="text-sm text-gray-700 dark:text-gray-300 mb-6">
              Tem certeza que deseja excluir esta publicação?
            </p>
            <div className="flex justify-end gap-3">
              <button
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
                onClick={() => setIsDeleteModalOpen(false)}
              >
                Não
              </button>
              <button
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
                onClick={() => handleDeletePost(postToDelete.id)}
              >
                Sim
              </button>
            </div>
          </Modal>
        )}

        <button
        type="submit"
        disabled={!messageText.trim() || loading}
        className={`flex h-9 w-9 items-center justify-center rounded-full ${
            loading ? 'bg-blue-300 cursor-not-allowed' : 'bg-blue-500 hover:bg-blue-600'
        } text-white transition`}
        >
        {loading ? (
            <svg
            className="animate-spin h-5 w-5 text-white"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            >
            <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
            ></circle>
            <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            ></path>
            </svg>
        ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
        )}
        </button>

      </form>
    </div>
  );
};

export default ChannelChat;
