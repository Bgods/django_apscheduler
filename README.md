# Django APScheduler 任务调度平台

基于 Django 6.0 + APScheduler 3.x + Vue 3 的任务调度平台，支持 Python 脚本和 SQL 脚本的定时执行与多机分布式部署。

## 目录

- [功能特性](#功能特性)
- [环境要求](#环境要求)
- [一、首次部署](#一首次部署)
- [二、配置 Windows 服务](#二配置-windows-服务开机自启--崩溃自动重启)
- [三、辅助脚本说明](#三辅助脚本说明)
- [四、管理后台说明](#四管理后台说明)
- [五、日志管理](#五日志管理)
- [六、常见问题](#六常见问题)
- [附录](#附录)

***

## 功能特性

- 支持 Python / SQL 两种任务类型
- Cron 表达式定时调度
- SQL 内容直接编辑或从文件加载
- 任务执行日志与状态监控
- 超时自动终止
- Vue 3 + Element Plus 前后端分离管理后台（`/app/`）+ DRF RESTful API（`/api/v2/`）
- Windows 服务化部署（开机自启 + 崩溃重启）
- 支持多机分布式部署（详见 [docs/multi\_machine\_setup.md](docs/multi_machine_setup.md)）

***

## 环境要求

| 组件     | 要求                                     |
| ------ | -------------------------------------- |
| 操作系统   | Windows 10/11、Windows Server 2016+     |
| Python | 3.10+（推荐 3.12）                         |
| Node.js | 18+（构建前端管理后台）                       |
| 数据库    | SQLite（内置）或 MySQL 5.7+ / MariaDB 10.3+ |

***

## 一、首次部署

### 1.1 将项目拷贝到目标目录

将整个项目文件夹拷贝到目标机器的任意路径（例如 `D:\django_apscheduler\`），下面以 `<项目目录>` 代指。

### 1.2 配置环境变量（.env）

复制样例 `.env.example` 文件保存为 `.env` 并编辑：

```powershell
copy .env.example .env
```

然后编辑 `.env` 文件，根据实际情况修改：

**方式一：使用 SQLite（单机部署推荐，无需安装数据库）**

```ini
# Django 配置
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=*

# 数据库配置（使用 SQLite，无需额外安装）
# 留空或注释掉 MySQL 配置即可，系统会自动使用 SQLite
```

**方式二：使用 MySQL（多机部署必须）**

```ini
# Django 配置
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=*

# 数据库配置（连接 MySQL）
NAME=task_scheduler
USER=root
PASSWORD=your-password
HOST=127.0.0.1
PORT=3306
```

> **注意：** 使用 MySQL 时数据库需预先创建（详见 [MySQL 安装教程](docs/mysql_setup.md)），`.env` 会被项目自动加载，无需手动设置系统环境变量。

### 1.3 安装依赖

双击运行 `setup_venv.bat`，脚本会自动创建虚拟环境并安装依赖。

或手动执行：

```powershell
cd <项目目录>

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境并安装依赖
.venv\Scripts\activate
pip install -r requirements.txt
```

核心依赖：`Django 6.0`、`django-apscheduler`、`djangorestframework`、`mysqlclient`、`sqlparse`

### 1.4 构建前端管理后台

管理后台为 Vue 3 + Element Plus SPA，源码位于 `frontend/`，构建产物输出到 `tasks/static/app/`：

```powershell
cd frontend
npm install
npm run build
cd ..
```

> 部署时可直接使用构建产物；开发调试可用 `npm run dev`（Vite 代理 `/api` 至 `localhost:8000`）。

### 1.5 初始化数据库

**使用 SQLite**：直接执行迁移即可，数据库文件会自动创建

```powershell
python manage.py migrate
```

**使用 MySQL**：需先在 MySQL 中创建数据库

```powershell
# 先在 MySQL 中创建数据库
# CREATE DATABASE task_scheduler DEFAULT CHARACTER SET utf8mb4;

# 然后执行迁移
python manage.py migrate
```

迁移完成后会生成以下核心表：

| 表名                   | 说明      |
| -------------------- | ------- |
| `task_config`        | 任务配置    |
| `host_config`        | 执行机器    |
| `database_config`    | 数据库连接配置 |
| `task_execution_log` | 任务执行日志  |

### 1.6 创建管理员账户

```powershell
python manage.py createsuperuser
```

### 1.7 启动服务验证

```powershell
python manage.py runserver 0.0.0.0:8000 --noreload
```

访问 `http://localhost:8000/app/`，登录后进入管理后台，确认页面能正常访问。

> 启动必须带 `--noreload`，避免 Django 自动重载导致调度器重复启动。

***

## 二、配置 Windows 服务（开机自启 + 崩溃自动重启）

### 2.1 以管理员身份运行 PowerShell

右键「Windows PowerShell」→「以管理员身份运行」。

### 2.2 执行一键安装脚本

```powershell
cd <项目目录>
.\install_service.ps1
```

脚本自动完成：

1. 下载 NSSM（如果不存在）
2. 清理旧服务
3. 创建 `Django_APScheduler` 服务（开机自启、崩溃 5 秒后自动重启）
4. 启动服务

> 脚本自动检测并使用项目内的虚拟环境 Python：`<项目目录>\.venv\Scripts\python.exe`

### 2.3 修改服务端口（可选）

默认端口为 `8000`，如需修改：

1. 打开 `install_service.ps1`，修改 `$port` 变量：
   ```powershell
   $port = 8001  # 修改为需要的端口，要求与 `.env` 中的 `SCHEDULER_API_PORT` 一致
   ```
2. 重新执行安装脚本（会自动清理旧服务并重建）

> 多机部署时，所有机器的服务端口必须保持一致，且与 `.env` 中的 `SCHEDULER_API_PORT` 一致

### 2.4 服务管理命令

```powershell
# 查看状态
.\nssm\nssm.exe status Django_APScheduler
# 启动
.\nssm\nssm.exe start Django_APScheduler
# 停止
.\nssm\nssm.exe stop Django_APScheduler
# 重启
.\nssm\nssm.exe restart Django_APScheduler
# 卸载服务
.\nssm\nssm.exe remove Django_APScheduler confirm
```

***

## 三、辅助脚本说明

项目根目录提供以下辅助脚本，均在 `<项目目录>` 下执行：

| 脚本                         | 场景               | 权限      | 作用                                          | 注意                 |
| -------------------------- | ---------------- | ------- | ------------------------------------------- | ------------------ |
| `setup_venv.bat`           | 首次部署             | 普通用户    | 创建虚拟环境 `.venv` 并安装依赖                        | 需要系统已安装 Python     |
| `install_requirements.bat` | 新增 Python 依赖后    | 普通用户    | 激活虚拟环境并执行 `pip install -r requirements.txt` | 确保 `.venv` 已创建     |
| `sync_code.ps1`            | 更新代码             | 普通用户    | 从 Gitea 拉取最新代码（自动初始化 Git 仓库）                | 首次运行会自动 `git init` |
| `install_service.ps1`      | 首次部署、服务配置重建      | **管理员** | 下载 NSSM → 清理旧服务 → 注册服务（开机自启 + 崩溃重启）→ 启动服务   | 会先停止并删除同名旧服务       |
| `restart_service.bat`      | 更新代码、修改 `.env` 后 | **管理员** | 调用 `nssm restart Django_APScheduler` 重启服务   | 仅对 NSSM 注册的服务有效    |
| `uninstall_service.ps1`    | 迁移部署、彻底清理        | **管理员** | 停止并删除 `Django_APScheduler` 服务               | 不会删除项目文件和 NSSM 目录  |

***

## 四、管理后台说明

管理后台为 Vue 3 SPA，地址：`http://<本机IP>:8000/app/`

| 菜单           | 功能                   |
| ------------ | -------------------- |
| 仪表盘         | 任务统计与最近执行概览        |
| 任务调度 → 任务配置  | 管理定时任务（Python / SQL） |
| 任务调度 → 执行机器  | 管理执行机器列表             |
| 任务调度 → 数据库配置 | 管理 SQL 任务的数据库连接      |
| 任务调度 → 执行日志  | 查看任务执行历史             |
| 系统管理 → 用户管理 | 管理用户账号与权限            |
| 系统管理 → 分组管理 | 管理用户分组与权限            |

> 所有数据操作通过 `/api/v2/` DRF RESTful API 完成，不再使用 Django Admin 后台。

### 4.1 任务类型

| 类型        | 说明                                     | 使用的 Python                  |
| --------- | -------------------------------------- | --------------------------- |
| Python 脚本 | 通过 subprocess 调用 Python 解释器执行 `.py` 文件 | 配置的「执行器路径」→ 未配置则系统全局 Python |
| SQL 脚本    | 通过 sql\_runner 连接目标数据库执行 SQL 语句        | 当前 Django 服务环境（venv）        |

### 4.2 执行日志状态

| 状态  | 颜色 | 说明             |
| --- | -- | -------------- |
| 成功  | 绿  | 任务正常执行完成       |
| 失败  | 红  | 脚本报错或异常        |
| 超时  | 橙  | 超过设定的超时时间被强制终止 |
| 中断  | 灰  | 服务重启导致任务中断     |
| 执行中 | 蓝  | 正在执行           |

### 4.3 任务配置字段

| 字段       | 说明                  |
| -------- | ------------------- |
| 名称       | 任务唯一标识              |
| 分组       | 任务分组                |
| 任务类型     | Python / SQL        |
| 启用       | 是否启用定时调度            |
| 超时时间(秒)  | 0=不限制，超时后自动终止并标记为超时 |
| 分配机器     | 指定在哪些机器上执行（多机部署时使用） |
| 项目路径     | Python 脚本所在目录       |
| 执行器路径    | 留空=系统全局 Python      |
| 执行脚本     | 需要执行的脚本文件名          |
| SQL 内容   | SQL 任务直接填写的 SQL 语句  |
| Cron 表达式 | 分 时 日 月 周，留空=仅手动触发  |

***

## 五、日志管理

日志文件位于 `logs/` 目录，按天分割，保留 30 天：

| 日志文件              | 内容                |
| ----------------- | ----------------- |
| `server.log`      | 服务通用日志            |
| `error.log`       | 错误日志              |
| `apscheduler.log` | APScheduler 调度器日志 |

日志格式：`[YYYY-MM-DD HH:MM:SS] [LEVEL] [MODULE] MESSAGE`

***

## 六、常见问题

### Q1: 服务启动后日志中无调度器启动信息

确保启动参数包含 `--noreload`，否则 Django 的自动重载机制可能导致调度器未在主进程中启动。

### Q2: 新增任务不自动生效

无需重启。任务保存后会通过 `transaction.on_commit` 自动同步到调度器。

### Q3: ModuleNotFoundError: No module named 'xxx'

需根据任务类型区分安装位置：

- **Python 任务**：依赖包需安装在对应环境中：
  ```powershell
  python -m pip install xxx
  ```
- **SQL 任务**：依赖包（如 `sqlparse`、数据库驱动）需安装在项目 venv 中：
  ```powershell
  cd <项目目录>
  .venv\Scripts\activate
  pip install xxx
  ```

### Q4: 脚本路径问题

- `项目路径` + `执行脚本` = 完整脚本路径
- 执行脚本建议只填文件名（如 `脚本.py`），程序会自动在项目路径下查找

### Q5: 管理后台空白或提示未构建

前端产物位于 `tasks/static/app/`，若缺失请先在 `frontend/` 目录执行 `npm install && npm run build`。

***

## 附录

| 文档                                    | 说明               |
| ------------------------------------- | ---------------- |
| [MySQL 安装教程](docs/mysql_setup.md)     | MySQL 数据库安装与配置指南 |
| [多机部署指南](docs/multi_machine_setup.md) | 多机分布式部署配置说明      |


