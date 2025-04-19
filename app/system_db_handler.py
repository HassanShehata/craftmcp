import sqlite3
from pathlib import Path


class SystemDBHandler:
    
    def __init__(self, db_path='system.db'):
        self.db_path = db_path
        self._init_db()


    def _connect(self):
        return sqlite3.connect(self.db_path)


    def _init_db(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mcp_status (
                    mcp_id INTEGER PRIMARY KEY,
                    status TEXT,
                    pid INTEGER
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS libraries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    installed_by TEXT,
                    installed_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    owner TEXT,
                    mcp_id INTEGER,
                    snippet TEXT,
                    metadata TEXT,
                    skeleton_code TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    owner TEXT,
                    mcp_id INTEGER,
                    snippet TEXT,
                    metadata TEXT,
                    skeleton_code TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    owner TEXT,
                    mcp_id INTEGER,
                    is_async INTEGER,
                    snippet TEXT,
                    metadata TEXT,
                    skeleton_code TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    token TEXT,
                    is_admin INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mcps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    owner_token TEXT,
                    owner TEXT,
                    metadata TEXT,
                    skeleton_code TEXT
                )
            """)
            conn.commit()


    def create_record(self, table, data: dict):
        with self._connect() as conn:
            keys = ', '.join(data.keys())
            placeholders = ', '.join('?' for _ in data)
            values = tuple(data.values())
            conn.execute(f"INSERT INTO {table} ({keys}) VALUES ({placeholders})", values)
            conn.commit()


    def fetch_records(self, table, where_clause=None):
        with self._connect() as conn:
            cursor = conn.cursor()
            query = f"SELECT * FROM {table}"
            if where_clause:
                query += f" WHERE {where_clause}"
            cursor.execute(query)
            return cursor.fetchall()


    def update_record(self, table, updates: dict, where_clause):
        with self._connect() as conn:
            set_clause = ', '.join(f"{k}=?" for k in updates)
            values = list(updates.values())
            query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
            conn.execute(query, values)
            conn.commit()


    def delete_record(self, table, where_clause):
        with self._connect() as conn:
            conn.execute(f"DELETE FROM {table} WHERE {where_clause}")
            conn.commit()
