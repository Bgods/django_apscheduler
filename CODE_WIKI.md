# Django APScheduler 任务调度平台 — Code Wiki

> 基于 **Django 6.0 + APScheduler 3.x + Vue 3 + Element Plus** 的前后端分离任务调度平台，
> 支持 Python / SQL 两类任务的定时执行、多机分布式部署、执行日志监控与权限管理。

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [目录结构](#3-目录结构)
4. [后端核心模块](#4-后端核心模块)
   - 4.1 [全局配置层 `task_scheduler/`](#41-全局配置层-task_scheduler)
   - 4.2 [数据模型 `tasks/models.py`](#42-数据模型-tasksmodelspy)
   - 4.3 [调度引擎 `tasks/scheduler.py`](#43-调度引擎-tasksschedulerpy)
   - 4.4 [SQL 执行器 `tasks/sql_runner.py`](#44-sql-执行器-taskssql_runnerpy)
   - 4.5 [信号同步 `tasks/signals.py`](#45-信号同步-taskssignalspy)
   - 4.6 [视图层 `tasks/views.py`](#46-视图层-tasksviewspy)
   - 4.7 [RESTful API 层 `tasks/api/`](#47-restful-api-层-tasksapi)
5. [前端模块](#5-前端模块)
6. [关键类与函数速查](#6-关键类与函数速查)
7. [依赖关系](#7-依赖关系)
8. [运行与部署](#8-运行与部署)
9. [核心流程与数据流转](#9-核心流程与数据流转)
10. [多机分布式架构](#10-多机分布式架构)

---

## 1. 项目概述

| 维度 | 说明 |
|------|------|
| 定位 | 企业级定时任务调度平台 |
| 任务类型 | Python 脚本（subprocess 调用）/ SQL 脚本（直连目标数据库执行） |
| 调度方式 | Cron 表达式（5 段：分 时 日 月 周）；留空则仅手动触发 |
| 部署形态 | 单机（SQLite）/ 多机分布式（共享 MySQL + HTTP 跨机代理） |
| 后端技术栈 | Django 6.0、DRF 3.16、APScheduler 3.11、django-apscheduler |
| 前端技术栈 | Vue 3 + Vue Router 4 + Element Plus 2.9 + CodeMirror 6（SQL 编辑）+ Axios |
| 服务化 | Windows NSSM 服务（开机自启 + 崩溃自动重启） |

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        浏览器 (SPA)                          │
│          Vue 3 + Element Plus + CodeMirror(SQL)             │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (Session + CSRF)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Django (runserver :8000)                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  /app/ SPA   │  │ /api/v2/ DRF │  │ /api/ 跨机代理   │  │
│  │  spa_view    │  │  ViewSets    │  │ api_execute_task │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                   │            │
│         ▼                 ▼                   ▼            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              tasks 应用 (核心业务)                     │  │
│  │  models ── signals ── scheduler(APScheduler)          │  │
│  │                      │                                │  │
│  │                      ├── _execute_python (subprocess) │  │
│  │                      └── _execute_sql (sql_runner)    │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
         ┌──────────┐  ┌────────────┐  ┌──────────────┐
         │ SQLite / │  │ 目标数据库  │  │  业务脚本     │
         │  MySQL   │  │ (5 种类型)  │  │  (.py / .sql)│
         └──────────┘  └────────────┘  └──────────────┘
```

**设计要点：**

- **调度器与 Web 服务同进程**：`runserver` 启动时 `TasksConfig.ready()` 拉起 `BackgroundScheduler`，不使用 Celery 等独立 Worker。
- **任务存储分离**：APScheduler 使用 `DjangoJobStore`（默认 store，保留兼容）+ `MemoryJobStore("tasks")`（实际任务存储），后者保证多机环境下每台机器独立调度、互不竞争。
- **任务执行独立进程**：Python/SQL 均通过 `subprocess.Popen` 拉起子进程执行，隔离故障、支持超时强杀。
- **SQL 执行器独立脚本**：`sql_runner.py` 作为子进程运行，接收 JSON 配置，密码不暴露在命令行参数中。

---

## 3. 目录结构

```
/workspace
├── manage.py                    # Django 入口，内置 .env 加载（不依赖 python-dotenv）
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量模板
├── deploy.bat / deploy.ps1      # 一键部署脚本（NSSM 服务化）
├── restart.ps1 / sync_code.ps1  # 运维辅助脚本
├── task_scheduler/              # Django 项目配置层
│   ├── settings.py              # 全局配置（DB/DRF/APScheduler/日志/多机）
│   ├── urls.py                  # 根路由（/app + /api/v2 + /api）
│   ├── asgi.py / wsgi.py        # ASGI/WSGI 入口
├── tasks/                       # 核心业务应用
│   ├── apps.py                  # AppConfig：启动调度器、注册信号
│   ├── models.py                # 4 个核心数据模型
│   ├── scheduler.py             # 调度引擎（核心，约 600 行）
│   ├── sql_runner.py            # 独立 SQL 执行脚本
│   ├── signals.py               # post_save/post_delete 同步调度器
│   ├── views.py                 # SPA 入口 + 跨机执行代理
│   ├── urls_api.py              # /api/ 旧版路由（跨机执行）
│   ├── api/
│   │   ├── urls.py              # DRF Router 注册
│   │   ├── viewsets.py          # 8 个 ViewSet + dashboard
│   │   ├── serializers.py       # 序列化器
│   │   └── pagination.py        # 容错分页器
│   ├── migrations/              # 23 个迁移文件
│   └── static/app/              # 前端构建产物（随代码发布）
├── frontend/                    # Vue 3 前端源码
│   ├── src/
│   │   ├── main.js              # 应用入口
│   │   ├── App.vue              # 根组件
│   │   ├── router/index.js      # 路由 + 登录守卫
│   │   ├── api/index.js         # Axios 封装 + 全部接口
│   │   ├── components/
│   │   │   ├── Layout.vue       # 侧边栏 + 顶栏布局
│   │   │   └── SqlEditor.vue    # CodeMirror SQL 编辑器
│   │   └── pages/               # 9 个业务页面
│   ├── vite.config.js           # 构建输出到 tasks/static/app
│   └── package.json
└── docs/                        # 部署文档与截图
```

---

## 4. 后端核心模块

### 4.1 全局配置层 `task_scheduler/`

#### `settings.py` 关键配置

| 配置项 | 值/逻辑 | 说明 |
|--------|---------|------|
| `INSTALLED_APPS` | django_apscheduler, tasks, rest_framework | 核心应用 |
| `DATABASES` | `.env` 含 `NAME` → MySQL；否则 SQLite | 动态切换 |
| `REST_FRAMEWORK` | SessionAuthentication + IsAuthenticated | 会话认证，默认需登录 |
| `DEFAULT_PAGINATION_CLASS` | `tasks.api.pagination.FlexiblePagination` | 容错分页（越界返回空） |
| `PAGE_SIZE` | 20 | 默认每页 20 条 |
| `APSCHEDULER_RUN_NOW_TIMEOUT` | 6000 | 手动触发超时秒数 |
| `SCHEDULER_HOST` | `''`（自动检测局域网 IP） | 多机标识 |
| `SCHEDULER_API_PORT` | `os.getenv('SCHEDULER_API_PORT', 8000)` | 跨机 API 端口 |
| `TASK_SYNC_INTERVAL` | 60 | 定时从 DB 刷新任务的间隔（秒） |
| `TIME_ZONE` | `Asia/Shanghai` | 时区 |
| `LOGGING` | 3 个按天切割的日志文件 | server/error/apscheduler |

**`.env` 加载机制**：`settings.py` 与 `manage.py` 均内置 `_load_env()`，逐行解析 `.env`，**不依赖 `python-dotenv`**。

#### `urls.py` 路由分发

```
/app/            → spa_view（Vue SPA 入口，catch-all）
/api/v2/         → tasks.api.urls（DRF Router，所有业务接口）
/api/            → tasks.urls_api（跨机执行代理 api_execute_task）
```

---

### 4.2 数据模型 `tasks/models.py`

共 4 个模型，构成完整的任务调度领域模型。

#### `HostConfig` — 执行机器

| 字段 | 类型 | 说明 |
|------|------|------|
| `ip` | CharField(unique) | 机器局域网 IP，多机调度的唯一标识 |
| `label` | CharField | 机器标签 |
| `is_active` | BooleanField | 是否启用 |
| `created_at` | DateTimeField | 创建时间 |

#### `DatabaseConfig` — 数据库连接配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `label` | CharField | 配置名称 |
| `db_type` | CharField(choices) | mysql / postgresql / sqlserver / oracle / sqlite |
| `host` / `port` / `database` | — | 连接参数 |
| `username` / `password` | CharField | 凭证 |
| `extra_params` | CharField | 额外连接参数（如 charset、sslmode） |
| `is_active` | BooleanField | 是否启用 |

#### `TaskConfig` — 任务配置（核心模型）

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | CharField | 任务名称 |
| `group` | CharField | 分组（用于分类管理） |
| `task_type` | CharField(choices) | `python` / `sql` |
| `project_path` | CharField | Python 脚本所在目录（SQL 任务留空） |
| `executor_path` | CharField(nullable) | Python 解释器路径，留空=系统默认 |
| `script_path` | CharField | 脚本文件名 |
| `script_args` | CharField | 命令行参数（shlex 解析，支持引号） |
| `sql_content` | TextField | 内联 SQL 内容（SQL 任务必填） |
| `cron_expression` | CharField | 5 段 Cron，留空=仅手动触发 |
| `is_active` | BooleanField | 是否启用调度 |
| `timeout_seconds` | PositiveIntegerField | 超时秒数，0=不限制 |
| `skip_if_running` | BooleanField | 执行中跳过来次触发 |
| `hosts` | M2M(HostConfig) | 分配机器，留空=任意机器 |
| `database` | FK(DatabaseConfig, SET_NULL) | SQL 任务的目标数据库 |
| `created_at` / `updated_at` | DateTimeField | 时间戳 |

**模型方法：**

- `save()`：保存前清理路径中的不可见 Unicode 字符（`\u200b` 等）；SQL 任务强制清空路径字段、校验 `sql_content` 非空。
- `clean()`：校验 Cron 表达式 5 段格式与字段范围；SQL 任务必须选数据库；Python 任务必须有项目路径和脚本。
- `cron_description` (property)：将 Cron 表达式转为中文人类可读描述（如「每天 9 时 0 分」「每周一 9 时」）。

#### `TaskExecutionLog` — 执行日志

| 字段 | 类型 | 说明 |
|------|------|------|
| `task` | FK(TaskConfig, CASCADE) | 关联任务 |
| `start_time` / `end_time` | DateTimeField | 起止时间 |
| `duration` | FloatField | 执行时长（秒） |
| `result` | CharField(choices) | `SUCCESS` / `FAILED` / `TIMEOUT` / `INTERRUPTED` / `RUNNING` |
| `return_code` | BigIntegerField | 子进程返回码 |
| `output` | TextField | 标准输出（截断至 5000 字符） |
| `error_message` | TextField | 错误信息（截断至 2000 字符） |
| `execution_host` | CharField | 实际执行机器 IP |
| `command_text` | TextField | 实际执行的完整命令行 |

**索引**：`idx_log_task_latest(task, -id)`、`idx_log_result(result)`、`idx_log_start_time(start_time)`。

---

### 4.3 调度引擎 `tasks/scheduler.py`

整个平台的**核心模块**，负责任务注册、调度、执行、日志记录与多机协调。

#### 调度器初始化

```python
scheduler = None  # 模块级延迟初始化

def _get_scheduler():
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")
        scheduler.add_jobstore(MemoryJobStore(), "tasks")  # 实际任务存储
    return scheduler
```

**为什么用 `MemoryJobStore` 而不是 `DjangoJobStore`？**
多机环境下若共用 DjangoJobStore，多台机器会竞争同一个 job；改用内存存储后，每台机器独立从数据库加载属于自己的任务并注册，互不干扰。

#### 核心函数

| 函数 | 签名 | 职责 |
|------|------|------|
| `_get_current_host()` | `→ str` | 获取当前机器局域网 IP（优先 `settings.SCHEDULER_HOST`，否则 UDP 探测） |
| `build_job_id(config)` | `→ str` | 生成 job id：`task_{config.id}` |
| `_clean_path(path)` | `→ str` | 移除不可见 Unicode 字符 |
| `_force_kill_process_tree(proc)` | — | 超时强杀进程树（Windows 用 `taskkill /F /T`） |
| `_communicate_limited(proc, timeout)` | `→ (stdout, stderr)` | 带兜底超时的 communicate，防永久阻塞 |
| `_get_default_python()` | `→ str` | 获取系统全局 Python（区分 venv/virtualenv） |
| `_convert_dow(dow)` | `→ str` | **关键**：标准 Cron 星期（0=周日）→ APScheduler 星期（0=周一） |
| `_get_cmd_and_cwd(config)` | `→ (cmd, cwd)` | 拼装 Python 执行命令（含 shlex 解析的 script_args） |
| `execute_script(config, force)` | `→ TaskExecutionLog` | **执行入口**：主机校验 → skip 检查 → 执行 → 写日志 |
| `_execute_python(config, log)` | — | subprocess 执行 Python 脚本 |
| `_execute_sql(config, log)` | — | 写入临时 SQL + JSON 配置，subprocess 调用 sql_runner.py |
| `run_task_now(config, force)` | `→ log` | 手动立即执行（同步，不经调度器） |
| `register_task(config)` | — | 根据 Cron 注册到 APScheduler（含重复注册优化） |
| `unregister_task(config)` | — | 从调度器移除 |
| `sync_all_tasks()` | — | 从 DB 全量同步属于本机的启用任务 |
| `start()` | — | 启动调度器 + 清理遗留 RUNNING 日志 + 注册同步/清理定时任务 |
| `shutdown()` | — | 优雅关闭 |

#### 执行流程 `execute_script()`

```
1. close_old_connections()        关闭可能断开的 DB 连接
2. config.refresh_from_db()       任务可能已被删除
3. 主机匹配检查（force=True 跳过）  多机调度：不在分配列表则 return None
4. skip_if_running 检查           本机仍有 RUNNING 日志则创建 SKIPPED 日志返回
5. 创建 RUNNING 日志
6. 按 task_type 分发：
   - python → _execute_python()
   - sql    → _execute_sql()
7. 异常处理：
   - TimeoutExpired → TIMEOUT
   - 其他 Exception → FAILED
8. close_old_connections() + log.save()（失败则重连重试）
```

#### `_execute_sql()` 安全设计

1. `sql_content` 写入临时 `.sql` 文件。
2. 数据库连接配置（含密码）写入临时 `.json` 文件。
3. 子进程命令仅含 `python sql_runner.py <config.json>`，**密码不出现在进程列表/命令行**。
4. `finally` 中删除两个临时文件。

#### 启动时的两个定时后台任务

`start()` 中额外注册两个 APScheduler interval job：

| Job ID | 间隔 | 职责 |
|--------|------|------|
| `_sync_all_tasks_` | `TASK_SYNC_INTERVAL` 秒（默认 60） | 从 DB 刷新任务列表，感知跨机器的任务变更 |
| `_cleanup_stale_running_logs_` | 30 分钟 | 扫描超时的 RUNNING 日志，标记为 INTERRUPTED（解决进程被杀/断网导致的僵尸日志） |

---

### 4.4 SQL 执行器 `tasks/sql_runner.py`

**独立运行的命令行脚本**，通过 JSON 配置接收数据库连接参数。

**用法**：`python sql_runner.py <config.json>`

**支持的数据库驱动**：

| db_type | 驱动 | 备选 |
|---------|------|------|
| mysql | pymysql | mysqlclient (MySQLdb) |
| postgresql | psycopg2 | — |
| sqlserver | pyodbc (ODBC Driver 17) | — |
| oracle | oracledb | cx_Oracle |
| sqlite | sqlite3（内置） | — |

**执行逻辑**：

1. 读取 JSON 配置 → `_connect()` 建立连接。
2. 读取 SQL 文件 → `_split_sql()` 用 `sqlparse` 按分号拆分语句。
3. 逐条执行：
   - `SELECT/SHOW/DESC` 类查询 → 打印结果表格（列名 + 行数据 + 行数）。
   - 其他语句 → 打印影响行数。
4. **任一语句失败 → `conn.rollback()` + `sys.exit(1)`**（整批回滚）。
5. 全部成功 → `conn.commit()`，打印成功统计。

> 设计意图：独立子进程隔离数据库驱动依赖（用户目标库的驱动装在项目 venv 中），同时避免主进程被数据库连接阻塞。

---

### 4.5 信号同步 `tasks/signals.py`

通过 Django signal 实现「**任务配置变更 → 调度器自动同步**」，无需重启服务。

```python
@receiver(post_save, sender=TaskConfig)
def on_task_config_saved(sender, instance, **kwargs):
    def _sync():
        if instance.is_active:
            register_task(instance)
        else:
            unregister_task(instance)
    transaction.on_commit(_sync)   # 事务提交后执行，确保 M2M(hosts) 已保存

@receiver(post_delete, sender=TaskConfig)
def on_task_config_deleted(sender, instance, **kwargs):
    unregister_task(instance)
```

**关键点**：使用 `transaction.on_commit` 而非直接在 signal 中调用，确保 M2M 字段（`hosts`）已写入数据库后再注册。

---

### 4.6 视图层 `tasks/views.py`

| 视图 | 路由 | 职责 |
|------|------|------|
| `spa_view(request, path)` | `/app/`, `/app/<path:path>` | 读取 `tasks/static/app/index.html` 返回 SPA；缺失时提示构建命令 |
| `api_execute_task(request, pk)` | `POST /api/tasks/<pk>/execute/` | **跨机执行代理**：`force=True` 跳过主机检查，线程异步执行 |

`spa_view` 中调用 `get_token(request)` 确保下发 `csrftoken` Cookie，供前端 CSRF 请求使用。

---

### 4.7 RESTful API 层 `tasks/api/`

#### URL 注册（`api/urls.py`）

```python
router = DefaultRouter()
router.register(r'hosts', HostConfigViewSet)
router.register(r'databases', DatabaseConfigViewSet)
router.register(r'tasks', TaskConfigViewSet)
router.register(r'logs', TaskExecutionLogViewSet)
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserManageViewSet, basename='users')
router.register(r'groups', GroupViewSet, basename='groups')
router.register(r'permissions', PermissionViewSet, basename='permissions')
# + path('dashboard/', dashboard_stats)
```

#### ViewSet 一览

| ViewSet | 权限 | 关键 Action |
|---------|------|-------------|
| `HostConfigViewSet` | IsAuthenticated | list/create/update/destroy；支持 `is_active` 过滤 |
| `DatabaseConfigViewSet` | IsAuthenticated | 含 `task_count` 注解；`test_connection`（在线测连 MySQL/PG/SQLite） |
| `TaskConfigViewSet` | IsAuthenticated | `execute`（手动触发+跨机代理）、`copy`（复制任务）、`groups`（分组下拉）、`options`（轻量下拉） |
| `TaskExecutionLogViewSet` | IsAuthenticated (只读) | list 排除大文本字段 `output`/`error_message`；多条件过滤 |
| `AuthViewSet` | login 允许匿名 | `login` / `logout` / `me` / `change_password` / `update_profile` |
| `UserManageViewSet` | IsAdminUser | `reset_password`；删除时保护最后一个超级管理员 |
| `GroupViewSet` | IsAdminUser | 用户组 CRUD |
| `PermissionViewSet` | IsAdminUser (只读) | 权限列表，供组管理选择 |

#### `TaskConfigViewSet.execute()` 跨机执行逻辑

```
获取任务分配的机器 IP 列表 assigned_ips
├── 当前机器在列表中（或未指定） → 本机线程执行 run_task_now
└── 向其他分配机器发送 POST http://<ip>:<port>/api/tasks/<id>/execute/
```

#### `dashboard_stats()` 仪表盘接口

返回：任务总数/启用数/Python/SQL 数、分组统计、机器/数据库数、最近 10 条执行日志（排除大文本）。

#### 序列化器 `api/serializers.py`

| Serializer | 说明 |
|------------|------|
| `TaskConfigSerializer` | 含 `cron_description`、`hosts_display`、`script_display`、`next_runs`（计算未来 3 次执行时间）、`last_execution`（Prefetch 优化，避免 N+1） |
| `TaskExecutionLogSerializer` | list 时排除 `output`/`error_message` |
| `DatabaseConfigSerializer` | 动态添加 `task_count` 只读字段 |
| `UserCreateSerializer` | 创建用户时接收密码并 `set_password` |

#### 分页器 `api/pagination.py`

`FlexiblePagination` 继承 `PageNumberPagination`，页码越界时返回空结果而非 404（前端体验更友好）。

---

## 5. 前端模块

### 5.1 技术栈

- **Vue 3** (Composition API + `<script setup>`)
- **Vue Router 4**（`createWebHistory('/app/')`，base 与后端路由对齐）
- **Element Plus 2.9**（中文 locale）
- **CodeMirror 6**（SQL 编辑器，`@codemirror/lang-sql` + one-dark 主题）
- **Axios**（统一封装，baseURL `/api/v2`）

### 5.2 路由与页面

| 路由 | 页面 | 说明 |
|------|------|------|
| `/login` | `Login.vue` | 登录页（`meta.public`） |
| `/dashboard` | `Dashboard.vue` | 统计概览 + 最近日志 |
| `/tasks` | `TaskList.vue` | 任务配置管理（最复杂页面，含批量操作、SQL 编辑器） |
| `/hosts` | `HostList.vue` | 执行机器管理 |
| `/databases` | `DatabaseList.vue` | 数据库配置 + 在线测连 |
| `/logs` | `ExecutionLog.vue` | 执行日志查询 |
| `/profile` | `UserProfile.vue` | 个人信息 + 改密 |
| `/users` | `UserManage.vue` | 用户管理（管理员） |
| `/groups` | `GroupManage.vue` | 分组权限管理（管理员） |

### 5.3 布局与认证

- `Layout.vue`：左侧菜单 + 顶部面包屑 + 用户下拉；「系统管理」菜单仅 `is_superuser || is_staff` 可见。
- 路由守卫：未登录（`localStorage.user` 为空）跳转 `/login?redirect=...`。
- Axios 拦截器：
  - **请求**：自动从 Cookie 读取 `csrftoken` 并添加 `X-CSRFToken` 头。
  - **响应**：401/403 自动清理本地状态并跳转登录页。

### 5.4 API 封装 `api/index.js`

按模块导出所有接口函数（`getTasks`、`executeTask`、`testDbConnection` 等），统一使用 `/api/v2` 前缀。

### 5.5 构建配置 `vite.config.js`

```js
base: '/static/app/'                      // 与 Django STATIC_URL 对齐
build.outDir: '../tasks/static/app'       // 产物输出到后端 static 目录
server.proxy: { '/api': 'http://localhost:8000' }  // 开发代理
```

---

## 6. 关键类与函数速查

### 后端

| 类/函数 | 位置 | 一句话说明 |
|---------|------|-----------|
| `TaskConfig` | `models.py` | 任务配置核心模型，含 Cron 校验与中文描述 |
| `TaskExecutionLog.ResultType` | `models.py` | 5 种执行结果枚举 |
| `_get_scheduler()` | `scheduler.py` | 懒初始化 BackgroundScheduler |
| `execute_script()` | `scheduler.py` | 任务执行总入口（含主机匹配/skip/日志） |
| `_execute_sql()` | `scheduler.py` | SQL 任务执行（临时文件+sql_runner 子进程） |
| `_execute_python()` | `scheduler.py` | Python 任务执行（subprocess） |
| `register_task()` | `scheduler.py` | Cron→CronTrigger 注册，含去重优化 |
| `_convert_dow()` | `scheduler.py` | Cron 星期字段转换（0=周日 → 0=周一） |
| `sync_all_tasks()` | `scheduler.py` | 全量同步属于本机的启用任务 |
| `start()` / `shutdown()` | `scheduler.py` | 调度器生命周期 |
| `_connect()` | `sql_runner.py` | 5 种数据库连接分发 |
| `on_task_config_saved` | `signals.py` | 保存后事务提交时同步调度器 |
| `TaskConfigViewSet.execute` | `api/viewsets.py` | 手动触发 + 跨机 HTTP 代理 |
| `FlexiblePagination` | `api/pagination.py` | 越界返回空的容错分页器 |

### 前端

| 组件/函数 | 位置 | 说明 |
|-----------|------|------|
| `Layout.vue` | `components/` | 主布局（侧边栏+顶栏） |
| `SqlEditor.vue` | `components/` | CodeMirror 6 SQL 编辑器组件 |
| `router.beforeEach` | `router/index.js` | 登录守卫 |
| `api.interceptors` | `api/index.js` | CSRF 注入 + 401 跳转 |

---

## 7. 依赖关系

### 7.1 后端 Python 依赖（`requirements.txt`）

| 依赖 | 用途 |
|------|------|
| `Django==6.0.7` | Web 框架 |
| `djangorestframework==3.16.0` | REST API |
| `APScheduler==3.11.3` | 定时调度引擎 |
| `django-apscheduler==0.7.0` | Django JobStore 集成 |
| `mysqlclient==2.2.8` | MySQL 驱动 |
| `psycopg2-binary==2.9.10` | PostgreSQL 驱动 |
| `pyodbc==5.2.0` | SQL Server (ODBC) 驱动 |
| `oracledb==2.5.1` | Oracle 驱动 |
| `sqlparse==0.5.5` | SQL 语句拆分 |
| `psutil==7.2.2` | 进程/系统工具 |
| `pywin32==312` | Windows 平台支持 |
| `tzlocal==5.4.4` | 时区本地化 |

### 7.2 前端依赖（`frontend/package.json`）

| 依赖 | 用途 |
|------|------|
| `vue@^3.5.13` | 前端框架 |
| `vue-router@^4.5.0` | 路由 |
| `element-plus@^2.9.7` | UI 组件库 |
| `@element-plus/icons-vue` | 图标 |
| `axios@^1.9.0` | HTTP 客户端 |
| `codemirror@6` + `@codemirror/lang-sql` | SQL 代码编辑器 |
| `vite@^6.3.5` | 构建工具 |

### 7.3 模块内部依赖关系

```
apps.py ──► signals.py ──► scheduler.py
                  ▲
                  │ post_save/post_delete
            models.py (TaskConfig)

scheduler.py ──► models.py (TaskConfig/HostConfig/DatabaseConfig/TaskExecutionLog)
            ──► sql_runner.py (subprocess 调用)

api/viewsets.py ──► models.py
                 ──► scheduler.py (run_task_now, _get_current_host)
                 ──► serializers.py

views.py ──► scheduler.py (run_task_now)
          ──► models.py (TaskConfig)
```

---

## 8. 运行与部署

### 8.1 开发环境运行

**后端**：

```bash
# 1. 创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env            # 编辑 SECRET_KEY 等

# 3. 数据库迁移
python manage.py migrate

# 4. 创建管理员
python manage.py createsuperuser

# 5. 启动（必须 --noreload，否则调度器在子进程重复启动）
python manage.py runserver 0.0.0.0:8000 --noreload
```

> **重要**：必须加 `--noreload`。Django 的自动重载会启动子进程，导致调度器被重复初始化。`apps.py` 中也做了防护：`RUN_MAIN=true` 且非 `--noreload` 时不启动调度器。

**前端开发**：

```bash
cd frontend
npm install
npm run dev        # Vite dev server :5173，代理 /api 到 :8000
```

访问 `http://localhost:5173/app/`（注意 base 为 `/app/`）。

**前端构建**：

```bash
cd frontend
npm run build      # 产物输出到 ../tasks/static/app/
```

### 8.2 生产部署（Windows 服务化）

以管理员身份运行：

```powershell
.\deploy.bat
```

`deploy.ps1` 自动完成 9 个步骤：

1. **拉取最新代码**（git fetch + reset --hard）
2. **环境检查**（Git、Python 3.10+）
3. **下载 NSSM**（服务管理工具）
4. **停止旧服务**
5. **检查 `.env`**（不存在则从 `.env.example` 生成）
6. **安装 Python 依赖**（venv）
7. **数据库迁移**
8. **检查前端构建产物**
9. **创建管理员**（首次部署）
10. **注册/更新并启动 Windows 服务**（`runserver 0.0.0.0:8000 --noreload --insecure`）

服务配置：开机自启 + 崩溃 5 秒后自动重启。

部署完成后访问 `http://<IP>:8000/app/`。

### 8.3 配置项 `.env`

```env
DEBUG=False
SECRET_KEY=<随机字符串>
ALLOWED_HOSTS=*

# 单机：保持注释，使用 SQLite
# 多机：取消注释，所有机器指向同一 MySQL
# NAME=task_scheduler
# USER=root
# PASSWORD=your-password
# HOST=127.0.0.1
# PORT=3306

SCHEDULER_API_PORT=8000
```

### 8.4 日志

日志位于 `logs/`，按天切割，保留 30 天：

| 文件 | 内容 |
|------|------|
| `server.log` | Django + tasks 通用日志 |
| `error.log` | ERROR 级别以上 |
| `apscheduler.log` | APScheduler 调度器日志 |

---

## 9. 核心流程与数据流转

### 9.1 任务调度执行流程

```
用户在前端保存/启用任务
        │
        ▼
TaskConfig.save()  ──►  post_save signal
                              │
                              ▼
                   transaction.on_commit → register_task()
                              │
                              ▼
              校验 cron → 构建 CronTrigger → add_job(execute_script)
                              │
                              ▼
              APScheduler 按 cron 触发 execute_script(config)
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        主机匹配检查    skip_if_running    创建 RUNNING 日志
                │             │             │
                └─────────────┴─────────────┘
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
        _execute_python()           _execute_sql()
        subprocess.Popen(py,        写临时 SQL+JSON
          script, args)             subprocess.Popen(py,
                │                     sql_runner.py, cfg.json)
                ▼                           │
        communicate(timeout)                ▼
                │                   sql_runner 逐条执行 SQL
                ▼                           │
        写入 output/result          写入 output/result
                │                           │
                └─────────────┬─────────────┘
                              ▼
                    更新 TaskExecutionLog
                    (SUCCESS/FAILED/TIMEOUT)
```

### 9.2 手动触发执行流程

```
前端 POST /api/v2/tasks/<id>/execute/
        │
        ▼
TaskConfigViewSet.execute()
        │
        ├── 本机在分配列表 → threading.Thread(run_task_now)
        │
        └── 其他分配机器 → urllib POST http://<ip>:8000/api/tasks/<id>/execute/
                                      │
                                      ▼
                            api_execute_task (force=True)
                                      │
                                      ▼
                            run_task_now → execute_script
```

### 9.3 多机任务同步流程

```
机器 A 在前端修改任务 → 写入共享 MySQL
        │
        ▼ (机器 A 的 signal 立即 register/unregister)

机器 B 的 _sync_all_tasks_ 定时任务（每 60s）
        │
        ▼
从 MySQL 读取所有 is_active=True 的任务
过滤出属于本机（hosts 含本机 IP 或未分配）的任务
        │
        ▼
逐个 register_task()（cron 未变则跳过）
```

---

## 10. 多机分布式架构

### 10.1 架构图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   机器 A     │     │   机器 B     │     │   机器 C     │
│  :8000       │     │  :8000       │     │  :8000       │
│ 调度器+执行  │     │ 调度器+执行  │     │ 调度器+执行  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────┴──────┐
                    │   MySQL     │
                    │  共享数据库   │
                    └─────────────┘
```

### 10.2 关键设计

| 设计点 | 实现方式 |
|--------|----------|
| 任务共享 | 所有机器连同一个 MySQL，`TaskConfig` 等表共享 |
| 独立调度 | 每台机器用 `MemoryJobStore`，各自从 DB 加载属于自己的任务注册 |
| 主机匹配 | `execute_script` 中检查 `config.hosts` 是否含当前机器 IP |
| 变更感知 | `signal` 即时同步本机 + `_sync_all_tasks_` 每 60s 全量刷新 |
| 跨机触发 | 手动执行时向其他分配机器的 `/api/tasks/<id>/execute/` 发 HTTP POST |
| 执行归属 | 日志 `execution_host` 字段记录实际执行机器 |

### 10.3 任务分配规则

| `hosts` 配置 | 行为 |
|--------------|------|
| 空（未分配） | 所有机器均可执行（每台机器都会注册并触发，即多机同时执行） |
| 指定机器 | 仅选中机器注册并执行 |

> 注意：未分配机器的任务会在**所有机器上同时执行**，如不希望重复执行请务必指定机器。

### 10.4 多机部署步骤

1. 部署共享 MySQL，创建数据库。
2. 每台机器：`git clone` → 配置相同的 `.env`（MySQL + `SCHEDULER_API_PORT`）→ `deploy.bat`。
3. 在管理后台「执行机器」录入各机器局域网 IP。
4. 编辑任务时在「分配机器」选择目标机器。
5. 防火墙开放对应端口（如 8000）。

---

## 附录：常见问题排查

| 问题 | 原因 / 解决 |
|------|-------------|
| 服务启动后日志无调度器信息 | 缺少 `--noreload`；或非 `runserver` 命令（migrate 等不启动调度器） |
| 新增任务不自动生效 | signal 已处理，无需重启；若多机则等 60s 同步间隔 |
| Python 任务 ModuleNotFoundError | 依赖需安装在任务执行环境的 Python 中（`executor_path` 对应的解释器） |
| SQL 任务驱动缺失 | 驱动需安装在**项目 venv** 中（sql_runner 用 `sys.executable`） |
| RUNNING 日志永不结束 | 进程异常退出；`_cleanup_stale_running_logs_` 每 30min 自动标记 INTERRUPTED |
| Cron 星期不对 | 标准 Cron 0=周日，APScheduler 0=周一，`_convert_dow` 已自动转换 |
| 管理后台空白 | 前端产物 `tasks/static/app/index.html` 缺失，需 `npm run build` |
