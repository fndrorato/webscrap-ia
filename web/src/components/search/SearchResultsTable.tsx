import React from 'react';
import { useTranslation } from 'react-i18next';

interface ProductImage {
  id: number;
  image_url: string;
  is_main: boolean;
  alt_text: string;
  order: number;
  original_url: string;
}

interface Product {
  id: number;
  main_image_url: string;
  images: ProductImage[];
  name: string;
  description: string;
  status?: number; // 0: declined, 1: pending, 2: approved
}

interface SearchResultsTableProps {
  results: Product[];
  onImageClick: (images: ProductImage[]) => void;
  onApprove?: (productId: number) => void;
  onDecline?: (productId: number) => void;
}

const SearchResultsTable: React.FC<SearchResultsTableProps> = ({ results, onImageClick, onApprove, onDecline }) => {
  const { t } = useTranslation();

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white dark:bg-gray-800">
        <thead>
          <tr>
            <th className="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('search.results.image')}</th>
            <th className="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('search.results.name')}</th>
            <th className="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('search.results.description')}</th>
            {(onApprove || onDecline) && (
              <th className="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('search.results.actions')}</th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {results.map((product) => (
            <tr key={product.id}>
              <td className="py-4 px-6">
                <img 
                  src={product.main_image_url} 
                  alt={product.name} 
                  className="h-16 w-16 object-cover cursor-pointer rounded-md" 
                  onClick={() => onImageClick(product.images)}
                />
              </td>
              <td className="py-4 px-6 text-sm text-gray-900 dark:text-white">{product.name}</td>
              <td className="py-4 px-6 text-sm text-gray-500 dark:text-gray-400">{product.description}</td>
              {(onApprove || onDecline) && (
                <td className="py-4 px-6">
                  {product.status === undefined || product.status === 1 ? (
                    <div className="flex space-x-2">
                      {onApprove && (
                        <button 
                          onClick={() => onApprove(product.id)} 
                          className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded"
                        >
                          {t('search.results.approve')}
                        </button>
                      )}
                      {onDecline && (
                        <button 
                          onClick={() => onDecline(product.id)} 
                          className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded"
                        >
                          {t('search.results.reject')}
                        </button>
                      )}
                    </div>
                  ) : product.status === 2 ? (
                    <span className="text-green-600 font-semibold">{t('search.results.approved')}</span>
                  ) : (
                    <span className="text-red-600 font-semibold">{t('search.results.declined')}</span>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default SearchResultsTable;