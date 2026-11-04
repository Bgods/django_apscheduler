import atexit
import os
import sys

from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tasks'
    verbose_name = '任务调度'

    def ready(self):
        import tasks.signals  # noqa

        # Django dev 服务器自动重载时，旧进程关闭期间不再尝试创建新线程
        from socketserver import ThreadingMixIn
        ThreadingMixIn.daemon_threads = True

        def _safe_start():
            from .scheduler import start
            start()

        def _shutdown():
            from .scheduler import shutdown
            shutdown()

        # 仅在 runserver 时启动调度器，migrate 等管理命令不应启动
        if 'runserver' not in sys.argv:
            return

        # runserver 自动重载时，子进程不应重复启动调度器
        if os.environ.get('RUN_MAIN') == 'true' and '--noreload' not in sys.argv:
            return

        _safe_start()
        atexit.register(_shutdown)
