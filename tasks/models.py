from django.db import models
from django.utils import timezone


class HostConfig(models.Model):
    """执行机器"""

    ip = models.CharField('IP地址', max_length=100, unique=True)
    label = models.CharField('标签', max_length=200, blank=True, default='')
    is_active = models.BooleanField('启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'host_config'
        verbose_name = '执行机器'
        verbose_name_plural = verbose_name
        ordering = ['ip']

    def __str__(self):
        return self.ip if not self.label else f'{self.label}({self.ip})'


class DatabaseConfig(models.Model):
    """数据库连接配置"""

    DB_TYPES = [
        ('mysql', 'MySQL'),
        ('postgresql', 'PostgreSQL'),
        ('sqlserver', 'SQL Server'),
        ('oracle', 'Oracle'),
        ('sqlite', 'SQLite'),
    ]

    label = models.CharField('配置名称', max_length=200)
    db_type = models.CharField('数据库类型', max_length=50, choices=DB_TYPES, default='mysql')
    host = models.CharField('主机', max_length=200, default='localhost')
    port = models.IntegerField('端口', default=3306)
    database = models.CharField('数据库名', max_length=200)
    username = models.CharField('用户名', max_length=200, blank=True, default='')
    password = models.CharField('密码', max_length=500, blank=True, default='')
    extra_params = models.CharField(
        '额外参数', max_length=500, blank=True, default='',
        help_text='如 charset=utf8mb4 或 sslmode=require',
    )
    is_active = models.BooleanField('启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'db_config'
        verbose_name = '数据库配置'
        verbose_name_plural = verbose_name
        ordering = ['label']

    def __str__(self):
        return f'{self.label} ({self.get_db_type_display()})'


class TaskConfig(models.Model):
    """任务配置模型 —— 支持定时执行 Python / SQL 脚本"""

    TASK_TYPES = [
        ('python', 'Python 脚本'),
        ('sql', 'SQL 脚本'),
    ]

    name = models.CharField('任务名称', max_length=200)
    group = models.CharField(
        '分组', max_length=100, blank=True, default='',
        help_text='任务分组，用于分类管理，如 数据同步、报表生成'
    )
    project_path = models.CharField(
        '项目路径', max_length=500, blank=True, default='',
        help_text='执行脚本所在目录，如 D:/projects/myapp。SQL 任务使用文件路径时必填'
    )
    executor_path = models.CharField(
        '执行器路径', max_length=500, null=True, blank=True, default=None,
        help_text='Python 解释器路径，如 D:/Python39/python.exe，留空则使用系统默认 Python'
    )
    script_path = models.CharField(
        '执行脚本', max_length=500, blank=True, default='',
        help_text='脚本文件名，如 同步数据.py、生成报表.sql 等。SQL 任务可留空改用内联 SQL'
    )
    sql_content = models.TextField(
        'SQL 内容', blank=True, default='',
        help_text='填写要执行的 SQL 语句'
    )
    cron_expression = models.CharField(
        'Cron 表达式', max_length=100, blank=True, default='',
        help_text=(
            '留空=纯手动触发。格式：分 时 日 月 周。'
            '示例：0 9 * * *（每天9点）| 0 9 * * 1（每周一9点）| 0 9 1 * *（每月1号9点）| '
            '*/30 * * * *（每30分钟）| 0 9,18 * * *（每天9点和18点）'
        )
    )
    is_active = models.BooleanField('启用', default=True)
    timeout_seconds = models.PositiveIntegerField(
        '超时时间(秒)', default=0,
        help_text='0 表示不限制。超过此时间任务将被终止并标记为超时',
    )
    hosts = models.ManyToManyField(
        HostConfig,
        blank=True,
        verbose_name='分配机器',
        related_name='tasks',
        help_text='留空表示不限制（任意机器均可执行）',
    )
    task_type = models.CharField(
        '任务类型', max_length=20, choices=TASK_TYPES,
        default='python',
    )
    database = models.ForeignKey(
        DatabaseConfig, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='目标数据库', related_name='tasks',
        help_text='仅 SQL 任务需要选择',
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'task_config'
        verbose_name = '任务配置'
        verbose_name_plural = verbose_name
        ordering = ['-is_active', '-id']

    def save(self, *args, **kwargs):
        """保存前清理路径中的不可见字符，SQL 任务清空路径字段"""
        import re
        pattern = re.compile(r'[\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\ufeff\ufffc]')
        self.project_path = pattern.sub('', self.project_path).strip() if self.project_path else ''
        self.executor_path = pattern.sub('', self.executor_path).strip() if self.executor_path else self.executor_path
        self.script_path = pattern.sub('', self.script_path).strip() if self.script_path else ''

        # SQL 任务：清空路径字段，校验 sql_content
        if self.task_type == 'sql':
            self.project_path = ''
            self.script_path = ''
            if not self.sql_content or not self.sql_content.strip():
                from django.core.exceptions import ValidationError
                raise ValidationError({'sql_content': 'SQL 内容不能为空'})

        super().save(*args, **kwargs)

    def clean(self):
        """校验 cron 表达式及任务配置"""
        if self.cron_expression and self.cron_expression.strip():
            parts = self.cron_expression.strip().split()
            if len(parts) != 5:
                from django.core.exceptions import ValidationError
                raise ValidationError({'cron_expression': 'Cron 表达式需包含 5 个字段: 分 时 日 月 周'})
            minute, hour, dom, month, dow = parts
            from django.core.exceptions import ValidationError
            try:
                self._check_field(minute, 0, 59, '分钟')
                self._check_field(hour, 0, 23, '小时')
                self._check_field(dom, 1, 31, '日期')
                self._check_field(month, 1, 12, '月份')
            except ValidationError:
                raise
            except Exception:
                pass
        if self.task_type == 'sql' and not self.database_id:
            from django.core.exceptions import ValidationError
            raise ValidationError({'database': 'SQL 任务必须选择目标数据库'})

        if self.task_type == 'python':
            if not self.project_path or not self.script_path:
                from django.core.exceptions import ValidationError
                raise ValidationError({'project_path': 'Python 任务必须填写项目路径和执行脚本'})

    @staticmethod
    def _check_field(value, _min, _max, label):
        try:
            v = int(value)
            if v < _min or v > _max:
                from django.core.exceptions import ValidationError
                raise ValidationError({'cron_expression': f'{label}值 {v} 超出范围 [{_min}, {_max}]'})
        except ValueError:
            pass  # 非纯数字跳过

    def __str__(self):
        return f'{self.name}'

    @property
    def cron_description(self):
        """将 cron 表达式转为人类可读描述"""
        if not self.cron_expression or not self.cron_expression.strip():
            return '手动触发'
        parts = self.cron_expression.strip().split()
        if len(parts) != 5:
            return self.cron_expression
        minute, hour, dom, month, dow = parts

        WDAY_MAP = {'0': '日', '1': '一', '2': '二', '3': '三',
                    '4': '四', '5': '五', '6': '六', '7': '日'}

        def _desc_field(val: str, unit: str, wday: bool = False) -> str:
            """将单个 cron 字段转为描述"""
            if val == '*':
                return ''
            parts_list = val.split(',')
            descs = []
            for p in parts_list:
                p = p.strip()
                if p == '*':
                    descs.append('')
                elif p.startswith('*/'):
                    descs.append(f'每{p[2:]}{unit}')
                elif '-' in p:
                    a, b = p.split('-', 1)
                    if wday:
                        a = WDAY_MAP.get(a, a)
                        b = WDAY_MAP.get(b, b)
                    descs.append(f'{a}-{b}{unit}')
                elif wday:
                    descs.append(f'{WDAY_MAP.get(p, p)}')
                else:
                    descs.append(f'{p}{unit}')
            return ','.join(d for d in descs if d)

        # 分钟描述
        min_desc = _desc_field(minute, '分')
        # 小时描述
        hour_desc = _desc_field(hour, '时')
        # 星期描述（特殊：使用全名）
        dow_desc = _desc_field(dow, '', wday=True)
        # 日描述
        dom_desc = _desc_field(dom, '日')
        # 月描述
        month_desc = _desc_field(month, '月')

        # 构建完整描述
        parts_desc = []

        if month != '*':
            parts_desc.append(f'每年{_desc_field(month, "月") or month}')

        if dom != '*':
            parts_desc.append(f'每月{_desc_field(dom, "日") or dom}')
        elif dow != '*' and dom == '*':
            val = _desc_field(dow, '', wday=True)
            if ',' in val and not val.startswith('每'):
                val = '周' + val
            elif val and not val.startswith('每'):
                val = '周' + val
            if val:
                parts_desc.append(val)

        # 时间部分
        time_parts = []
        if hour_desc:
            time_parts.append(hour_desc)
        if min_desc:
            time_parts.append(min_desc)
        elif minute != '*':
            # 具体分钟数后面不需要"分"
            parts_list = minute.split(',')
            has_step = any(p.strip().startswith('*/') for p in parts_list)
            if has_step:
                time_parts.append(_desc_field(minute, '分'))
            else:
                time_parts.append(f'{minute}分')

        time_str = ' '.join(time_parts) if time_parts else ''

        if parts_desc:
            base = parts_desc[0]
            if time_str:
                return f'{base} {time_str}'
            return base

        if time_str:
            return time_str

        if minute.startswith('*/'):
            return f'每{minute[2:]}分钟'

        return self.cron_expression


class TaskExecutionLog(models.Model):
    """任务执行日志"""

    class ResultType(models.TextChoices):
        SUCCESS = 'SUCCESS', '成功'
        FAILED = 'FAILED', '失败'
        TIMEOUT = 'TIMEOUT', '超时'
        INTERRUPTED = 'INTERRUPTED', '中断'
        RUNNING = 'RUNNING', '执行中'

    task = models.ForeignKey(
        TaskConfig, on_delete=models.CASCADE,
        related_name='execution_logs', verbose_name='任务'
    )
    start_time = models.DateTimeField('开始时间', auto_now_add=True)
    end_time = models.DateTimeField('结束时间', null=True, blank=True)
    duration = models.FloatField('执行时长(秒)', null=True, blank=True)
    result = models.CharField(
        '执行结果', max_length=20, choices=ResultType.choices,
        default=ResultType.RUNNING
    )
    return_code = models.BigIntegerField('返回码', null=True, blank=True)
    output = models.TextField('输出内容', blank=True, default='')
    error_message = models.TextField('错误信息', blank=True, default='')
    execution_host = models.CharField('执行机器', max_length=64, blank=True, default='')
    command_text = models.TextField('完整命令', blank=True, default='', help_text='记录实际执行的完整命令行')

    class Meta:
        db_table = 'task_execution_log'
        verbose_name = '执行日志'
        verbose_name_plural = verbose_name
        ordering = ['-start_time']

    def __str__(self):
        return f'{self.task.name}'
