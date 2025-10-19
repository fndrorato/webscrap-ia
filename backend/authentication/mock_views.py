"""
Views mock para desenvolvimento e testes do frontend
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class MockLoginView(APIView):
    """
    View mock para login - retorna dados fake para desenvolvimento do frontend
    
    Aceita qualquer username/password e retorna um JSON com dados simulados
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username', 'demo')
        password = request.data.get('password', 'demo')
        
        logger.info(f"🎭 Mock Login: username={username}")
        
        # Validações básicas
        if not username or not password:
            return Response(
                {'detail': 'Usuário e senha são obrigatórios.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Criar ou pegar usuário fake
        user, created = User.objects.get_or_create(
            username=username.lower(),
            defaults={
                'is_active': True,
                'is_staff': False,
            }
        )
        
        # Gerar tokens JWT reais
        refresh = RefreshToken.for_user(user)
        
        # Dados FAKE de catálogo
        mock_data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'is_staff': user.is_staff,
                'is_active': user.is_active,
            },
            'catalog': {
                'fornecedores': [
                    {'cod_proveedor': 'F001', 'nombre': 'FORNECEDOR ALPHA LTDA'},
                    {'cod_proveedor': 'F002', 'nombre': 'DISTRIBUIDORA BETA S.A.'},
                    {'cod_proveedor': 'F003', 'nombre': 'COMERCIAL GAMMA'},
                    {'cod_proveedor': 'F004', 'nombre': 'IMPORTADORA DELTA'},
                    {'cod_proveedor': 'F005', 'nombre': 'EPSILON TRADING'},
                    {'cod_proveedor': 'F006', 'nombre': 'ZETA DISTRIBUIDORES'},
                    {'cod_proveedor': 'F007', 'nombre': 'ETA COMERCIO'},
                    {'cod_proveedor': 'F008', 'nombre': 'THETA IMPORTACIONES'},
                ],
                'marcas': [
                    {'cod_marca': 'M001', 'descripcion': 'SAMSUNG'},
                    {'cod_marca': 'M002', 'descripcion': 'LG'},
                    {'cod_marca': 'M003', 'descripcion': 'SONY'},
                    {'cod_marca': 'M004', 'descripcion': 'PHILIPS'},
                    {'cod_marca': 'M005', 'descripcion': 'PANASONIC'},
                    {'cod_marca': 'M006', 'descripcion': 'ELECTROLUX'},
                    {'cod_marca': 'M007', 'descripcion': 'BRASTEMP'},
                    {'cod_marca': 'M008', 'descripcion': 'CONSUL'},
                    {'cod_marca': 'M009', 'descripcion': 'WHIRLPOOL'},
                    {'cod_marca': 'M010', 'descripcion': 'BOSCH'},
                ],
                'rubros': [
                    {'cod_rubro': 'R001', 'descripcion': 'ELECTRODOMÉSTICOS'},
                    {'cod_rubro': 'R002', 'descripcion': 'ELECTRÓNICOS'},
                    {'cod_rubro': 'R003', 'descripcion': 'INFORMÁTICA'},
                    {'cod_rubro': 'R004', 'descripcion': 'TELECOMUNICACIONES'},
                    {'cod_rubro': 'R005', 'descripcion': 'LÍNEA BLANCA'},
                    {'cod_rubro': 'R006', 'descripcion': 'AUDIO Y VIDEO'},
                    {'cod_rubro': 'R007', 'descripcion': 'CLIMATIZACIÓN'},
                ],
                'grupos': [
                    {'cod_grupo': 'G001', 'cod_rubro': 'R001', 'descripcion': 'REFRIGERADORES'},
                    {'cod_grupo': 'G002', 'cod_rubro': 'R001', 'descripcion': 'LAVADORAS'},
                    {'cod_grupo': 'G003', 'cod_rubro': 'R001', 'descripcion': 'COCINAS'},
                    {'cod_grupo': 'G004', 'cod_rubro': 'R002', 'descripcion': 'TELEVISORES'},
                    {'cod_grupo': 'G005', 'cod_rubro': 'R002', 'descripcion': 'EQUIPOS DE SONIDO'},
                    {'cod_grupo': 'G006', 'cod_rubro': 'R003', 'descripcion': 'NOTEBOOKS'},
                    {'cod_grupo': 'G007', 'cod_rubro': 'R003', 'descripcion': 'COMPUTADORAS'},
                    {'cod_grupo': 'G008', 'cod_rubro': 'R003', 'descripcion': 'IMPRESORAS'},
                    {'cod_grupo': 'G009', 'cod_rubro': 'R004', 'descripcion': 'SMARTPHONES'},
                    {'cod_grupo': 'G010', 'cod_rubro': 'R004', 'descripcion': 'TABLETS'},
                    {'cod_grupo': 'G011', 'cod_rubro': 'R005', 'descripcion': 'HELADERAS'},
                    {'cod_grupo': 'G012', 'cod_rubro': 'R005', 'descripcion': 'FREEZERS'},
                    {'cod_grupo': 'G013', 'cod_rubro': 'R006', 'descripcion': 'HOME THEATER'},
                    {'cod_grupo': 'G014', 'cod_rubro': 'R007', 'descripcion': 'AIRE ACONDICIONADO'},
                    {'cod_grupo': 'G015', 'cod_rubro': 'R007', 'descripcion': 'VENTILADORES'},
                ],
                'counts': {
                    'fornecedores': 8,
                    'marcas': 10,
                    'rubros': 7,
                    'grupos': 15,
                }
            }
        }
        
        logger.info(f"✅ Mock Login bem-sucedido: {username}")
        
        return Response(mock_data, status=status.HTTP_200_OK)


class MockLoginInfoView(APIView):
    """
    Endpoint informativo sobre o mock login
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'message': 'Mock Login Endpoint - Para desenvolvimento apenas',
            'endpoint': '/api/auth/mock-token/',
            'method': 'POST',
            'credentials': 'Aceita qualquer username/password',
            'example': {
                'username': 'demo',
                'password': 'demo123'
            },
            'response': 'Retorna tokens JWT válidos + dados fake de catálogo',
            'warning': '⚠️ Não usar em produção! Desabilitar antes do deploy.'
        })