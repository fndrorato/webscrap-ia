import { useEffect } from 'react';

export default function useSessionSocket(onUpdate: (data: any) => void) {
  const baseWs = import.meta.env.VITE_API_BASE_URL?.replace("http", "ws") ?? "ws://whatschannel-backend:8000";   
  
  useEffect(() => {
    // const socket = new WebSocket('ws://127.0.0.1:8000/ws/sessions/');
    const socket = new WebSocket(`${baseWs}/ws/sessions/`);  

    socket.onopen = () => {
      console.log('✅ WebSocket conectado');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('📡 Mensagem recebida via WebSocket:', data);
        onUpdate(data);
      } catch (e) {
        console.error('❌ Erro ao processar WebSocket:', e);
      }
    };

    socket.onerror = (error) => {
      console.error('❌ Erro WebSocket:', error);
    };

    socket.onclose = () => {
      console.log('🔌 WebSocket desconectado');
    };

    return () => {
      socket.close();
    };
  }, [onUpdate]);
}
