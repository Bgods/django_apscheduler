import json
import os
import threading
import urllib.request

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models import OuterRef, Subquery, Count, Max, Prefetch
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from ..models import HostConfig, DatabaseConfig, TaskConfig, TaskExecutionLog
from ..scheduler import run_task_now, _get_current_host
from .serializers import (
    HostConfigSerializer, DatabaseConfigSerializer,
    TaskConfigSerializer, TaskExecutionLogSerializer,
    UserSerializer, UserManageSerializer, UserCreateSerializer,
    ChangePasswordSerializer, ResetPasswordSerializer,
    GroupSerializer, PermissionSerializer,
)


class HostConfigViewSet(viewsets.ModelViewSet):
    queryset = HostConfig.objects.all()
    serializer_class = HostConfigSerializer
    search_fields = ['ip', 'label']

    def get_queryset(self):
        qs = super().get_queryset()
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('true', '1'))
        return qs


class DatabaseConfigViewSet(viewsets.ModelViewSet):
    queryset = DatabaseConfig.objects.all()
    serializer_class = DatabaseConfigSerializer

    def get_queryset(self):
        qs = super().get_queryset().annotate(
            task_count=Count('tasks', distinct=True)
        )
        params = self.request.query_params
        search = params.get('search')
        if search:
            qs = qs.filter(label__icontains=search) | qs.filter(host__icontains=search)
        db_type = params.get('db_type')
        if db_type:
            qs = qs.filter(db_type=db_type)
        is_active = params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('true', '1'))
        return qs

    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        data = request.data
        db_type = data.get('db_type', 'mysql')
        host = data.get('host', 'localhost')
        port = int(data.get('port', 3306))
        database = data.get('database', '')
        username = data.get('username', '')
        password = data.get('password', '')

        try:
            if db_type == 'mysql':
                try:
                    import pymysql
                except ImportError:
                    import MySQLdb as pymysql
                conn = pymysql.connect(
                    host=host, port=port, user=username,
                    password=password, database=database, connect_timeout=5,
                )
                conn.close()
            elif db_type == 'postgresql':
                import psycopg2
                conn = psycopg2.connect(
                    host=host, port=port, user=username,
                    password=password, dbname=database, connect_timeout=5,
                )
                conn.close()
            elif db_type == 'sqlite':
                import sqlite3
                if not os.path.isfile(database):
                    return Response({'ok': False, 'error': f'SQLite 文件不存在: {database}'})
                conn = sqlite3.connect(database)
                conn.close()
            else:
                return Response({'ok': False, 'error': f'暂不支持在线测试: {db_type}'})

            return Response({'ok': True, 'message': '连接成功'})
        except Exception as e:
            return Response({'ok': False, 'error': str(e)})


class TaskConfigViewSet(viewsets.ModelViewSet):
    queryset = TaskConfig.objects.all()
    serializer_class = TaskConfigSerializer

    def get_queryset(self):
        # 预查询每个任务最新日志的 ID（非关联子查询，数据库可优化为 Hash Join）
        latest_log_ids = (
            TaskExecutionLog.objects
            .values('task').annotate(latest_id=Max('id'))
            .values('latest_id')
        )
        # Prefetch 仅加载每个任务的最新一条日志
        last_log_prefetch = Prefetch(
            'execution_logs',
            queryset=TaskExecutionLog.objects.filter(id__in=latest_log_ids),
            to_attr='_last_logs',
        )
        qs = (
            TaskConfig.objects
            .select_related('database')
            .prefetch_related('hosts', last_log_prefetch)
        )
        params = self.request.query_params
        is_active = params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ('true', '1'))
        task_type = params.get('task_type')
        if task_type:
            qs = qs.filter(task_type=task_type)
        group = params.get('group')
        if group:
            qs = qs.filter(group=group)
        host = params.get('host')
        if host:
            qs = qs.filter(hosts__ip=host)
        search = params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        database = params.get('database')
        if database:
            qs = qs.filter(database_id=database)
        last_result = params.get('last_result')
        if last_result:
            # 非关联子查询：找出最新日志结果为指定值的任务
            task_ids = (
                TaskExecutionLog.objects
                .filter(id__in=latest_log_ids, result=last_result)
                .values('task_id')
            )
            qs = qs.filter(id__in=task_ids)
        return qs

    @action(detail=False, methods=['get'])
    def options(self, request):
        """轻量接口：仅返回 id + name，供下拉框使用"""
        tasks = list(TaskConfig.objects.values('id', 'name').order_by('name'))
        return Response(tasks)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        config = self.get_object()
        current_host = _get_current_host()
        assigned_ips = list(config.hosts.values_list('ip', flat=True))

        results = []

        # 当前机器在分配列表中（或未指定机器），本地执行
        if not assigned_ips or current_host in assigned_ips:
            threading.Thread(target=run_task_now, args=(config,), daemon=True).start()
            results.append(f'本机({current_host})已触发执行')

        # 向其他所有分配机器发起代理请求
        remote_ips = [ip for ip in assigned_ips if ip != current_host]
        for ip in remote_ips:
            url = f'http://{ip}:{settings.SCHEDULER_API_PORT}/api/tasks/{config.pk}/execute/'
            req_data = json.dumps({}).encode('utf-8')
            req = urllib.request.Request(
                url, data=req_data, method='POST',
                headers={'Content-Type': 'application/json'},
            )
            try:
                urllib.request.urlopen(req, timeout=10)
                results.append(f'已代理到 {ip} 执行')
            except Exception:
                results.append(f'代理到 {ip} 失败(不可达)')

        if not results:
            return Response({'status': 'error', 'message': '所有分配机器不可达'}, status=503)

        return Response({'status': 'ok', 'message': '；'.join(results)})

    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        source = self.get_object()
        new_task = TaskConfig.objects.create(
            name=f'{source.name} (副本)',
            group=source.group,
            task_type=source.task_type,
            project_path=source.project_path,
            executor_path=source.executor_path or '',
            script_path=source.script_path,
            sql_content=source.sql_content,
            cron_expression=source.cron_expression,
            is_active=False,
            timeout_seconds=source.timeout_seconds,
            database=source.database,
        )
        new_task.hosts.set(source.hosts.all())
        serializer = self.get_serializer(new_task)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def groups(self, request):
        # 注意：TaskConfig 有默认 ordering(is_active/id)，会破坏 MySQL 的 DISTINCT 去重，
        # 因此这里显式按 group 排序以覆盖默认排序
        groups = TaskConfig.objects.order_by('group').values_list('group', flat=True).distinct()
        return Response([g for g in groups if g])


class TaskExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TaskExecutionLog.objects.all().select_related('task')
    serializer_class = TaskExecutionLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        task_id = params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        task_name = params.get('task_name')
        if task_name:
            qs = qs.filter(task__name__icontains=task_name)
        group = params.get('group')
        if group:
            qs = qs.filter(task__group=group)
        result = params.get('result')
        if result:
            qs = qs.filter(result=result)
        execution_host = params.get('execution_host')
        if execution_host:
            qs = qs.filter(execution_host=execution_host)
        search = params.get('search')
        if search:
            qs = qs.filter(error_message__icontains=search) | qs.filter(command_text__icontains=search)
        # 列表查询排除大文本字段
        if self.action == 'list':
            qs = qs.defer('output', 'error_message')
        return qs


class AuthViewSet(viewsets.ViewSet):
    """登录认证接口：login / logout / me"""

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        if not username or not password:
            raise AuthenticationFailed('请输入用户名和密码')
        user = authenticate(request, username=username, password=password)
        if user is None:
            raise AuthenticationFailed('用户名或密码错误')
        login(request, user)
        return Response(UserSerializer(user).data)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        logout(request)
        return Response({'detail': '已注销'})

    @action(detail=False, methods=['get'])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """当前用户修改自己的密码"""
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            raise ValidationError({'old_password': '原密码不正确'})
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'detail': '密码修改成功'})

    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        """当前用户修改个人资料（邮箱/姓名）"""
        user = request.user
        for field in ('first_name', 'last_name', 'email'):
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        return Response(UserSerializer(user).data)


class UserManageViewSet(viewsets.ModelViewSet):
    """用户管理（仅管理员）：列表/新增/编辑/删除"""
    permission_classes = [IsAdminUser]
    queryset = get_user_model().objects.all().order_by('id')

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserManageSerializer

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related('groups')
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(username__icontains=search) | qs.filter(first_name__icontains=search)
        return qs

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """管理员重置指定用户密码"""
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'detail': f'已重置用户 {user.username} 的密码'})

    def perform_destroy(self, instance):
        if instance.is_superuser and instance == self.request.user:
            raise ValidationError({'detail': '不能删除当前登录的管理员账号'})
        if instance.is_superuser:
            User = get_user_model()
            if User.objects.filter(is_superuser=True).exclude(pk=instance.pk).count() == 0:
                raise ValidationError({'detail': '系统至少保留一个超级管理员账号'})
        instance.delete()


class GroupViewSet(viewsets.ModelViewSet):
    """用户组管理（仅管理员）：列表/新增/编辑/删除"""
    permission_classes = [IsAdminUser]
    queryset = Group.objects.all().prefetch_related('permissions')
    serializer_class = GroupSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """权限列表（仅管理员，供组管理选择权限）"""
    permission_classes = [IsAdminUser]
    queryset = Permission.objects.select_related('content_type').all().order_by('content_type__app_label', 'codename')
    serializer_class = PermissionSerializer


@api_view(['GET'])
def dashboard_stats(request):
    """仪表盘统计数据（只返回数字，不返回完整对象）"""
    # 任务统计
    total_tasks = TaskConfig.objects.count()
    active_tasks = TaskConfig.objects.filter(is_active=True).count()
    python_tasks = TaskConfig.objects.filter(task_type='python').count()
    sql_tasks = TaskConfig.objects.filter(task_type='sql').count()
    # 分组统计
    group_stats = list(
        TaskConfig.objects.filter(group__isnull=False)
        .exclude(group='')
        .values('group')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    group_stats = [{'name': g['group'], 'count': g['count']} for g in group_stats]
    # 机器/数据库数量
    host_count = HostConfig.objects.count()
    db_count = DatabaseConfig.objects.count()
    # 最近 10 条执行日志（排除大文本）
    recent_logs = list(
        TaskExecutionLog.objects.select_related('task')
        .values(
            'id', 'task__name', 'execution_host', 'result', 'duration', 'start_time',
        )[:10]
    )
    for log in recent_logs:
        log['task_name'] = log.pop('task__name')
        log['result_display'] = dict(TaskExecutionLog.ResultType.choices).get(log['result'], log['result'])
    return Response({
        'total_tasks': total_tasks,
        'active_tasks': active_tasks,
        'python_tasks': python_tasks,
        'sql_tasks': sql_tasks,
        'host_count': host_count,
        'db_count': db_count,
        'group_stats': group_stats,
        'recent_logs': recent_logs,
    })
