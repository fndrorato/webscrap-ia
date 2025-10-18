import React from 'react';

interface LocalizedLoadingOverlayProps {
  isLoading: boolean;
  className?: string;
}

const LocalizedLoadingOverlay: React.FC<LocalizedLoadingOverlayProps> = ({ isLoading, className = '' }) => {
  if (!isLoading) return null;

  return (
    <div className={`absolute inset-0 flex items-center justify-center bg-white/70 dark:bg-gray-900/70 z-10 ${className}`}>
      <div className="flex flex-col items-center">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-300 border-t-brand-500"></div>
      </div>
    </div>
  );
};

export default LocalizedLoadingOverlay;