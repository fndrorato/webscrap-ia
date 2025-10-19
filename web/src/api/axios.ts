import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const instance = axios.create({
  baseURL: API_BASE_URL,
  // withCredentials: true, // 🔥 necessário se for usar cookie de CSRF
  headers: {
    'Content-Type': 'application/json',
  },
});


instance.interceptors.request.use(
  (config) => {
    const accessToken = localStorage.getItem('accessToken');
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }

    // Adiciona o CSRF token (se existir no cookie)
    // const csrfToken = getCookie('csrftoken');
    // if (csrfToken) {
    //   config.headers['X-CSRFToken'] = csrfToken;
    // }

    return config;
  },
  (error) => Promise.reject(error)
);


export const loginEndpoint = '/api/v1/auth/token/';
// export const loginEndpoint = '/api/v1/auth/mock-token/';

export default instance;