import json
import locale
import logging
import os
import re
import sys
import socket
import subprocess
import tempfile

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.db.models import Exists, OuterRef
from django.utils import timezone
from django_apscheduler.jobstores import DjangoJobStore

from .models import DatabaseConfig, HostConfig, TaskConfig, TaskExecutionLog

logger = logging.getLogger('tasks')

scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
scheduler.add_jobstore(DjangoJobStore(), "default")
scheduler.add_jobstore(MemoryJobStore(), "tasks")  # 自定义任务用内存存储，避免多机竞争

# 屏蔽"跳过"警告日志（任务仍在运行时跳过本次触发）
logging.getLogger('apscheduler.executors.default').setLevel(logging.ERROR)
logging.getLogger('apscheduler.scheduler').setLevel(logging.ERROR)
# 屏蔽内存任务（tasks jobstore）在 django_apscheduler 中找不到 job 的警告
logging.getLogger('django_apscheduler.jobstores').setLevel(logging.ERROR)


def _get_current_host() -> str:
    """获取当前机器的局域网 IP"""
    host = getattr(settings, 'SCHEDULER_HOST', '').strip()
    if host:
        return host
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def build_job_id(config: TaskConfig) -> str:
    return f'task_{config.id}'


def _clean_path(path: str) -> str:
    """清理路径中的不可见 Unicode 字符（如 LRE/RLE/PDF 等）"""
    import re
    # 移除常见不可见控制字符：LRE‪ RLE‫ PDF‬ LRO‭ RLO‮ 等
    return re.sub(r'[\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\ufeff\ufffc]', '', path).strip()


def _get_default_python() -> str:
    """获取全局 Python 解释器路径"""
    if hasattr(sys, 'real_prefix'):
        # virtualenv
        return os.path.join(sys.real_prefix, 'python.exe')
    if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
        # venv
        return os.path.join(sys.base_prefix, 'python.exe')
    return sys.executable


def _convert_dow(dow: str) -> str:
    """将标准 cron 星期值（0=周日）转换为 APScheduler 格式（0=周一）"""
    if dow == '*':
        return dow

    def _convert_val(v: str) -> str:
        return str((int(v) - 1) % 7)

    # 处理 */N
    if '/' in dow:
        prefix, step = dow.split('/', 1)
        if prefix == '*':
            return dow
        return f'{_convert_val(prefix)}/{step}'

    # 处理逗号分隔
    if ',' in dow:
        return ','.join(_convert_dow(p) for p in dow.split(','))

    # 处理范围 a-b
    if '-' in dow:
        lo, hi = dow.split('-', 1)
        return f'{_convert_val(lo)}-{_convert_val(hi)}'

    # 单个值
    return _convert_val(dow)


def _get_cmd_and_cwd(config: TaskConfig):
    """根据任务配置拼装执行命令和工作目录"""
    cwd = _clean_path(config.project_path) or str(settings.BASE_DIR)
    executor = _clean_path(config.executor_path) if config.executor_path else ''
    script = _clean_path(config.script_path)

    # 脚本路径：如果是相对路径则拼接 cwd
    if not os.path.isabs(script):
        script = os.path.join(cwd, script)

    py = executor or _get_default_python()
    cmd = [py, script]

    return cmd, cwd


def execute_script(config: TaskConfig, force: bool = False) -> TaskExecutionLog:
    """执行脚本并记录日志。
    
    force=True 时跳过主机匹配检查（用于跨机 API 调用）。
    """
    # 任务可能在调度期间被删除，捕获 DoesNotExist 并清理残留 job
    try:
        config.refresh_from_db()
    except TaskConfig.DoesNotExist:
        logger.info(f'任务已被删除，从调度器移除残留 job: task_{config.pk}')
        try:
            scheduler.remove_job(f'task_{config.id}', jobstore='tasks')
        except Exception:
            pass
        return None

    current_host = _get_current_host()

    # 多机调度：未分配主机（任意）或当前机器在分配列表中才执行
    has_hosts = config.hosts.exists()
    if not force and has_hosts and not config.hosts.filter(ip=current_host).exists():
        assigned_ips = list(config.hosts.values_list('ip', flat=True))
        return None

    command_text = ''
    if config.task_type == 'sql':
        command_text = f'[{config.database.get_db_type_display()}] {config.database.label} → [内联SQL]' if config.database_id else f'[SQL] [内联SQL]'
    else:
        cmd, cwd = _get_cmd_and_cwd(config)
        command_text = ' '.join(cmd)

    log = TaskExecutionLog.objects.create(
        task=config,
        start_time=timezone.now(),
        result=TaskExecutionLog.ResultType.RUNNING,
        execution_host=current_host,
        command_text=command_text,
    )

    try:
        if config.task_type == 'sql':
            _execute_sql(config, log)
        else:
            _execute_python(config, log)
    except subprocess.TimeoutExpired:
        log.end_time = timezone.now()
        log.duration = (log.end_time - log.start_time).total_seconds()
        log.result = TaskExecutionLog.ResultType.TIMEOUT
        log.error_message = f'任务执行超时（>{config.timeout_seconds}秒）'
    except Exception as e:
        log.end_time = timezone.now()
        log.duration = (log.end_time - log.start_time).total_seconds()
        log.result = TaskExecutionLog.ResultType.FAILED
        log.error_message = str(e)

    log.save()
    return log


