import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';

interface UserData {
  firstName: string;
  lastName: string;
  email: string;
  userId: string;
  phone: string;
  photo?: string;
  permissions: string[];
  profilePicture?: string;
}

interface AuthContextType {
  user: UserData | null;
  setUser: React.Dispatch<React.SetStateAction<UserData | null>>;
  login: (userData: UserData, accessToken: string, refreshToken: string) => void;
  logout: () => void;
  updateUser: (userData: Partial<UserData>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserData | null>(null);

  useEffect(() => {
    const storedFirstName = localStorage.getItem('firstName');
    const storedLastName = localStorage.getItem('lastName');
    const storedEmail = localStorage.getItem('email');
    const storedUserId = localStorage.getItem('userId');
    const storedPermissions = localStorage.getItem('permissions');
    const storedPhone = localStorage.getItem('phone');
    const storedPhotoUser = localStorage.getItem('photoUser');

    if (storedFirstName && storedLastName && storedEmail && storedUserId && storedPermissions) {
      try {
        const permissions = JSON.parse(storedPermissions);
        setUser({
          firstName: storedFirstName,
          lastName: storedLastName,
          email: storedEmail,
          userId: storedUserId,
          permissions: permissions,
          phone: storedPhone || '',
          photo: storedPhotoUser || '',
        });
      } catch (e) {
        console.error("Failed to parse permissions from localStorage", e);
        logout(); // Clear invalid data
      }
    }
  }, []);

  const login = (userData: UserData, accessToken: string, refreshToken: string) => {
    console.log(userData);
    localStorage.setItem('accessToken', accessToken);
    localStorage.setItem('refreshToken', refreshToken);
    localStorage.setItem('firstName', userData.firstName);
    localStorage.setItem('lastName', userData.lastName);
    localStorage.setItem('email', userData.email);
    localStorage.setItem('userId', userData.userId);
    localStorage.setItem('permissions', JSON.stringify(userData.permissions));
    localStorage.setItem('phone', userData.phone);
    if (userData.photo) {
      localStorage.setItem('photoUser', userData.photo);
    }
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('firstName');
    localStorage.removeItem('lastName');
    localStorage.removeItem('email');
    localStorage.removeItem('userId');
    localStorage.removeItem('permissions');
    setUser(null);
  };

  const updateUser = (updatedFields: Partial<UserData>) => {
    setUser(prevUser => {
      if (!prevUser) return null;
      const newUser = { ...prevUser, ...updatedFields };
      if (updatedFields.photo !== undefined) {
        localStorage.setItem('photoUser', updatedFields.photo);
      }
      // Add other fields to update in localStorage if needed
      return newUser;
    });
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};