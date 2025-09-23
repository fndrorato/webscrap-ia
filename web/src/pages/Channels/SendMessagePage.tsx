import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from '../../api/axios';
import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import PageMeta from "../../components/common/PageMeta";
import ChannelChat from "./ChannelChat";
import { Channel } from './ChannelsList';
import { Post } from './ChannelChat';

export default function SendMessagePage() {
  const { channelId } = useParams<{ channelId: string }>();
  const [channel, setChannel] = useState<Channel | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchChannel = async () => {
      if (!channelId) {
        setLoading(false);
        return;
      }
      try {
        const response = await axios.get(`/api/v1/channels/default/${channelId}/`);
        console.log(response.data)
        setChannel(response.data.channel);
        setPosts(response.data.posts);
      } catch (err) {
        setError('Failed to fetch channel details.');
        console.error('Error fetching channel:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchChannel();
  }, [channelId]);

  if (loading) {
    return <div>Loading channel...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }
  return (
    <div>
      <PageMeta
        title="React.js Chart Dashboard | TailAdmin - React.js Admin Dashboard Template"
        description="This is React.js Chart Dashboard page for TailAdmin - React.js Tailwind CSS Admin Dashboard Template"
      />
      <PageBreadcrumb pageTitle="Channel Chat" pageSubTitle={channel?.name} />
      <div className="space-y-6">
          <ChannelChat channel={channel} posts={posts} setPosts={setPosts} />
      </div>
    </div>
  );
}
