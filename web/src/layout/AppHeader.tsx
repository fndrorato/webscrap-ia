import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';

const AppHeader: React.FC = () => {
  const { t } = useTranslation();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <header className="bg-gray-800 text-white p-4">
      <nav className="container mx-auto flex justify-between items-center">
        <Link to="/" className="text-xl font-bold">
          {t('app.name')}
        </Link>
        <ul className="flex space-x-4">
          <li>
            <Link to="/" className="hover:text-gray-300">
              {t('Home')}
            </Link>
          </li>
          <li>
            <Link to="/approved-items" className="hover:text-gray-300">
              {t('Approved Items')}
            </Link>
          </li>
          <li>
            <button onClick={handleLogout} className="hover:text-gray-300 bg-transparent border-none cursor-pointer text-white">
              {t('Cerrar Sesión')}
            </button>
          </li>
        </ul>
      </nav>
    </header>
  );
};

export default AppHeader;
