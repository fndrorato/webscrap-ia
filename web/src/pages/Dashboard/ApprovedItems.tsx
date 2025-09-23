import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import PageMeta from "../../components/common/PageMeta";
import { useState, useEffect } from "react";
import axios from '../../api/axios';
import { useTranslation } from "react-i18next";
import SearchResultsTable from '../../components/search/SearchResultsTable';
import ImageModal from '../../components/search/ImageModal';
import FullScreenLoadingOverlay from '../../components/common/FullScreenLoadingOverlay';

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
  status?: number; // 0: declined, 1: pending, 2: approved
}

interface ProductsResponse {
  products: Product[];
}

export default function ApprovedItems() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<Product[]>([]);
  const [selectedImages, setSelectedImages] = useState<ProductImage[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    const fetchApprovedProducts = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await axios.get<ProductsResponse>('/api/v1/products/status/2/');
        setResults(response.data.products);
      } catch (err) {
        setError("Ocurrió un error al cargar los productos aprobados.");
        console.error('Error fetching approved products:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchApprovedProducts();
  }, []);

  const handleImageClick = (images: ProductImage[]) => {
    setSelectedImages(images);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedImages([]);
  };

  return (
    <>
      <PageMeta
        title={t('Artículos confirmados')}
        description={t('Lista de productos aprobados')}
      />
      <PageBreadcrumb pageTitle="Artículos confirmados" />
      <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] lg:p-6">
        <div className="space-y-6">
          {loading && <p>{t('search.loading')}</p>}
          {error && <p className="text-red-500">{t('search.error')}</p>}

          {results.length > 0 && (
            <SearchResultsTable
              results={results} 
              onImageClick={handleImageClick} 
            />
          )}

          {/* Image Modal */}
          {isModalOpen && <ImageModal images={selectedImages} onClose={handleCloseModal} />}
        </div>
      </div>
      <FullScreenLoadingOverlay isLoading={loading} />
    </>
  );
}