import { useEffect, useState } from 'react';
import { Modal } from '../ui/modal';
import Input from '../form/input/InputField';
import Label from '../form/Label';
import Button from '../ui/button/Button';

interface SessionData {
  id: number;
  name: string;
  user: string;
  status: any;
  me_id: string;
  me_push_name: string;
  config: string;
  webhook_url?: string;
  webhook_events?: string[];
  created_at: string;
  updated_at: string;
}

interface SessionFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (name: string, webhookUrl: string, webhookEvents: string[], id?: number) => void;
  session?: SessionData | null;
}

const SessionFormModal: React.FC<SessionFormModalProps> = ({ isOpen, onClose, onSubmit, session }) => {
  const [sessionName, setSessionName] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookEvents, setWebhookEvents] = useState('');

  useEffect(() => {
    if (session) {
      setSessionName(session.name);
      setWebhookUrl(session.webhook_url || '');
      setWebhookEvents(session.webhook_events?.join(',') || '');
    } else {
      setSessionName('');
      setWebhookUrl('');
      setWebhookEvents('');
    }
  }, [session]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(sessionName, webhookUrl, webhookEvents.split(',').map(event => event.trim()), session?.id);
    setSessionName('');
    setWebhookUrl('');
    setWebhookEvents('');
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} isFullscreen={false} className="relative w-full rounded-3xl bg-white  dark:bg-gray-900  max-w-[584px] p-5 lg:p-10">
      <form onSubmit={handleSubmit} className="space-y-4">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
          {session ? 'Edit Session' : 'Create New Session'}
        </h2>

        <div>
          <Label htmlFor="sessionName">Session Name</Label>
          <Input
            id="sessionName"
            type="text"
            value={sessionName}
            onChange={(e) => setSessionName(e.target.value)}
            required
          />
        </div>

        <div>
          <Label htmlFor="webhookUrl">Webhook URL</Label>
          <Input
            id="webhookUrl"
            type="url"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
          />
        </div>

        <div>
          <Label htmlFor="webhookEvents">Webhook Events (comma-separated)</Label>
          <Input
            id="webhookEvents"
            type="text"
            value={webhookEvents}
            onChange={(e) => setWebhookEvents(e.target.value)}
            placeholder="message,qr,status"          />
        </div>
        <Button type="submit">
          {session ? 'Update Session' : 'Create Session'}
        </Button>
      </form>
    </Modal>
  );
};

export default SessionFormModal;