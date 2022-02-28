from django.urls import path
from django.conf import settings
from authentication.views.users import UserListCreateAPIView, UserRetrieveUpdateDestroyAPIView 

from django.views.decorators.cache import cache_page
from django.core.cache.backends.base import DEFAULT_TIMEOUT


CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)
AUTHENTICATION_CACHE_KEY = getattr(settings, 'AUTHENTICATION_CACHE_KEY', '')

urlpatterns = [
    path('', cache_page(CACHE_TTL, key_prefix=AUTHENTICATION_CACHE_KEY)(UserListCreateAPIView.as_view()), name="authentication__list"),
    path('<int:pk>/', cache_page(CACHE_TTL, key_prefix=AUTHENTICATION_CACHE_KEY)(UserRetrieveUpdateDestroyAPIView.as_view()), name="authentication__details"),
]