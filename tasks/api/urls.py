from django.urls import path
from rest_framework.routers import DefaultRouter
from .viewsets import (
    HostConfigViewSet, DatabaseConfigViewSet,
    TaskConfigViewSet, TaskExecutionLogViewSet,
    AuthViewSet, UserManageViewSet, GroupViewSet, PermissionViewSet,
    dashboard_stats,
)

router = DefaultRouter()
router.register(r'hosts', HostConfigViewSet)
router.register(r'databases', DatabaseConfigViewSet)
router.register(r'tasks', TaskConfigViewSet)
router.register(r'logs', TaskExecutionLogViewSet)
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserManageViewSet, basename='users')
router.register(r'groups', GroupViewSet, basename='groups')
router.register(r'permissions', PermissionViewSet, basename='permissions')

urlpatterns = router.urls + [
    path('dashboard/', dashboard_stats, name='dashboard-stats'),
]
