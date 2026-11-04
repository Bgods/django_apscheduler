# Agents.md — Django APScheduler 任务调度平台

## 项目概述

基于 **Django 6.0 + APScheduler 3.x** 的 Windows 任务调度平台，支持 Python 脚本和 SQL 脚本的定时执行与多机分布式部署。

**现有方案（唯一方向）**：Vue 3 + Element Plus 前后端分离 SPA（`/app/`）+ DRF RESTful API（`/api/v2/`）。

> **说明**：旧版 Django Admin 后台（`/admin/`）已移除，所有功能统一通过新方案实现。

## 技术栈

| 层级       | 技术                                            |
|----------|-----------------------------------------------|
| Web 框架   | Django 6.0.7                                  |
| 调度引擎     | APScheduler 3.11.3 + django-apscheduler 0.7.0 |
| REST API  | Django REST Framework 3.16.0                  |
| 前端框架     | Vue 3 + Element Plus + Vue Router + Axios     |
| 构建工具     | Vite 6                                        |
| SQL 解析    | sqlparse                                      |
| 数据库      | MySQL（多机）/ SQLite（单机，mysqlclient）           |
| 服务化      | NSSM（Windows 服务，开机自启 + 崩溃重启）               |
| Python    | 3.10+（推荐 3.12）                               |

## 项目结构（新方案）

```
django_apscheduler/
├── task_scheduler/          # Django 项目配置
│   ├── settings.py          # 核心配置（.env 加载、数据库、日志、DRF）
│   └── urls.py              # 根路由（api/v2/ + app/ 为主）
│
├── tasks/                   # 核心应用
│   ├── models.py            # 数据模型（HostConfig, DatabaseConfig, TaskConfig, TaskExecutionLog）
│   ├── scheduler.py         # APScheduler 调度引擎（注册/执行/同步/多机调度）
│   ├── sql_runner.py        # 独立 SQL 执行器（subprocess，支持 5 种数据库）
│   ├── signals.py           # 信号（task 保存/删除 → 自动同步调度器）
│   ├── apps.py              # 应用配置（启动调度器、优雅关闭）
│   ├── views.py             # 内部跨机代理接口（仅保留必要内部接口，不做新功能）
│   ├── api/                 # DRF API 层（唯一数据出口）
│   │   ├── serializers.py   # 数据序列化
│   │   ├── viewsets.py      # API 视图集（CRUD + 自定义 action）
│   │   ├── pagination.py    # 自定义分页（页码越界返回空结果）
│   │   └── urls.py          # API 路由（/api/v2/）
│   ├── static/app/          # Vue 构建产物（自动生成，禁止手改）
│   └── migrations/          # 数据库迁移
│
├── frontend/                # Vue 3 前端源码（新版后台唯一前端）
│   ├── src/
│   │   ├── api/index.js     # Axios API 封装（唯一请求入口）
│   │   ├── components/      # 布局与复用组件
│   │   ├── pages/           # 页面组件
│   │   ├── router/index.js  # 路由（历史模式，base=/app/）
│   │   ├── main.js          # 入口（Element Plus 全局注册 + zh-cn）
│   │   └── App.vue          # 根组件（全局样式）
│   ├── vite.config.js       # Vite 配置（构建到 tasks/static/app/）
│   └── package.json
│
├── .env.example             # 环境变量样例
├── requirements.txt
├── manage.py
├── deploy.ps1               # 一键部署/更新（环境检查+下载NSSM+拉取代码+依赖+迁移+注册服务）
├── uninstall_service.ps1    # 卸载 Windows 服务
└── reset_repo.bat           # 强制推送仓库到 Gitea
```

## 路由体系（新方案）

| 路径 | 说明 | 技术 |
|------|------|------|
| `/app/` | Vue 3 SPA 后台（唯一管理界面） | Element Plus |
| `/api/v2/` | DRF RESTful API（唯一数据出口） | DRF ViewSet |
| `/api/` | 内部跨机代理接口（只读保留） | Django View |

