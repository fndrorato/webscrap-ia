import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../ui/table";


import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

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


export default function TopPosts({ posts }: { posts: Post[] }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white px-4 pb-3 pt-4 dark:border-gray-800 dark:bg-white/[0.03] sm:px-6">
      <div className="flex flex-col gap-2 mb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 dark:text-white/90">
            {t('dashboard.top_posts.title')}
          </h3>
        </div>

        <div className="flex items-center gap-3">

          <button
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-theme-sm font-medium text-gray-700 shadow-theme-xs hover:bg-gray-50 hover:text-gray-800 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-white/[0.03] dark:hover:text-gray-200"
            onClick={() => navigate('/reports/posts')}
          >
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
    </div>
  );
}
