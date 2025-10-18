import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import PageMeta from "../../components/common/PageMeta";
import { useState } from "react";
import axios from '../../api/axios';
import { useTranslation } from "react-i18next";
import SearchIcon from '../../icons/SearchIcon';
import SearchResultsTable from '../../components/search/SearchResultsTable';
import ImageModal from '../../components/search/ImageModal';
import LocalizedLoadingOverlay from '../../components/common/LocalizedLoadingOverlay';

// Define interfaces for the API response
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
  price: number; // Add price field
  sku_code: string; // Add sku_code field
  created_at: string; // Changed from scraped_at to created_at
  status?: number; // 0: declined, 1: pending, 2: approved
}

interface SearchResponse {
  database_results: {
    products: Product[];
  };
  success: boolean;
}

export default function Home() {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Product[]>([]);
  const [selectedImages, setSelectedImages] = useState<ProductImage[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleSearch = async () => {
    if (!query) return;
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post<SearchResponse>('/api/v1/products/nissei-search-detailed/', {
        query: query,
        max_results: 2,
        max_detailed: 2,
        max_images: 3
      });
      console.log(response.data);
      if (response.data.success) {
        setResults(response.data.database_results.products);
      } else {
        setError("La búsqueda no tuvo éxito.");
      }
    } catch (err) {
      setError("Ocurrió un error al realizar la búsqueda.");
      console.error('Error fetching search data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleImageClick = (images: ProductImage[]) => {
    setSelectedImages(images);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedImages([]);
  };

  const handleUpdateStatus = async (productId: number, status: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post('/api/v1/products/update-status/', {
        id: productId,
        status: status,
      });

      if (response.status === 200) {
        setResults((prevResults) =>
          prevResults.map((product) =>
            product.id === productId ? { ...product, status: status } : product
          )
        );
      } else {
        setError("Error al actualizar el estado del producto.");
      }
    } catch (err) {
      setError("Ocurrió un error al actualizar el estado del producto.");
      console.error('Error updating product status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = (productId: number) => {
    handleUpdateStatus(productId, 2); // 2 for approved
  };

  const handleDecline = (productId: number) => {
    handleUpdateStatus(productId, 0); // 0 for declined
  };

  return (
    <>
      <PageMeta
        title={t('Hacer búsqueda')}
        description={t('Página de búsqueda de productos')}
      />
      <PageBreadcrumb pageTitle="Búsqueda de Productos" />
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] lg:p-6">

        <div className="space-y-6">
          {/* Search Bar */}
          <div className="hidden lg:block">
            <div className="relative">
              <button className="absolute -translate-y-1/2 left-4 top-1/2 text-black dark:text-white" onClick={handleSearch} disabled={loading}>
                <SearchIcon />
              </button>
              <input
                type="text"
                value={query}
                onChange={(e) => e.target.value === '' ? setQuery('') : setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder={t('search.placeholder')}
                className="dark:bg-dark-900 h-14 w-full rounded-lg border border-gray-200 bg-transparent py-2.5 pl-12 pr-14 text-xl text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-800 dark:bg-gray-900 dark:bg-white/[0.03] dark:text-white/90 dark:placeholder:text-white/30 dark:focus:border-brand-800"
              />

              {/* <button className="absolute right-2.5 top-1/2 inline-flex -translate-y-1/2 items-center gap-0.5 rounded-lg border border-gray-200 bg-gray-50 px-[7px] py-[4.5px] text-xs -tracking-[0.2px] text-gray-500 dark:border-gray-800 dark:bg-white/[0.03] dark:text-gray-400">
                <span> ⌘ </span>
                <span> K </span>
              </button> */}
            </div>
          </div>

          {error && <p className="text-red-500">{t('search.error')}</p>}

          <div className="relative">
            {results.length > 0 && (
              <SearchResultsTable
                results={results} 
                onImageClick={handleImageClick} 
                onApprove={handleApprove} 
                onDecline={handleDecline} 
              />
            )}
            <LocalizedLoadingOverlay isLoading={loading} />
          </div>

          {/* Image Modal */}
          {isModalOpen && <ImageModal images={selectedImages} onClose={handleCloseModal} />}
        </div>
      </div>
    </>
  );
}
