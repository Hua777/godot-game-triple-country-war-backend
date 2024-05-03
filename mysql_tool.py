import mysql.connector
from dbutils.pooled_db import PooledDB


class MySQLTool:
    def __init__(self, host, port, user, password, database):
        self.pool = PooledDB(
            creator=mysql.connector,
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
        )

    def execute_query(self, query: str, params=None) -> list[dict]:
        print(f"[execute query] {query.strip().replace('  ', ' ')}")
        conn = self.pool.connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result

    def execute_query_one(self, query: str, params=None) -> dict:
        print(f"[execute query] {query.strip().replace('  ', ' ')}")
        conn = self.pool.connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result

    def execute_update(self, query: str, params=None) -> any:
        print(f"[execute query] {query.strip().replace('  ', ' ')}")
        conn = self.pool.connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        last_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return last_id


MYSQL_TOOL = MySQLTool(
    "rm-bp12901ffblxg3v0j6o.mysql.rds.aliyuncs.com",
    3306,
    "root",
    "Liao31415926",
    "tcwb",
)
