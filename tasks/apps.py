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

        from django.db.models.signals import post_migrate

        # Django dev 服务器自动重载时，旧进程关闭期间不再尝试创建新线程
        from socketserver import ThreadingMixIn
        ThreadingMixIn.daemon_threads = True

        def _safe_start():
            from .scheduler import start
            start()

        def _shutdown():
            from .scheduler import shutdown
            shutdown()

        # 注册退出时优雅关闭调度器
        atexit.register(_shutdown)

        # 仅在主进程启动调度器，避免 runserver 自动重载导致的重复执行
        # --noreload 模式下 RUN_MAIN 不会被设置，需放行
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true' and '--noreload' not in sys.argv:
            return

        # runserver 或生产环境启动调度器
        _safe_start()

        # 也注册 post_migrate，确保首次 migrate 后能启动
        post_migrate.connect(lambda sender, **kwargs: _safe_start(), sender=self)
