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
  price: number;
  sku_code: string;
  created_at: string; // Changed from scraped_at to created_at
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

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) {
        console.error("Invalid Date string:", dateString);
        return "Fecha inválida";
      }
      return date.toLocaleString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    } catch (e) {
      console.error("Error formatting date:", dateString, e);
      return "Fecha inválida";
    }
  };

  const formatPrice = (priceString: string | number) => {
    if (priceString === null || priceString === undefined || priceString === "") {
      return "N/A";
    }
    let priceNumber: number;
    if (typeof priceString === 'string') {
      // Remove everything after the decimal point and then parse as float
      const cleanedPriceString = priceString.split('.')[0];
      priceNumber = parseFloat(cleanedPriceString);
    } else {
      priceNumber = priceString;
    }

    if (isNaN(priceNumber)) {
      console.error("Invalid Price string/number:", priceString);
      return "N/A";
    }
    return priceNumber.toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white dark:bg-gray-800">
        <thead>
          <tr>
            <th className="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('search.results.image')}</th>
            <th className="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('search.results.name')}</th>
            <th className="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('search.results.description')}</th>
            <th className="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Precio</th>
            <th className="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Código</th>
            <th className="py-3 px-6 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Fecha Hora</th>
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
              <td className="py-4 px-6 text-sm text-gray-900 dark:text-white">{formatPrice(product.price)}</td>
              <td className="py-4 px-6 text-sm text-gray-900 dark:text-white">{product.sku_code}</td>
              <td className="py-4 px-6 text-sm text-gray-900 dark:text-white">{formatDate(product.created_at)}</td>
              {(onApprove || onDecline) && (
                <td className="py-4 px-6">
                  {product.status === undefined || product.status === 1 ? (
                    <div className="flex space-x-2">
                      {onApprove && (
                        <button 
                          onClick={() => onApprove(product.id)} 
                          className="bg-green-500 hover:bg-green-600 text-white font-bold py-1 px-2 rounded text-sm"
                        >
                          {t('search.results.approve')}
                        </button>
                      )}
                      {onDecline && (
                        <button 
                          onClick={() => onDecline(product.id)} 
                          className="bg-red-500 hover:bg-red-600 text-white font-bold py-1 px-2 rounded text-sm"
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