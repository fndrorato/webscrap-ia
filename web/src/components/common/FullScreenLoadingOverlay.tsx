import React from 'react';

interface FullScreenLoadingOverlayProps {
  isLoading: boolean;
}

const FullScreenLoadingOverlay: React.FC<FullScreenLoadingOverlayProps> = ({ isLoading }) => {
  if (!isLoading) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black bg-opacity-50 dark:bg-opacity-75">
      <div className="flex flex-col items-center justify-center p-5">
        <div className="w-16 h-16 border-4 border-current border-t-transparent rounded-full animate-spin ease-linear text-blue-500 dark:text-brand-500"></div>
        <p className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">Cargando...</p>
      </div>
    </div>
  );
};

export default FullScreenLoadingOverlay;