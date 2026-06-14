import os
import sqlite3

MYSQL_AVAILABLE = False
try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    mysql = None

MSSQL_AVAILABLE = False
try:
    import pyodbc
    MSSQL_AVAILABLE = True
except ImportError:
    pyodbc = None

DB_BACKEND = os.getenv("DB_BACKEND", "auto").lower()
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "student"),
}
MSSQL_CONFIG = {
    "host": os.getenv("MSSQL_HOST", "127.0.0.1"),
    "port": os.getenv("MSSQL_PORT", "1433"),
    "database": os.getenv("MSSQL_DATABASE", "student"),
    "trusted_connection": os.getenv("MSSQL_TRUSTED", "yes"),
    "user": os.getenv("MSSQL_USER", ""),
    "password": os.getenv("MSSQL_PASSWORD", ""),
}
DB_FILENAME = os.path.join(os.path.dirname(__file__), "register.db")

SQLITE_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS register(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT,
    last_name TEXT,
    contact TEXT,
    email TEXT UNIQUE,
    security_question TEXT,
    answer TEXT,
    password TEXT
)
"""

MYSQL_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS register(
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    contact VARCHAR(20),
    email VARCHAR(100) UNIQUE,
    security_question VARCHAR(100),
    answer VARCHAR(100),
    password VARCHAR(100)
)
"""

SQLSERVER_CREATE_TABLE_SQL = """
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[register]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[register](
        id INT IDENTITY(1,1) PRIMARY KEY,
        first_name NVARCHAR(100),
        last_name NVARCHAR(100),
        contact NVARCHAR(20),
        email NVARCHAR(100) UNIQUE,
        security_question NVARCHAR(100),
        answer NVARCHAR(100),
        password NVARCHAR(255)
    )
END
"""


def _use_mysql():
    if DB_BACKEND == "mysql":
        if not MYSQL_AVAILABLE:
            raise ImportError(
                "mysql-connector-python is required for MySQL backend. Install it with: pip install mysql-connector-python"
            )
        return True
    return DB_BACKEND == "auto" and MYSQL_AVAILABLE


def _use_sqlserver():
    if DB_BACKEND == "sqlserver":
        if not MSSQL_AVAILABLE:
            raise ImportError(
                "pyodbc is required for SQL Server backend. Install it with: pip install pyodbc"
            )
        return True
    return False


def get_db_connection():
    if _use_sqlserver():
        master_conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={MSSQL_CONFIG['host']},{MSSQL_CONFIG['port']};"
            f"DATABASE=master;"
            f"Trusted_Connection={MSSQL_CONFIG['trusted_connection']};"
            + (f"UID={MSSQL_CONFIG['user']};PWD={MSSQL_CONFIG['password']};" if MSSQL_CONFIG['user'] else "")
        )
        master_cursor = master_conn.cursor()
        master_cursor.execute(
            f"IF DB_ID(N'{MSSQL_CONFIG['database']}') IS NULL CREATE DATABASE [{MSSQL_CONFIG['database']}];"
        )
        master_conn.commit()
        master_cursor.close()
        master_conn.close()

        connection = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={MSSQL_CONFIG['host']},{MSSQL_CONFIG['port']};"
            f"DATABASE={MSSQL_CONFIG['database']};"
            f"Trusted_Connection={MSSQL_CONFIG['trusted_connection']};"
            + (f"UID={MSSQL_CONFIG['user']};PWD={MSSQL_CONFIG['password']};" if MSSQL_CONFIG['user'] else "")
        )
        cursor = connection.cursor()
        cursor.execute(SQLSERVER_CREATE_TABLE_SQL)
        connection.commit()
        return connection, cursor

    if _use_mysql():
        connection = mysql.connector.connect(
            host=MYSQL_CONFIG["host"],
            port=MYSQL_CONFIG["port"],
            user=MYSQL_CONFIG["user"],
            password=MYSQL_CONFIG["password"],
        )
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_CONFIG['database']}")
        cursor.execute(f"USE {MYSQL_CONFIG['database']}")
        cursor.execute(MYSQL_CREATE_TABLE_SQL)
        connection.commit()
        return connection, cursor

    connection = sqlite3.connect(DB_FILENAME)
    cursor = connection.cursor()
    cursor.execute(SQLITE_CREATE_TABLE_SQL)
    connection.commit()
    return connection, cursor


def execute_query(cursor, query, params=()):
    if _use_mysql():
        query = query.replace("?", "%s")
    cursor.execute(query, params)
    return cursor
