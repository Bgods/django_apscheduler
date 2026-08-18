from django.urls import path, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from tasks.views import spa_view


# 配置路由：新方案以 /app/ SPA 与 /api/v2/ DRF 接口为主
urlpatterns = [
    path('api/v2/', include('tasks.api.urls')),
    path('api/', include('tasks.urls_api')),
    path('app/', spa_view, name='spa'),
    path('app/<path:path>', spa_view, name='spa-catch-all'),
]

urlpatterns += staticfiles_urlpatterns()