"""SQL 脚本执行器 —— 独立运行，通过 JSON 配置接收数据库连接参数。

用法: python sql_runner.py <config.json>
"""

import json
import sys
import os


def _connect(cfg: dict):
    """根据配置连接数据库，返回 (connection, cursor)。"""
    db_type = cfg['db_type']
    host = cfg['host']
    port = cfg['port']
    database = cfg['database']
    username = cfg['username']
    password = cfg['password']
    extra = cfg.get('extra_params', '')

    if db_type == 'mysql':
        try:
            import pymysql
        except ImportError:
            try:
                import MySQLdb as pymysql
            except ImportError:
                print('错误: 缺少 MySQL 驱动，请安装 pymysql 或 mysqlclient', file=sys.stderr)
                sys.exit(1)
        conn = pymysql.connect(
            host=host, port=port, user=username, password=password,
            database=database, charset='utf8mb4',
        )
        return conn, conn.cursor()

    elif db_type == 'postgresql':
        try:
            import psycopg2
        except ImportError:
            print('错误: 缺少 PostgreSQL 驱动，请安装 psycopg2', file=sys.stderr)
            sys.exit(1)
        conn = psycopg2.connect(
            host=host, port=port, user=username, password=password,
            dbname=database,
        )
        return conn, conn.cursor()

    elif db_type == 'sqlserver':
        try:
            import pyodbc
        except ImportError:
            print('错误: 缺少 SQL Server 驱动，请安装 pyodbc', file=sys.stderr)
            sys.exit(1)
        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={host},{port};DATABASE={database};'
            f'UID={username};PWD={password};'
        )
        if extra:
            conn_str += extra
        conn = pyodbc.connect(conn_str)
        return conn, conn.cursor()

    elif db_type == 'oracle':
        try:
            import oracledb
        except ImportError:
            try:
                import cx_Oracle as oracledb
            except ImportError:
                print('错误: 缺少 Oracle 驱动，请安装 oracledb 或 cx_Oracle', file=sys.stderr)
                sys.exit(1)
        dsn = oracledb.makedsn(host, port, service_name=database)
        conn = oracledb.connect(user=username, password=password, dsn=dsn)
        return conn, conn.cursor()

    elif db_type == 'sqlite':
        import sqlite3
        db_path = database
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.path.dirname(cfg['script_path']), db_path)
        conn = sqlite3.connect(db_path)
        return conn, conn.cursor()

    else:
        print(f'错误: 不支持的数据库类型 {db_type}', file=sys.stderr)
        sys.exit(1)


def _split_sql(sql_content: str):
    """将 SQL 内容按分号拆分为语句列表，跳过注释和空语句。"""
    import sqlparse
    statements = [
        str(s).strip()
        for s in sqlparse.split(sql_content)
        if str(s).strip()
    ]
    return statements


def main():
    if len(sys.argv) < 2:
        print('用法: python sql_runner.py <config.json>', file=sys.stderr)
        sys.exit(1)

    cfg_path = sys.argv[1]
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception as e:
        print(f'错误: 无法读取配置文件 {cfg_path}: {e}', file=sys.stderr)
        sys.exit(1)

    script_path = cfg['script_path']
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
    except Exception as e:
        print(f'错误: 无法读取 SQL 文件 {script_path}: {e}', file=sys.stderr)
        sys.exit(1)

    conn = None
    try:
        conn, cursor = _connect(cfg)
        statements = _split_sql(sql_content)
        total = len(statements)
        success = 0
        for i, stmt in enumerate(statements):
            try:
                # 判断 SQL 类型
                stmt_upper = stmt.strip().upper()
                is_query = stmt_upper.startswith('SELECT') or stmt_upper.startswith('SHOW') or stmt_upper.startswith('DESC')

                cursor.execute(stmt)

                if is_query:
                    # 查询语句：打印结果表格
                    try:
                        rows = cursor.fetchall()
                        col_names = [desc[0] for desc in cursor.description]
                        # 列标题
                        print(' | '.join(str(c) for c in col_names))
                        print('-' * 80)
                        if rows:
                            for row in rows:
                                print(' | '.join(str(v) if v is not None else 'NULL' for v in row))
                            print(f'-- 共 {len(rows)} 行')
                        else:
                            print('-- (空结果集)')
                    except Exception:
                        pass
                else:
                    # 非查询语句：显示影响行数
                    rowcount = cursor.rowcount
                    if rowcount >= 0:
                        print(f'-- 影响 {rowcount} 行')
                    else:
                        print('-- 执行成功')

                success += 1

            except Exception as e:
                print(f'第 {i + 1}/{total} 条 SQL 执行失败:', file=sys.stderr)
                print(f'  SQL: {stmt[:200]}{"..." if len(stmt) > 200 else ""}', file=sys.stderr)
                print(f'  错误: {e}', file=sys.stderr)
                conn.rollback()
                print(f'已回滚，共执行 {success}/{total} 条（失败前）', file=sys.stderr)
                sys.exit(1)

        conn.commit()
        print(f'-- 成功执行 {success}/{total} 条 SQL 语句 --')

    except Exception as e:
        print(f'错误: {e}', file=sys.stderr)
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        sys.exit(1)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == '__main__':
    main()
