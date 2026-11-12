from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
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
    path("admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "social_pipeline/new-feed/",
        alternative_feed_view,
        name="alternative_feed",
    ),
    path("api/register/", register_user_view, name="api_register"),
    path(
        "api/users/",
        ActiveUserRegistryView.as_view(),
        name="api_active_users",
    ),
    path(
        "api/messages/",
        DirectMessagePipelineView.as_view(),
        name="api_messages",
    ),
]
