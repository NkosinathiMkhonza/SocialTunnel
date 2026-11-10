"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from social_pipeline.views import (
    ActiveUserRegistryView,
    DirectMessagePipelineView,
    alternative_feed_view,
    register_user_view,
)

urlpatterns = [
    # Admin clients open Django's built-in administration page.
    path('admin/', admin.site.urls),

    # Browser clients open the login page and social dashboard.
    path('', TemplateView.as_view(template_name='index.html'), name='home'),

    # API clients obtain an authentication token with username and password.
    path('api/login/', obtain_auth_token, name='api-login'),
    # API clients obtain a JWT access and refresh token pair.
    path(
        'api/token/',
        TokenObtainPairView.as_view(),
        name='token_obtain_pair',
    ),
    # API clients exchange a refresh token for a new access token.
    path(
        'api/token/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh',
    ),

    # API clients request the current sample feed response.
    path(
        'social_pipeline/new-feed/',
        alternative_feed_view,
        name='alternative_feed',
    ),

    # API clients create an account with registration details.
    path('api/register/', register_user_view, name='api_register'),
    # API clients list active accounts other than the requester.
    path(
        'api/users/',
        ActiveUserRegistryView.as_view(),
        name='api_active_users',
    ),
    # Post feature under construction
    # path('api/posts/', posts_view, name='api_posts'),

    # API clients read a conversation or send a direct message.
    path(
        'api/messages/',
        DirectMessagePipelineView.as_view(),
        name='api_messages',
    ),
]
