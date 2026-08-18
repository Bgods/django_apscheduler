import logging
import os
import threading

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import TaskConfig
from .scheduler import run_task_now

logger = logging.getLogger('tasks')


def spa_view(request, path=''):
    """服务 Vue 3 SPA 前端"""
    # 确保 csrftoken cookie 已下发，供前端登录等 CSRF 请求使用
    get_token(request)
    index_path = os.path.join(settings.BASE_DIR, 'tasks', 'static', 'app', 'index.html')
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/html')
    except FileNotFoundError:
        return HttpResponse(
            '<h2>前端尚未构建</h2>'
            '<p>请在 frontend/ 目录下执行:</p>'
            '<pre>npm install && npm run build</pre>',
            status=404,
        )


@csrf_exempt
def api_execute_task(request, pk):
    """内部 API：跨机器触发任务执行（跳过 host 检查）"""
    config = get_object_or_404(TaskConfig, pk=pk)
    threading.Thread(target=run_task_now, args=(config,), kwargs={'force': True}, daemon=True).start()
    return JsonResponse({'status': 'ok', 'task': config.name})