## API 规范（/api/v2/）必备约定

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/v2/tasks/` | GET/POST | 任务列表/创建 |
| `/api/v2/tasks/<id>/` | GET/PATCH/DELETE | 任务详情/更新/删除 |
| `/api/v2/tasks/<id>/execute/` | POST | 触发任务执行 |
| `/api/v2/tasks/<id>/copy/` | POST | 复制任务 |
| `/api/v2/tasks/groups/` | GET | 获取全部分组 |
| `/api/v2/hosts/` | GET/POST | 机器列表/创建 |
| `/api/v2/hosts/<id>/` | GET/PATCH/DELETE | 机器详情/更新/删除 |
| `/api/v2/databases/` | GET/POST | 数据库列表/创建 |
| `/api/v2/databases/<id>/` | GET/PATCH/DELETE | 数据库详情/更新/删除 |
| `/api/v2/databases/test_connection/` | POST | 测试数据库连接 |
| `/api/v2/logs/` | GET | 执行日志列表（只读） |
| `/api/v2/logs/<id>/` | GET | 日志详情 |
| `/api/v2/auth/login/` | POST | 登录 |
| `/api/v2/auth/logout/` | POST | 注销 |
| `/api/v2/auth/me/` | GET | 当前用户信息 |
| `/api/v2/auth/change_password/` | POST | 修改当前用户密码 |
| `/api/v2/auth/update_profile/` | PATCH | 修改当前用户资料（邮箱/姓名） |
| `/api/v2/users/` | GET/POST | 用户列表/创建（仅超管） |
| `/api/v2/users/<id>/` | GET/PATCH/DELETE | 用户详情/更新/删除（仅超管） |
| `/api/v2/users/<id>/reset_password/` | POST | 管理员重置指定用户密码（仅超管） |
| `/api/v2/groups/` | GET/POST | 分组列表/创建（仅超管） |
| `/api/v2/groups/<id>/` | GET/PATCH/DELETE | 分组详情/更新/删除（仅超管） |
| `/api/v2/permissions/` | GET | 权限列表（仅超管，供分组选择权限） |

**新增接口的标准**：
- 路由统一注册在 `tasks/api/urls.py` 的 `DefaultRouter` 中，禁止散落各处
- 逻辑写入 `tasks/api/viewsets.py` 的对应 ViewSet；自定义动作用 `@action(detail=False/True)` 装饰器
- 序列化统一在 `tasks/api/serializers.py`，禁止直接在 view 中拼接 dict
- 列表接口默认支持分页（`page`/`page_size`，`page_size` 最大 10000）、DRF 的 `search_fields` 过滤
- 查询参数筛选在 `get_queryset()` 中按 `request.query_params` 过滤
- 注意模型 `Meta.ordering` 会干扰 MySQL `DISTINCT`，去重查询必须显式 `order_by`（如 `order_by('field').distinct()`）

## 前端开发规范（新方案）

- 页面路由：`frontend/src/router/index.js`，Layout 子路由 + `meta.title` 面包屑
- API 请求：统一封装进 `frontend/src/api/index.js`，页面禁止直接 new axios
  - `baseURL: '/api/v2'`，拦截器自动附加 CSRF Token
  - 返回结构：`GET 列表` → `{ results, count }`，`POST/PATCH` 返回对象
- 组件：复用 `components/`，每个页面一个 `<script setup>` 单文件组件
- 页面布局遵循现有模式：`.page-container`（绝对定位撑满）+ `.page-header`（筛选/操作区）+ `.table-wrapper` + `.page-footer`（分页）+ `el-dialog`（弹窗）
- 全局样式：`App.vue` 的非 scoped `<style>` 块（如按钮禁用态颜色覆盖）
- 构建：`cd frontend && npm run build`，产物输出到 `tasks/static/app/`，**禁止手改构建产物**
- 开发调试：`cd frontend && npm run dev`（Vite 代理 /api → localhost:8000）

## 数据模型

### HostConfig（执行机器）
- `ip`（唯一）、`label`、`is_active`

### DatabaseConfig（数据库配置）
- `label`、`db_type`（mysql/postgresql/sqlserver/oracle/sqlite）
- `host`、`port`、`database`、`username`、`password`、`extra_params`

### TaskConfig（任务配置）
- `name`、`group`、`task_type`（python/sql）
- `project_path`、`executor_path`、`script_path`（Python 任务）
- `sql_content`、`database`（SQL 任务）
- `cron_expression`、`is_active`、`timeout_seconds`
- `hosts`（M2M → HostConfig）

### TaskExecutionLog（执行日志）
- `task`、`start_time`、`end_time`、`duration`
- `result`（SUCCESS/FAILED/TIMEOUT/INTERRUPTED/RUNNING）
- `return_code`、`output`、`error_message`
- `execution_host`、`command_text`

## 关键架构决策

1. **内存 JobStore 用于自定义任务**：避免多机环境 DjangoJobStore 竞争
2. **subprocess 执行 SQL**：`sql_runner.py` 子进程执行，隔离依赖、避免密码进进程列表
3. **transaction.on_commit 同步**：M2M 保存完毕后再注册调度器
4. **跨机代理执行**：HTTP POST 至目标机器内部接口，无需消息队列
5. **定时全量同步**：每 60s 刷新任务列表，实现跨机器 eventual consistency
6. **.env 自加载**：settings.py 手动解析，不依赖 python-dotenv
7. **路径不可见字符清理**：防止复制路径带入 Unicode 控制字符
8. **FlexiblePagination**：DRF 自定义分页，页码越界返回空结果而非 404
9. **SPA 嵌入 Django**：Vue 产物放入 `tasks/static/app/`，Django 直接服务，保持单机 NSSM 部署不变

## 开发注意事项

- 启动服务必须带 `--noreload`，避免 Django 自动重载导致调度器重复启动
- 修改任务无需重启，信号 + 定时同步自动生效
- Python 任务依赖装在目标环境 Python 中；SQL 任务依赖装在项目 venv 中
- 多机部署必须用 MySQL，SQLite 不支持多进程并发写入
- Cron 星期值转换：标准 cron（0=周日）→ APScheduler（0=周一）
- 新增功能按「新增 API 接口的标准」+「前端开发规范」落实

## 部署与更新

### 首次部署（新机器）

1. **准备环境**：安装 Python 3.10+、Git
2. **克隆代码**：`git clone http://192.168.13.75:3000/chenfs/django_apscheduler.git`
3. **配置 .env**：复制 `.env.example` 为 `.env`，修改数据库配置（多机部署必须一致）
4. **运行部署**：以管理员身份运行 `deploy.ps1`（自动下载 NSSM、注册服务、创建管理员）

### 日常更新（所有机器）

以管理员身份运行 `deploy.ps1`，脚本自动完成所有步骤。

### 前端构建

- 前端构建产物已入库（`tasks/static/app/`），拉取代码后直接使用，无需 Node.js
- 修改前端代码后需 `cd frontend && npm run build` 并提交产物

### 多机部署注意

- 所有机器的 `.env` 数据库配置必须一致
- 所有机器的端口必须一致
- 代码更新后每台机器都需运行 `deploy.ps1`