from django.urls import path
from .views import (
    RegisterView, LoginView, MeView, ProfileView, 
    StatsView, CustomTokenRefreshView
)

urlpatterns = [
    # Auth
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='auth-token-refresh'),
    path('me/', MeView.as_view(), name='auth-me'),

    # User
    path('users/profile/', ProfileView.as_view(), name='user-profile'),
    path('users/stats/', StatsView.as_view(), name='user-stats'),

]
