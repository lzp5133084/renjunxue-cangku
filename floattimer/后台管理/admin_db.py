# -*- coding: utf-8 -*-
"""
多人后台管理 - SQLite本地数据库
作者：军哥懂保
微信号：xunijiayuan

功能：
- 管理员账户管理（增删改查）
- 计时记录统计
- 操作日志
- 默认管理员：18180309010 / Lzp520520520.
"""

import sqlite3
import hashlib
import os
import json
from datetime import datetime


class AdminDB:
    """管理员数据库管理"""

    # 默认管理员（规则第8条）
    DEFAULT_ADMIN_USER = "18180309010"
    DEFAULT_ADMIN_PASS = "Lzp520520520."

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "admin.db"
            )
        self.db_path = db_path
        self._init_db()
        self._ensure_default_admin()

    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'admin',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_login TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS timer_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    mode TEXT NOT NULL,
                    duration INTEGER NOT NULL,
                    completed INTEGER DEFAULT 0,
                    started_at TEXT,
                    finished_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES admins(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def _ensure_default_admin(self):
        """确保默认管理员存在"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id FROM admins WHERE username = ?",
                (self.DEFAULT_ADMIN_USER,)
            ).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO admins (username, password_hash, role) VALUES (?, ?, ?)",
                    (self.DEFAULT_ADMIN_USER, self._hash_password(self.DEFAULT_ADMIN_PASS), 'super_admin')
                )
                conn.commit()
                print(f"[AdminDB] 默认管理员已创建: {self.DEFAULT_ADMIN_USER}")
        finally:
            conn.close()

    # ==================== 账户管理 ====================

    def authenticate(self, username: str, password: str) -> dict | None:
        """验证登录"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM admins WHERE username = ? AND password_hash = ?",
                (username, self._hash_password(password))
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE admins SET last_login = ? WHERE id = ?",
                    (datetime.now().isoformat(), row['id'])
                )
                conn.commit()
                return dict(row)
            return None
        finally:
            conn.close()

    def add_admin(self, username: str, password: str, role: str = 'admin') -> bool:
        """添加管理员"""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO admins (username, password_hash, role) VALUES (?, ?, ?)",
                (username, self._hash_password(password), role)
            )
            conn.commit()
            self._log_action(None, "add_admin", f"username={username}, role={role}")
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def delete_admin(self, admin_id: int) -> bool:
        """删除管理员"""
        conn = self._get_conn()
        try:
            # 不能删除最后一个超管
            if admin_id == 1:
                return False
            conn.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
            conn.commit()
            self._log_action(admin_id, "delete_admin")
            return True
        finally:
            conn.close()

    def change_password(self, admin_id: int, new_password: str) -> bool:
        """修改密码"""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE admins SET password_hash = ? WHERE id = ?",
                (self._hash_password(new_password), admin_id)
            )
            conn.commit()
            self._log_action(admin_id, "change_password")
            return True
        finally:
            conn.close()

    def list_admins(self) -> list:
        """列出所有管理员"""
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM admins").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ==================== 计时记录 ====================

    def save_timer_record(self, mode: str, duration: int, completed: bool,
                          started_at: str = None, finished_at: str = None,
                          user_id: int = None) -> int:
        """保存计时记录"""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "INSERT INTO timer_records (user_id, mode, duration, completed, started_at, finished_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, mode, duration, 1 if completed else 0,
                 started_at or datetime.now().isoformat(),
                 finished_at or datetime.now().isoformat())
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_timer_stats(self, days: int = 7) -> dict:
        """获取计时统计"""
        conn = self._get_conn()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed_sessions,
                    SUM(duration) as total_seconds,
                    mode,
                    DATE(started_at) as date
                FROM timer_records
                WHERE date(started_at) >= date('now', ?)
                GROUP BY date, mode
                ORDER BY date DESC
            """, (f'-{days} days',)).fetchall()

            return [dict(r) for r in row]
        finally:
            conn.close()

    def get_daily_summary(self) -> dict:
        """今日汇总"""
        conn = self._get_conn()
        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) as sessions,
                    SUM(CASE WHEN completed = 1 THEN duration ELSE 0 END) as focus_seconds
                FROM timer_records
                WHERE date(started_at) = date('now')
            """).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    # ==================== 日志 ====================

    def _log_action(self, user_id: int, action: str, details: str = None):
        """记录操作日志"""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO operation_logs (user_id, action, details) VALUES (?, ?, ?)",
                (user_id, action, details)
            )
            conn.commit()
        finally:
            conn.close()

    def get_logs(self, limit: int = 50) -> list:
        """获取操作日志"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM operation_logs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ==================== 导出 ====================

    def export_data(self, filepath: str) -> bool:
        """导出所有数据为JSON"""
        data = {
            "admins": self.list_admins(),
            "timer_stats": self.get_timer_stats(days=30),
            "daily_summary": self.get_daily_summary(),
            "logs": self.get_logs(limit=200),
            "exported_at": datetime.now().isoformat()
        }
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception:
            return False


# ==================== 后台管理CLI ====================

def main():
    """命令行管理入口"""
    import sys

    print("=" * 50)
    print(" 悬浮计时器 - 后台管理系统")
    print(" 作者：军哥懂保 | 微信：xunijiayuan")
    print("=" * 50)

    db = AdminDB()

    while True:
        print("\n【管理菜单】")
        print(" 1. 管理员登录")
        print(" 2. 查看管理员列表")
        print(" 3. 添加管理员")
        print(" 4. 删除管理员")
        print(" 5. 修改密码")
        print(" 6. 查看今日计时统计")
        print(" 7. 查看操作日志")
        print(" 8. 导出数据")
        print(" 0. 退出")

        choice = input("\n请选择: ").strip()

        if choice == "1":
            user = input("账号: ").strip()
            pwd = input("密码: ").strip()
            result = db.authenticate(user, pwd)
            if result:
                print(f"✅ 登录成功！欢迎 {result['username']}（{result['role']}）")
            else:
                print("❌ 账号或密码错误")

        elif choice == "2":
            admins = db.list_admins()
            if not admins:
                print("暂无管理员")
            else:
                for a in admins:
                    print(f"  [{a['id']}] {a['username']} ({a['role']}) - 创建于 {a['created_at']}")

        elif choice == "3":
            user = input("账号: ").strip()
            pwd = input("密码: ").strip()
            role = input("角色(admin/super_admin): ").strip() or "admin"
            if db.add_admin(user, pwd, role):
                print("✅ 添加成功")
            else:
                print("❌ 添加失败（账号可能已存在）")

        elif choice == "4":
            admins = db.list_admins()
            for a in admins:
                print(f"  [{a['id']}] {a['username']}")
            aid = int(input("输入要删除的ID: ").strip())
            if db.delete_admin(aid):
                print("✅ 删除成功")
            else:
                print("❌ 删除失败")

        elif choice == "5":
            admins = db.list_admins()
            for a in admins:
                print(f"  [{a['id']}] {a['username']}")
            aid = int(input("输入要修改的ID: ").strip())
            pwd = input("新密码: ").strip()
            if db.change_password(aid, pwd):
                print("✅ 修改成功")
            else:
                print("❌ 修改失败")

        elif choice == "6":
            summary = db.get_daily_summary()
            stats = db.get_timer_stats(days=7)
            print(f"\n📊 今日统计:")
            print(f"  完成计时: {summary.get('sessions', 0)} 次")
            focus_min = summary.get('focus_seconds', 0) / 60
            print(f"  专注时长: {focus_min:.1f} 分钟")

        elif choice == "7":
            logs = db.get_logs(20)
            for log in logs:
                print(f"  [{log['created_at']}] {log['action']} - {log.get('details', '')}")

        elif choice == "8":
            path = input("导出路径: ").strip() or "timer_data.json"
            if db.export_data(path):
                print(f"✅ 已导出到 {path}")
            else:
                print("❌ 导出失败")

        elif choice == "0":
            print("👋 再见！")
            break


if __name__ == "__main__":
    main()
