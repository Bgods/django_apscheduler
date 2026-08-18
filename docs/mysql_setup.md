# MySQL 安装教程

## 1. 下载 MySQL

1. 访问 [MySQL 社区版下载页](https://dev.mysql.com/downloads/mysql/)
2. 选择 Windows 版本（推荐 MSI 安装程序）
3. 或使用 [MySQL 镜像站](https://mirrors.tuna.tsinghua.edu.cn/mysql/downloads/) 加速下载

## 2. 安装 MySQL

1. 运行安装程序，选择「Custom」自定义安装
2. 建议安装路径：`C:\MySQL\`
3. 配置类型选择「Development Machine」
4. 设置 root 密码（记住此密码，填入 `.env`）
5. 其他选项保持默认，完成安装

## 3. 创建数据库

安装完成后，打开 MySQL Command Line Client 或 PowerShell：

```powershell
# 登录 MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE task_scheduler DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 验证
SHOW DATABASES;
EXIT;
```

## 4. 配置远程访问（多机部署）

如需其他机器连接此 MySQL，需开放权限：

```sql
-- 登录 MySQL 后执行
CREATE USER 'root'@'%' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON task_scheduler.* TO 'root'@'%';
FLUSH PRIVILEGES;
```

## 5. 防火墙设置

确保 MySQL 端口 3306 已开放：

```powershell
# 以管理员身份运行 PowerShell
New-NetFirewallRule -DisplayName "MySQL" -Direction Inbound -Protocol TCP -LocalPort 3306 -Action Allow
```

## 6. 常用 MySQL 命令

```sql
-- 查看所有数据库
SHOW DATABASES;

-- 切换数据库
USE task_scheduler;

-- 查看所有表
SHOW TABLES;

-- 查看表结构
DESCRIBE task_config;
```
