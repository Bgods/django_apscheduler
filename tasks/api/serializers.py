import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils import timezone
from rest_framework import serializers
from ..models import HostConfig, DatabaseConfig, TaskConfig, TaskExecutionLog


class UserSerializer(serializers.ModelSerializer):
    """当前登录用户信息序列化"""

    class Meta:
        model = get_user_model()
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'is_staff', 'is_superuser', 'is_active',
        ]


class UserManageSerializer(serializers.ModelSerializer):
    """用户管理序列化：管理员查看/编辑用户（含组）"""

    groups_display = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')
    last_login = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M')

    class Meta:
        model = get_user_model()
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'is_staff', 'is_superuser', 'is_active',
            'groups', 'groups_display', 'date_joined', 'last_login',
        ]

    def get_groups_display(self, obj):
        return [g.name for g in obj.groups.all()]


class UserCreateSerializer(UserManageSerializer):
    """创建用户：额外接收密码"""

    password = serializers.CharField(write_only=True, required=True, min_length=6)

    class Meta(UserManageSerializer.Meta):
        fields = UserManageSerializer.Meta.fields + ['password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        groups = validated_data.pop('groups', [])
        user = get_user_model()(**validated_data)
        user.set_password(password)
        user.save()
        if groups:
            user.groups.set(groups)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """当前用户修改自己的密码"""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': '两次输入的新密码不一致'})
        return data


class ResetPasswordSerializer(serializers.Serializer):
    """管理员重置指定用户密码"""

    new_password = serializers.CharField(required=True, min_length=6)


class GroupSerializer(serializers.ModelSerializer):
    """用户组管理序列化"""

    permissions_display = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'permissions_display']

    def get_permissions_display(self, obj):
        return [f'{p.name}' for p in obj.permissions.all()[:20]]


class PermissionSerializer(serializers.ModelSerializer):
    """权限列表序列化（供组管理选择）"""

    content_type = serializers.CharField(source='content_type.app_label', read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']


class HostConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostConfig
        fields = '__all__'


class DatabaseConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatabaseConfig
        fields = '__all__'

    def get_fields(self):
        fields = super().get_fields()
        fields['task_count'] = serializers.IntegerField(read_only=True, default=0)
        return fields


class TaskConfigSerializer(serializers.ModelSerializer):
    cron_description = serializers.ReadOnlyField()
    host_ids = serializers.PrimaryKeyRelatedField(
        queryset=HostConfig.objects.all(), many=True,
        required=False, source='hosts',
    )
    hosts_display = serializers.SerializerMethodField()
    script_display = serializers.SerializerMethodField()
    next_runs = serializers.SerializerMethodField()
    last_execution = serializers.SerializerMethodField()

    class Meta:
        model = TaskConfig
        fields = [
            'id', 'name', 'group', 'task_type', 'is_active',
            'project_path', 'executor_path', 'script_path', 'script_args',
            'sql_content', 'cron_expression', 'cron_description',
            'timeout_seconds', 'skip_if_running', 'hosts', 'host_ids', 'hosts_display',
            'database', 'created_at', 'updated_at',
            'script_display', 'next_runs', 'last_execution',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_hosts_display(self, obj):
        hosts = obj.hosts.all()
        if not hosts:
            return '* (任意机器)'
        return ', '.join(h.ip for h in hosts)

    def get_script_display(self, obj):
        if obj.task_type == 'sql':
            if obj.database_id:
                return f'[{obj.database.get_db_type_display()}] {obj.database.label} → 内联SQL[点击查看]'
            return '内联SQL[点击查看]'
        path = os.path.join(obj.project_path, obj.script_path) if obj.script_path else obj.project_path
        return path

    def get_next_runs(self, obj):
        if not obj.is_active:
            return '未启用计划'
        parts = (obj.cron_expression or '').strip().split()
        if len(parts) != 5:
            return '-'
        try:
            from apscheduler.triggers.cron import CronTrigger

            def _convert(v):
                return str((int(v) - 1) % 7)

            minute, hour, dom, month, dow = parts
            if '/' in dow and not dow.startswith('*/'):
                prefix, step = dow.split('/', 1)
                dow = f'{_convert(prefix)}/{step}'
            elif ',' in dow:
                dow = ','.join(str((int(x) - 1) % 7) for x in dow.split(','))
            elif '-' in dow:
                lo, hi = dow.split('-', 1)
                dow = f'{_convert(lo)}-{_convert(hi)}'
            elif dow != '*':
                dow = _convert(dow)

            trigger = CronTrigger(
                minute=minute, hour=hour, day=dom,
                month=month, day_of_week=dow,
                timezone='Asia/Shanghai',
            )
            now = timezone.now()
            next_t = trigger.get_next_fire_time(None, now)
            times = []
            for _ in range(3):
                if next_t is None:
                    break
                times.append(timezone.localtime(next_t).strftime('%m-%d %H:%M'))
                next_t = trigger.get_next_fire_time(next_t, next_t)
            return times if times else '无计划'
        except Exception:
            return '-'

    def get_last_execution(self, obj):
        # 直接通过 last_execution_log FK 获取（viewsets.get_queryset 已 select_related 预加载）
        log = obj.last_execution_log
        if not log:
            return None
        return {
            'start_time': timezone.localtime(log.start_time).strftime('%Y-%m-%d %H:%M'),
            'result': log.result,
            'result_display': log.get_result_display(),
            'duration': round(log.duration, 2) if log.duration else None,
        }

    def validate(self, data):
        task_type = data.get('task_type', getattr(self.instance, 'task_type', 'python'))
        if task_type == 'sql':
            sql_content = data.get('sql_content', getattr(self.instance, 'sql_content', ''))
            if not sql_content or not sql_content.strip():
                raise serializers.ValidationError({'sql_content': 'SQL 内容不能为空'})
        return data


class TaskExecutionLogSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source='task.name', read_only=True)
    result_display = serializers.CharField(source='get_result_display', read_only=True)

    class Meta:
        model = TaskExecutionLog
        fields = [
            'id', 'task', 'task_name', 'start_time', 'end_time',
            'duration', 'result', 'result_display', 'return_code',
            'output', 'error_message', 'execution_host', 'command_text',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # 列表接口排除大文本字段，只在详情页返回
        view = self.context.get('view')
        if view and view.action == 'list':
            data.pop('output', None)
            data.pop('error_message', None)
        return data
