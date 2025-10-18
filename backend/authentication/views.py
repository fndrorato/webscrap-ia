# from rest_framework_simplejwt.views import TokenObtainPairView
# from authentication.serializers import CustomTokenObtainPairSerializer


# class CustomTokenObtainPairView(TokenObtainPairView):
#     serializer_class = CustomTokenObtainPairSerializer

from rest_framework_simplejwt.views import TokenObtainPairView
from authentication.serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    View customizada para obter token JWT autenticando contra Oracle
    """
    serializer_class = CustomTokenObtainPairSerializer