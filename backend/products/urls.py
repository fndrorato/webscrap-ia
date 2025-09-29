from . import views
from django.urls import path
from products.views import (
    ProductViewSet,
    nissei_search_fixed,
    nissei_search_detailed,
    UpdateProductStatusView,
    ProductByStatusView,
)


urlpatterns = [
    # path('nissei-search/', ProductViewSet.as_view({'post': 'nissei_search'}), name='nissei_search'),
    # path('nissei-search-fixed/', views.nissei_search_fixed, name='nissei_search_fixed'),
    path('nissei-search-detailed/', views.nissei_search_detailed, name='nissei_search_detailed'),
    path("update-status/", UpdateProductStatusView.as_view(), name="update-product-status"),
    path("status/<int:status_code>/", ProductByStatusView.as_view(), name="products-by-status"),
]
