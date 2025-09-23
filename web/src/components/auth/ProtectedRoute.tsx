import React, { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import axios from '../../api/axios';

interface ProtectedRouteProps {
  element?: React.ReactElement; // Make element optional
  redirectPath?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ element, redirectPath = '/signin' }) => {
  const { user, logout, setUser } = useAuth();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const verifyTokenAndLoadUser = async () => {
      if (user) {
        setIsLoading(false);
        return;
      }

      const accessToken = localStorage.getItem('accessToken');
      if (!accessToken) {
        logout();
        setIsLoading(false);
        return;
      }

      try {
        await axios.post('/api/v1/auth/token/verify/', { token: accessToken });
        // If token is valid, try to load user data from localStorage
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          setUser(JSON.parse(storedUser));
        }
      } catch (error) {
        console.error('Token verification failed:', error);
        logout();
      } finally {
        setIsLoading(false);
      }
    };

    verifyTokenAndLoadUser();
  }, [user, logout, setUser]);

  if (isLoading) {
    return <div>Loading...</div>; // Or a more sophisticated loading spinner
  }

  if (!user) {
    return <Navigate to={redirectPath} replace />;
  }

  return element ? element : <Outlet />;
};

export default ProtectedRoute;