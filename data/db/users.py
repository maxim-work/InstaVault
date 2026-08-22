import sqlite3
from datetime import datetime

from core.models.user import User
from data.db.base import BaseDB
from data.exceptions import DuplicateUserError


class UserDB(BaseDB):
    def insert(self, user: User) -> int:
        with self.conn:
            try:
                cursor = self.conn.execute(
                    """INSERT INTO users(tg_id, username, first_name, last_name,
                       is_active, last_active_at, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user.tg_id,
                        user.username,
                        user.first_name,
                        user.last_name,
                        user.is_active,
                        user.last_active_at,
                        user.created_at,
                    ),
                )
                return cursor.lastrowid or 0
            except sqlite3.IntegrityError:
                raise DuplicateUserError(user.tg_id)

    def update(self, user: User) -> None:
        with self.conn:
            self.conn.execute(
                """UPDATE users
                   SET first_name = ?, last_name = ?, username = ?
                   WHERE tg_id = ?""",
                (user.first_name, user.last_name, user.username, user.tg_id),
            )

    def ban(self, tg_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE users SET is_active = 0 WHERE tg_id = ?",
                (tg_id,),
            )

    def unban(self, tg_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE users SET is_active = 1 WHERE tg_id = ?",
                (tg_id,),
            )

    def is_active(self, tg_id: int) -> bool:
        with self.conn:
            row = self.conn.execute(
                "SELECT is_active FROM users WHERE tg_id = ?",
                (tg_id,),
            ).fetchone()
        return bool(row and row[0])

    def delete(self, tg_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM users WHERE tg_id = ?", (tg_id,))

    def delete_all_users(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM users")
            self.conn.execute("DELETE FROM sqlite_sequence WHERE name='users'")

    def get_user(self, tg_id: int) -> User | None:
        with self.conn:
            row = self.conn.execute(
                "SELECT * FROM users WHERE tg_id = ?",
                (tg_id,),
            ).fetchone()
        return User(**dict(row)) if row else None

    def get_banned_users(self) -> list[User]:
        with self.conn:
            rows = self.conn.execute(
                "SELECT * FROM users WHERE is_active = 0"
            ).fetchall()
        return [User(**dict(row)) for row in rows]

    def get_active_users(self) -> list[User]:
        with self.conn:
            rows = self.conn.execute(
                "SELECT * FROM users WHERE is_active = 1"
            ).fetchall()
        return [User(**dict(row)) for row in rows]

    def get_all_users(self) -> list[User]:
        with self.conn:
            rows = self.conn.execute("SELECT * FROM users").fetchall()
        return [User(**dict(row)) for row in rows]

    def get_all_tg_ids_except(self, exclude_ids: list[int]) -> list[int]:
        placeholders = ",".join("?" * len(exclude_ids))
        with self.conn:
            rows = self.conn.execute(
                f"SELECT tg_id FROM users WHERE tg_id NOT IN ({placeholders})",
                exclude_ids,
            ).fetchall()
        return [row["tg_id"] for row in rows]

    def get_user_by_username(self, username: str) -> User | None:
        with self.conn:
            row = self.conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        return User(**dict(row)) if row else None

    def search_users(self, query: str) -> list[User]:
        with self.conn:
            rows = self.conn.execute(
                """
                SELECT * FROM users
                WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            ).fetchall()
        return [User(**dict(row)) for row in rows]

    def count_banned_users(self) -> int:
        with self.conn:
            return self.conn.execute(
                "SELECT COUNT(*) FROM users WHERE is_active = 0"
            ).fetchone()[0]

    def count_active_users(self) -> int:
        with self.conn:
            return self.conn.execute(
                "SELECT COUNT(*) FROM users WHERE is_active = 1"
            ).fetchone()[0]

    def count_all_users(self) -> int:
        with self.conn:
            return self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def count_new_users_since(self, since: datetime) -> int:
        with self.conn:
            return self.conn.execute(
                "SELECT COUNT(*) FROM users WHERE created_at >= ?",
                (since,),
            ).fetchone()[0]

    def count_active_users_since(self, since: datetime) -> int:
        with self.conn:
            return self.conn.execute(
                "SELECT COUNT(*) FROM users WHERE last_active_at >= ?",
                (since,),
            ).fetchone()[0]

    def update_last_active(self, tg_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE users SET last_active_at = ? WHERE tg_id = ?",
                (datetime.now().isoformat(), tg_id),
            )
