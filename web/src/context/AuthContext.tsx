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
  catalog?: CatalogData;
}

interface Fornecedor {
  nombre: string;
  cod_proveedor: string;
}

interface Marca {
  cod_marca: string;
  descripcion: string;
}

interface Rubro {
  cod_rubro: string;
  descripcion: string;
}

interface Grupo {
  cod_grupo: string;
  cod_rubro: string;
  descripcion: string;
}

interface CatalogData {
  fornecedores: Fornecedor[];
  marcas: Marca[];
  rubros: Rubro[];
  grupos: Grupo[];
  counts: {
    fornecedores: number;
    marcas: number;
    rubros: number;
    grupos: number;
  };
}

interface AuthContextType {
  user: UserData | null;
  setUser: React.Dispatch<React.SetStateAction<UserData | null>>;
  login: (userData: UserData, accessToken: string, refreshToken: string, catalogData?: CatalogData) => void;
  logout: () => void;
  updateUser: (userData: Partial<UserData>) => void;
  catalog: CatalogData | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserData | null>(null);
  const [catalog, setCatalog] = useState<CatalogData | null>(null);

  useEffect(() => {
    const storedFirstName = localStorage.getItem('firstName');
    const storedLastName = localStorage.getItem('lastName');
    const storedEmail = localStorage.getItem('email');
    const storedUserId = localStorage.getItem('userId');
    const storedPermissions = localStorage.getItem('permissions');
    const storedPhone = localStorage.getItem('phone');
    const storedPhotoUser = localStorage.getItem('photoUser');
    const storedCatalog = localStorage.getItem('catalog');

    if (storedFirstName && storedLastName && storedEmail && storedUserId && storedPermissions) {
      try {
        const permissions = JSON.parse(storedPermissions);
        const userData: UserData = {
          firstName: storedFirstName,
          lastName: storedLastName,
          email: storedEmail,
          userId: storedUserId,
          permissions: permissions,
          phone: storedPhone || '',
          photo: storedPhotoUser || '',
        };

        if (storedCatalog) {
          const parsedCatalog = JSON.parse(storedCatalog);
          userData.catalog = parsedCatalog;
          setCatalog(parsedCatalog);
        }
        setUser(userData);
      } catch (e) {
        console.error("Failed to parse data from localStorage", e);
        logout(); // Clear invalid data
      }
    }
  }, []);

  const login = (userData: UserData, accessToken: string, refreshToken: string, catalogData?: CatalogData) => {
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
    if (catalogData) {
      localStorage.setItem('catalog', JSON.stringify(catalogData));
      setCatalog(catalogData);
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
    localStorage.removeItem('catalog');
    setUser(null);
    setCatalog(null);
  };

  const updateUser = (updatedFields: Partial<UserData>) => {
    setUser(prevUser => {
      if (!prevUser) return null;
      const newUser = { ...prevUser, ...updatedFields };
      if (updatedFields.photo !== undefined) {
        localStorage.setItem('photoUser', updatedFields.photo);
      }
      if (updatedFields.catalog !== undefined) {
        localStorage.setItem('catalog', JSON.stringify(updatedFields.catalog));
        setCatalog(updatedFields.catalog);
      }
      // Add other fields to update in localStorage if needed
      return newUser;
    });
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, logout, updateUser, catalog }}>
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