def _execute_python(config: TaskConfig, log: TaskExecutionLog):
    """通过 subprocess 执行 Python 脚本"""
    cmd, cwd = _get_cmd_and_cwd(config)

    start = timezone.now()
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    timeout = config.timeout_seconds or None
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        _ = process.communicate()  # 清理僵尸进程
        raise
    end = timezone.now()

    log.end_time = end
    log.duration = (end - start).total_seconds()
    log.return_code = process.returncode
    encoding = locale.getpreferredencoding(do_setlocale=False)
    log.output = stdout.decode(encoding, errors='replace')[-5000:]

    if process.returncode == 0:
        log.result = TaskExecutionLog.ResultType.SUCCESS
    else:
        log.result = TaskExecutionLog.ResultType.FAILED
        log.error_message = stderr.decode(encoding, errors='replace')[-2000:]


def _execute_sql(config: TaskConfig, log: TaskExecutionLog):
    """通过 subprocess + sql_runner 执行 SQL 脚本。
    
    sql_content 在 save() 时已从文件读取（文件模式）或直接填写（内联模式），
    此处统一使用 sql_content 写入临时文件执行。
    """
    db = config.database
    if not db:
        log.result = TaskExecutionLog.ResultType.FAILED
        log.error_message = 'SQL 任务未配置目标数据库'
        return

    if not config.sql_content or not config.sql_content.strip():
        log.result = TaskExecutionLog.ResultType.FAILED
        log.error_message = 'SQL 内容为空，请检查任务配置'
        return

    sql_tmp_path = None
    cfg_path = None
    try:
        # 将 sql_content 写入临时文件
        sql_tmp = tempfile.NamedTemporaryFile(
            mode='w', suffix='.sql', delete=False, encoding='utf-8'
        )
        sql_tmp.write(config.sql_content)
        sql_tmp.close()
        sql_tmp_path = sql_tmp.name

        cfg = {
            'db_type': db.db_type,
            'host': db.host,
            'port': db.port,
            'database': db.database,
            'username': db.username,
            'password': db.password,
            'extra_params': db.extra_params,
            'script_path': sql_tmp_path,
        }

        # 写入临时 JSON（避免密码出现在进程列表中）
        cfg_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
        json.dump(cfg, cfg_file)
        cfg_path = cfg_file.name
        cfg_file.close()

        py = sys.executable  # sql_runner 依赖项目 venv 中的 sqlparse
        runner_path = os.path.join(os.path.dirname(__file__), 'sql_runner.py')
        cmd = [py, runner_path, cfg_path]

        start = timezone.now()
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        timeout = config.timeout_seconds or None
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            _ = process.communicate()
            raise
        end = timezone.now()

        log.end_time = end
        log.duration = (end - start).total_seconds()
        log.return_code = process.returncode
        encoding = locale.getpreferredencoding(do_setlocale=False)
        log.output = stdout.decode(encoding, errors='replace')[-5000:]

        if process.returncode == 0:
            log.result = TaskExecutionLog.ResultType.SUCCESS
        else:
            log.result = TaskExecutionLog.ResultType.FAILED
            log.error_message = stderr.decode(encoding, errors='replace')[-2000:]
    finally:
        for path in (cfg_path, sql_tmp_path):
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass


def run_task_now(config: TaskConfig, force: bool = False):
    """手动立即执行一次任务（同步执行，不经过调度器）"""
    return execute_script(config, force=force)


