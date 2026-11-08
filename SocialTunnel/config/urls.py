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
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from social_pipeline.views import alternative_feed_view, messages_view, register_user_view

urlpatterns = [
    # /admin/ opens Django's built-in administration page.
    path('admin/', admin.site.urls),

    # / serves the login page and the social dashboard.
    path('', TemplateView.as_view(template_name='index.html'), name='home'),

    # Login with a username and password to receive JWT tokens; refresh gets a new access token.
    path('api/login/', obtain_auth_token, name='api-login'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # /social_pipeline/new-feed/ returns the current sample feed response.
    path('social_pipeline/new-feed/', alternative_feed_view, name='alternative_feed'),

    # /api/register/ creates an account.
    path('api/register/', register_user_view, name='api_register'),
    # Post feature under construction
    # path('api/posts/', posts_view, name='api_posts'),

    # /api/messages/ reads a conversation with GET and sends a message with POST.
    path('api/messages/', messages_view, name='api_messages'),
]
