# from django.contrib.auth.models import Permission
# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from users.models import CustomUser


# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     @classmethod
#     def get_token(cls, user):
#         token = super().get_token(user)
#         # Adiciona campos customizados ao token (opcional)
#         token['first_name'] = user.first_name
#         token['last_name'] = user.last_name
#         token['user_id'] = user.id
#         return token

#     def validate(self, attrs):
#         data = super().validate(attrs)

#         # Adiciona campos customizados à resposta
#         user = self.user
#         data['first_name'] = user.first_name
#         data['last_name'] = user.last_name
#         data['user_id'] = user.id
      
#         # Pegando permissões via grupos
#         permissions = Permission.objects.filter(group__user=user).values_list('codename', flat=True).distinct()
#         data['permissions'] = list(permissions)

#         return data
# """
# Serializer customizado para autenticação JWT com Oracle
# """
# from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
# from rest_framework import serializers
# from django.contrib.auth import authenticate


# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     """
#     Serializer customizado que autentica usuários via Oracle Database
#     """
    
#     username_field = 'username'
    
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Remove validadores padrão de senha
#         self.fields['password'].required = True
        
#     def validate(self, attrs):
#         """
#         Valida as credenciais do usuário contra o Oracle Database
#         """
#         username = attrs.get('username')
#         password = attrs.get('password')
        
#         if not username or not password:
#             raise serializers.ValidationError({
#                 'detail': 'Usuário e senha são obrigatórios.'
#             })
        
#         # Autentica usando o backend Oracle customizado
#         user = authenticate(
#             request=self.context.get('request'),
#             username=username,
#             password=password
#         )
        
#         if user is None:
#             raise serializers.ValidationError({
#                 'detail': 'Credenciais inválidas ou conta Oracle bloqueada.'
#             })
        
#         if not user.is_active:
#             raise serializers.ValidationError({
#                 'detail': 'Conta de usuário desativada.'
#             })
        
#         # Gera os tokens JWT
#         refresh = self.get_token(user)
        
#         data = {
#             'refresh': str(refresh),
#             'access': str(refresh.access_token),
#             'username': user.username,
#         }
        
#         return data
    
#     @classmethod
#     def get_token(cls, user):
#         """
#         Adiciona claims customizados ao token
#         """
#         token = super().get_token(user)
        
#         # Adicionar informações customizadas ao token (opcional)
#         token['username'] = user.username
#         # token['email'] = user.email  # se você tiver
        
#         return token
"""
Serializer customizado para autenticação JWT com Oracle
"""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate
from authentication.oracle_queries import fetch_all_catalog_data
import logging

logger = logging.getLogger(__name__)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer customizado que autentica usuários via Oracle Database
    e retorna dados adicionais de catálogo
    """
    
    username_field = 'username'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove validadores padrão de senha
        self.fields['password'].required = True
        
    def validate(self, attrs):
        """
        Valida as credenciais do usuário contra o Oracle Database
        e busca dados adicionais de catálogo
        """
        username = attrs.get('username')
        password = attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidationError({
                'detail': 'Usuário e senha são obrigatórios.'
            })
        
        logger.info(f"🔐 Tentando autenticar usuário: {username}")
        
        # Autentica usando o backend Oracle customizado
        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )
        
        if user is None:
            logger.warning(f"❌ Autenticação falhou para usuário: {username}")
            raise serializers.ValidationError({
                'detail': 'Credenciais inválidas ou conta Oracle bloqueada.'
            })
        
        if not user.is_active:
            logger.warning(f"⚠️  Usuário inativo: {username}")
            raise serializers.ValidationError({
                'detail': 'Conta de usuário desativada.'
            })
        
        logger.info(f"✅ Usuário autenticado com sucesso: {username}")
        
        # Gera os tokens JWT
        refresh = self.get_token(user)
        
        # Buscar dados de catálogo do Oracle
        logger.info(f"📊 Buscando dados de catálogo do Oracle...")
        catalog_data = fetch_all_catalog_data(username, password)
        
        # Montar resposta
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'is_staff': user.is_staff,
                'is_active': user.is_active,
            }
        }
        
        # Adicionar dados de catálogo se foram buscados com sucesso
        if catalog_data:
            data['catalog'] = catalog_data
            logger.info(f"✅ Dados de catálogo incluídos no response")
        else:
            logger.warning(f"⚠️  Não foi possível buscar dados de catálogo")
            # Retornar estrutura vazia para não quebrar o frontend
            data['catalog'] = {
                'fornecedores': [],
                'marcas': [],
                'rubros': [],
                'grupos': [],
                'counts': {
                    'fornecedores': 0,
                    'marcas': 0,
                    'rubros': 0,
                    'grupos': 0,
                }
            }
        
        return data
    
    @classmethod
    def get_token(cls, user):
        """
        Adiciona claims customizados ao token
        """
        token = super().get_token(user)
        
        # Adicionar informações customizadas ao token (opcional)
        token['username'] = user.username
        token['is_staff'] = user.is_staff
        
        return token