def register_task(config: TaskConfig):
    """根据 TaskConfig 注册 cron 定时任务到 APScheduler（使用内存 job store，每台机器独立调度）"""
    if not scheduler.running:
        logger.warning(f'调度器未运行，跳过注册: {config.name}')
        return

    job_id = build_job_id(config)

    if not config.is_active or not config.cron_expression.strip():
        try:
            scheduler.remove_job(job_id, jobstore='tasks')
        except Exception:
            pass
        return

    # 多机调度：仅属于当前机器的任务才注册（未分配主机表示任意机器）
    current_host = _get_current_host()
    if config.hosts.exists() and not config.hosts.filter(ip=current_host).exists():
        assigned_ips = list(config.hosts.values_list('ip', flat=True))
        logger.info(f'跳过注册 {config.name}: 当前机器={current_host} 不在分配列表 {assigned_ips} 中')
        try:
            scheduler.remove_job(job_id, jobstore='tasks')
        except Exception:
            pass
        return

    parts = config.cron_expression.strip().split()
    if len(parts) != 5:
        logger.error(f'注册失败 {config.name}: cron 表达式格式错误 "{config.cron_expression}"（需5段，当前{len(parts)}段）')
        return

    # 构建 CronTrigger（APScheduler 会归一化字段值，如 '00'→'0'）
    minute, hour, dom, month, dow = parts
    new_trigger = CronTrigger(
        minute=minute, hour=hour, day=dom,
        month=month, day_of_week=_convert_dow(dow),
        timezone=settings.TIME_ZONE,
    )

    # 检查已有 job 的 cron 是否与当前配置一致，一致则跳过（避免 replace_existing 破坏 misfire 状态）
    existing = scheduler.get_job(job_id, jobstore='tasks')
    if existing and isinstance(existing.trigger, CronTrigger):
        if str(existing.trigger) == str(new_trigger):
            logger.debug(f'跳过重复注册 {job_id} ({config.name}): cron 未变化')
            return

    try:
        scheduler.add_job(
            execute_script,
            new_trigger,
            args=[config],
            id=job_id,
            jobstore='tasks',
            replace_existing=True,
            misfire_grace_time=3600,
        )
        job = scheduler.get_job(job_id, jobstore='tasks')
        logger.info(f'已注册 {job_id} ({config.name}) → cron: {config.cron_expression} → next_run: {job.next_run_time}')
    except Exception as e:
        logger.error(f'添加任务失败 {job_id}: {e}')


def unregister_task(config: TaskConfig):
    """从调度器移除任务"""
    if not scheduler.running:
        return
    try:
        scheduler.remove_job(build_job_id(config), jobstore='tasks')
    except Exception:
        pass


def _cleanup_running_logs():
    """启动时将当前机器上遗留的 RUNNING 状态日志标记为因重启中断"""
    from django.db import connection
    if 'task_config' not in connection.introspection.table_names():
        return
    current_host = _get_current_host()
    stale = TaskExecutionLog.objects.filter(
        result=TaskExecutionLog.ResultType.RUNNING,
        execution_host=current_host,
    )
    count = stale.count()
    if count:
        stale.update(
            result=TaskExecutionLog.ResultType.INTERRUPTED,
            error_message='服务重启导致任务中断',
            end_time=timezone.now(),
        )
        logger.warning(f'清理了 {count} 条遗留的 RUNNING 日志（服务重启中断）')


def sync_all_tasks():
    """同步分配给当前机器的启用任务到调度器"""
    from django.db import connection
    if 'task_config' not in connection.introspection.table_names():
        logger.warning('task_config 表不存在，跳过同步')
        return
    current_host = _get_current_host()
    logger.info(f'开始同步任务，当前机器: {current_host}')
    all_host_ips = list(HostConfig.objects.values_list('ip', flat=True))
    logger.debug(f'HostConfig 中所有 IP: {all_host_ips}')
    # 用 Exists 子查询替代 annotate+filter，避免 M2M OR 条件下 Django ORM 生成错误 SQL
    has_hosts = Exists(HostConfig.objects.filter(tasks=OuterRef('pk')))
    has_matching_host = Exists(HostConfig.objects.filter(tasks=OuterRef('pk'), ip=current_host))
    tasks = TaskConfig.objects.filter(is_active=True).filter(
        ~has_hosts | has_matching_host
    ).distinct()
    logger.info(f'找到 {tasks.count()} 个匹配任务')
    for config in tasks:
        register_task(config)

def start():
    """启动调度器"""
    if scheduler.running:
        logger.info('调度器已在运行')
        return
    try:
        scheduler.start()
        logger.info('调度器启动成功')
        _cleanup_running_logs()
        sync_all_tasks()
        # 定时从数据库刷新任务列表（跨机器变更自动感知）
        sync_interval = getattr(settings, 'TASK_SYNC_INTERVAL', 60)
        scheduler.add_job(
            sync_all_tasks,
            'interval',
            seconds=sync_interval,
            id='_sync_all_tasks_',
            jobstore='tasks',
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info(f'任务同步刷新间隔: {sync_interval}s')
    except Exception as e:
        logger.warning(f'调度器启动失败（表可能尚未创建）: {e}')


def shutdown():
    """优雅关闭调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
