import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Modal } from "../../components/ui/modal";
import Label from "../../components/form/Label";
import DatePicker from "../../components/form/date-picker";
import Select from "../../components/form/Select";
import Button from "../../components/ui/button/Button";
import { format } from 'date-fns';

import { useState, useEffect } from "react";
import axios from '../../api/axios';
import { useTranslation } from 'react-i18next';

// Define the TypeScript interface for the table rows
interface Post {
  id: number;
  file_url: string | null;
  text: string;
  channel: string;
  datetime: string;
  reactions: any; // Assuming reactions can be any object/array, adjust if a specific type is known
  total_reactions: number;
}


export default function Posts() {
  const { t } = useTranslation();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [channel, setChannel] = useState('');
  const [channels, setChannels] = useState<{ label: string; value: string }[]>([]);

  const applyFilters = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      if (channel) params.channel = channel;

      const response = await axios.get('/api/v1/reports/posts/', { params });
      setPosts(response.data);
      setIsFilterOpen(false);
    } catch (err) {
      setError('Erro ao aplicar filtros');
      console.error('Erro ao aplicar filtros:', err);
    } finally {
      setLoading(false);
    }
  };  

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        const response = await axios.get('/api/v1/reports/posts/');
        setPosts(response.data);
      } catch (err) {
        setError('Failed to fetch top posts.');
        console.error('Error fetching top posts:', err);
      } finally {
        setLoading(false);
      }
    };

    const fetchChannels = async () => {
      try {
        const response = await axios.get('/api/v1/channels/default/');
        const options = response.data.map((ch: any) => ({
          label: ch.name,
          value: ch.id
        }));

        // Adiciona a opção "Todos" no início
        const allOption = { label: "Todos", value: "" }; // ou use i18n.t('all')
        setChannels([allOption, ...options]);
      } catch (err) {
        console.error('Erro ao buscar canais:', err);
      }
    };


    fetchChannels();

    fetchPosts();
  }, []);


  if (loading) {
    return <div>{t('dashboard.top_posts.loading')}</div>;
  }

  if (error) {
    return <div>Error: {t('dashboard.top_posts.error')}</div>;
  }
  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white px-4 pb-3 pt-4 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6">
      <div className="flex flex-col gap-2 mb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            {t('dashboard.top_posts.title')}
          </h3>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={() => setIsFilterOpen(true)} className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-theme-sm font-medium text-gray-700 shadow-theme-xs hover:bg-gray-50 hover:text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-white/[0.03] dark:hover:text-gray-200">
            <svg
              className="stroke-current fill-white dark:fill-gray-800"
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M2.29004 5.90393H17.7067"
                stroke=""
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M17.7075 14.0961H2.29085"
                stroke=""
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M12.0826 3.33331C13.5024 3.33331 14.6534 4.48431 14.6534 5.90414C14.6534 7.32398 13.5024 8.47498 12.0826 8.47498C10.6627 8.47498 9.51172 7.32398 9.51172 5.90415C9.51172 4.48432 10.6627 3.33331 12.0826 3.33331Z"
                fill=""
                stroke=""
                strokeWidth="1.5"
              />
              <path
                d="M7.91745 11.525C6.49762 11.525 5.34662 12.676 5.34662 14.0959C5.34661 15.5157 6.49762 16.6667 7.91745 16.6667C9.33728 16.6667 10.4883 15.5157 10.4883 14.0959C10.4883 12.676 9.33728 11.525 7.91745 11.525Z"
                fill=""
                stroke=""
                strokeWidth="1.5"
              />
            </svg>
            {t('dashboard.top_posts.filter')}
          </button>
          <button className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-theme-sm font-medium text-gray-700 shadow-theme-xs hover:bg-gray-50 hover:text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-white/[0.03] dark:hover:text-gray-200">
            {t('dashboard.top_posts.see_all')}
          </button>
        </div>
      </div>
      <div className="max-w-full overflow-x-auto">
        <Table>
          {/* Table Header */}
          <TableHeader className="border-gray-100 dark:border-gray-800 border-y">
            <TableRow>
              <TableCell
                isHeader
                className="py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                {t('dashboard.top_posts.table.image')}
              </TableCell>
              <TableCell
                isHeader
                className="py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                {t('dashboard.top_posts.table.text')}
              </TableCell>
              <TableCell
                isHeader
                className="py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                {t('dashboard.top_posts.table.channel')}
              </TableCell>
              <TableCell
                isHeader
                className="py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                {t('dashboard.top_posts.table.datetime')}
              </TableCell>
              <TableCell
                isHeader
                className="py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
              >
                {t('dashboard.top_posts.table.reactions')}
              </TableCell>
            </TableRow>
          </TableHeader>

          {/* Table Body */}

          <TableBody className="divide-y divide-gray-100 dark:divide-gray-800">
            {posts.map((post) => (
              <TableRow key={post.id} className="">
                <TableCell className="py-3">
                  <div className="flex items-center gap-3">
                    {post.file_url && (
                      <div className="h-[50px] w-[50px] overflow-hidden rounded-md">
                        <img
                          src={post.file_url}
                          className="h-[50px] w-[50px] object-cover"
                          alt="Post Image"
                        />
                      </div>
                    )}
                  </div>
                </TableCell>
                <TableCell className="py-3 text-gray-500 text-theme-sm dark:text-gray-400">
                  {post.text}
                </TableCell>
                <TableCell className="py-3 text-gray-500 text-theme-sm dark:text-gray-400">
                  {post.channel}
                </TableCell>
                <TableCell className="py-3 text-gray-500 text-theme-sm dark:text-gray-400">
                  {post.datetime}
                </TableCell>
                <TableCell className="py-3 text-gray-500 text-theme-sm dark:text-gray-400">
                  {post.total_reactions}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <Modal
        isOpen={isFilterOpen}
        onClose={() => setIsFilterOpen(false)}
        isFullscreen={false}
        className="relative w-full rounded-3xl bg-white dark:bg-gray-900 max-w-[584px] p-5 lg:p-10"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            applyFilters();
          }}
          className="space-y-4"
        >
          <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
            {t('dashboard.top_posts.filter')}
          </h2>

          <div>
            <DatePicker
              id="startDate"
              label={t('dashboard.top_posts.start_date')}
              defaultDate={startDate}
              onChange={([date]) => setStartDate(format(date, 'dd/MM/yyyy'))}
            />
          </div>

          <div>
            <DatePicker
              id="endDate"
              label={t('dashboard.top_posts.end_date')}
              defaultDate={endDate}
              onChange={([date]) => setEndDate(format(date, 'dd/MM/yyyy'))}
            />
          </div>

          <div>
            <Label htmlFor="channel">{t('dashboard.top_posts.channel')}</Label>
            <Select
              options={channels}
              value={channel}
              onChange={(val: string) => setChannel(val)}
              placeholder={t('dashboard.top_posts.select_channel')}
            />
          </div>

          <Button type="submit">{t('dashboard.top_posts.apply_filters')}</Button>
        </form>
      </Modal>

    </div>
  );
}
