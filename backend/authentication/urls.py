from django.urls import path
from authentication.views import CustomTokenObtainPairView
from authentication.mock_views import MockLoginView, MockLoginInfoView
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)


urlpatterns = [
    path('auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    path('auth/mock-token/', MockLoginView.as_view(), name='mock_token_obtain'),
    path('auth/mock-info/', MockLoginInfoView.as_view(), name='mock_info'),    
]
