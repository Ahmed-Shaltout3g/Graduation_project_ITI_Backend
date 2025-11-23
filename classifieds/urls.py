from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.static import serve as static_serve
from django.http import Http404
import os
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Classifieds API",
        default_version='v1',
        description="API documentation for the Classifieds project",
        contact=openapi.Contact(email="your_email@example.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Apps
    path('api/', include('apps.users.urls')),
    path('api/', include('apps.products.urls')),
    path('api/', include('apps.payments.urls')),
    path('api/', include('apps.reviews.urls')),
    path('api/', include('apps.chats.urls')),
    path('api/', include('apps.reports.urls')),
    path("api/", include("apps.chatbot.urls")),
    # Swagger
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),  # ✅
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

def _media_serve_case_insensitive(request, path):
    # Normalize path separators
    normalized = os.path.normpath(path).lstrip(os.sep)
    full_path = os.path.join(settings.MEDIA_ROOT, normalized)
    if os.path.exists(full_path):
        return static_serve(request, normalized, document_root=settings.MEDIA_ROOT)

    # Case-insensitive fallback: walk each segment
    parts = normalized.split(os.sep)
    search_root = settings.MEDIA_ROOT
    matched_parts = []
    for part in parts:
        try:
            entries = os.listdir(search_root)
        except FileNotFoundError:
            raise Http404
        match = None
        for e in entries:
            if e.lower() == part.lower():
                match = e
                break
        if not match:
            raise Http404
        matched_parts.append(match)
        search_root = os.path.join(search_root, match)

    found_rel = os.path.join(*matched_parts)
    return static_serve(request, found_rel, document_root=settings.MEDIA_ROOT)


# Serve media in development or when explicitly enabled (useful for testing container-built media)
if settings.DEBUG or os.environ.get('SERVE_MEDIA', 'False') == 'True':
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', _media_serve_case_insensitive),
    ]
