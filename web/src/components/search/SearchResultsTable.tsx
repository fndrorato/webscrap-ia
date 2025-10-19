import React from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';

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
  selectedProveedor?: string;
  selectedMarca?: string;
  selectedRubro?: string;
  selectedGrupo?: string;
}

interface SearchResultsTableProps {
  results: Product[];
  onImageClick: (images: ProductImage[]) => void;
  onApprove?: (productId: number) => void;
  onDecline?: (productId: number) => void;
  onProveedorChange?: (productId: number, proveedor: string) => void;
  onMarcaChange?: (productId: number, marca: string) => void;
  onRubroChange?: (productId: number, rubro: string) => void;
  onGrupoChange?: (productId: number, grupo: string) => void;
}

const SearchResultsTable: React.FC<SearchResultsTableProps> = ({ 
  results, 
  onImageClick, 
  onApprove, 
  onDecline,
  onProveedorChange,
  onMarcaChange,
  onRubroChange,
  onGrupoChange,
}) => {
  const { t } = useTranslation();
  const { catalog } = useAuth();

  // const formatDate = (dateString: string) => {
  //   try {
  //     const date = new Date(dateString);
  //     if (isNaN(date.getTime())) {
  //       console.error("Invalid Date string:", dateString);
  //       return "Fecha inválida";
  //     }
  //     return date.toLocaleString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  //   } catch (e) {
  //     console.error("Error formatting date:", dateString, e);
  //     return "Fecha inválida";
  //   }
  // };

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
            <th className="py-3 px-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400 max-w-sm">{t('search.results.description')}</th>
            <th className="py-3 px-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Proveedor</th>
            <th className="py-3 px-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Marca</th>
            <th className="py-3 px-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Rubro</th>
            <th className="py-3 px-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Grupo</th>
            <th className="py-3 px-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Precio</th>
            <th className="py-3 px-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">Código</th>
            {(onApprove || onDecline) && (
              <th className="py-3 px-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('search.results.actions')}</th>
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
              <td className="py-2 px-2 text-sm text-gray-500 dark:text-gray-400 text-justify max-w-sm">{product.description}</td>
              <td className="py-2 px-2 text-sm text-gray-900 dark:text-white">
                <select
                  value={product.selectedProveedor || ''}
                  onChange={(e) => onProveedorChange && onProveedorChange(product.id, e.target.value)}
                  className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                >
                  <option value="">{t('search.results.select_proveedor')}</option>
                  {catalog?.fornecedores.map((prov) => (
                    <option key={prov.cod_proveedor} value={prov.cod_proveedor}>
                      {prov.nombre}
                    </option>
                  ))}
                </select>
              </td>
              <td className="py-2 px-2 text-sm text-gray-900 dark:text-white">
                <select
                  value={product.selectedMarca || ''}
                  onChange={(e) => onMarcaChange && onMarcaChange(product.id, e.target.value)}
                  className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                >
                  <option value="">{t('search.results.select_marca')}</option>
                  {catalog?.marcas.map((marca) => (
                    <option key={marca.cod_marca} value={marca.cod_marca}>
                      {marca.descripcion}
                    </option>
                  ))}
                </select>
              </td>
              <td className="py-2 px-2 text-sm text-gray-900 dark:text-white">
                <select
                  value={product.selectedRubro || ''}
                  onChange={(e) => onRubroChange && onRubroChange(product.id, e.target.value)}
                  className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                >
                  <option value="">{t('search.results.select_rubro')}</option>
                  {catalog?.rubros.map((rubro) => (
                    <option key={rubro.cod_rubro} value={rubro.cod_rubro}>
                      {rubro.descripcion}
                    </option>
                  ))}
                </select>
              </td>
              <td className="py-2 px-2 text-sm text-gray-900 dark:text-white">
                <select
                  value={product.selectedGrupo || ''}
                  onChange={(e) => onGrupoChange && onGrupoChange(product.id, e.target.value)}
                  className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                  disabled={!product.selectedRubro}
                >
                  <option value="">{t('search.results.select_grupo')}</option>
                  {product.selectedRubro && catalog?.grupos
                    .filter(grupo => grupo.cod_rubro === product.selectedRubro)
                    .map((grupo) => (
                      <option key={grupo.cod_grupo} value={grupo.cod_grupo}>
                        {grupo.descripcion}
                      </option>
                    ))}
                </select>
              </td>
              <td className="py-2 px-2 text-sm text-gray-900 dark:text-white">{formatPrice(product.price)}</td>
              <td className="py-2 px-2 text-sm text-gray-900 dark:text-white">{product.sku_code}</td>
              {(onApprove || onDecline) && (
                <td className="py-2 px-2">
                  {product.status === undefined || product.status === 1 ? (
                    <div className="flex space-x-2">
                      {onApprove && (
                        <button 
                          onClick={() => onApprove(product.id)} 
                          className="text-green-500 hover:text-green-600 p-1 rounded-full"
                          aria-label={t('search.results.approve')}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        </button>
                      )}
                      {onDecline && (
                        <button 
                          onClick={() => onDecline(product.id)} 
                          className="text-red-500 hover:text-red-600 p-1 rounded-full"
                          aria-label={t('search.results.reject')}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
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