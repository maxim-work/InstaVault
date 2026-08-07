import sqlite3
from datetime import datetime
from typing import Any, Optional

from core.exceptions import ResourceNotFoundError
from core.models.resource import Resource
from core.models.user import User
from data.exceptions import DuplicateResourceError, DuplicateUserError
from data.filter import ResourceFilter, calculate_scores


class ResourceDB:
    COLUMNS = [
        "tg_id",
        "title",
        "url",
        "description",
        "resource_type",
        "platform",
        "kind",
        "external_id",
        "status",
        "tags",
        "my_notes",
        "my_rating",
        "engagement",
        "views",
        "duration",
        "published_at",
        "completed_at",
    ]

    def __init__(self, path: str = "data/database.db"):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def insert(self, resource: Resource) -> int:
        try:
            data = resource.to_db_dict()
            with self.conn:
                cursor = self.conn.execute(self._build_insert_query(), data)
                if cursor.lastrowid is None:
                    raise RuntimeError("Failed to insert resource")
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise DuplicateResourceError(resource.url)

    def update(self, resource: Resource) -> None:
        data = resource.to_db_dict()
        data["id"] = resource.id

        with self.conn:
            cursor = self.conn.execute(self._build_update_query(), data)
            if cursor.rowcount == 0:
                raise ResourceNotFoundError(str(resource.id))

    def delete(self, resource_id: int, tg_id: int) -> None:
        with self.conn:
            self.conn.execute(
                "DELETE FROM resources WHERE id = ? AND tg_id = ?",
                (resource_id, tg_id),
            )

    def delete_all(self, tg_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM resources WHERE tg_id = ?", (tg_id,))

    def get_resource(self, resource_id: int, tg_id: int) -> Optional[Resource]:
        with self.conn:
            row = self.conn.execute(
                "SELECT * FROM resources WHERE id = ? AND tg_id = ?",
                (resource_id, tg_id),
            ).fetchone()
        return Resource(**dict(row)) if row else None

    def get_all_resources(self, tg_id: int) -> list[Resource]:
        with self.conn:
            rows = self.conn.execute(
                "SELECT * FROM resources WHERE tg_id = ? ORDER BY created_at DESC",
                (tg_id,),
            ).fetchall()
        return [Resource(**dict(row)) for row in rows]

    def count_user_resources(self, tg_id: int) -> int:
        with self.conn:
            row = self.conn.execute(
                "SELECT COUNT(*) FROM resources WHERE tg_id = ?",
                (tg_id,),
            ).fetchone()
        return row[0] if row else 0

    def count_all_resources(self) -> int:
        with self.conn:
            return self.conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]

    def search(
        self, tg_id: int, filter: Optional[ResourceFilter] = None
    ) -> list[tuple[Resource, int]]:
        if filter is None:
            filter = ResourceFilter(tg_id=tg_id)
        resources = self._get_candidates(filter)
        return calculate_scores(resources, filter)

    def export_urls(self, tg_id: int) -> list[str]:
        with self.conn:
            rows = self.conn.execute(
                "SELECT url FROM resources WHERE tg_id = ?", (tg_id,)
            ).fetchall()
        return [row["url"] for row in rows]

    def export_data(self, tg_id: int) -> list[Resource]:
        with self.conn:
            rows = self.conn.execute(
                "SELECT * FROM resources WHERE tg_id = ?", (tg_id,)
            ).fetchall()
        return [Resource(**dict(row)) for row in rows]

    def import_data(
        self, data: list[Resource], tg_id: int
    ) -> tuple[int, int, list[str]]:
        count = 0
        errors = []

        with self.conn as conn:
            conn.execute("BEGIN")
            for resource in data:
                try:
                    resource_data = resource.to_db_dict()
                    conn.execute(self._build_insert_query(), resource_data)
                    count += 1
                except sqlite3.IntegrityError:
                    errors.append(f"Дубликат: {resource.url}")
                except Exception as e:
                    errors.append(f"{resource.url}: {e}")
            conn.commit()

        return count, len(data), errors

    def get_by_url(self, url: str, tg_id: int) -> Optional[Resource]:
        with self.conn as conn:
            cursor = conn.execute(
                "SELECT * FROM resources WHERE url = ? AND tg_id = ?",
                (url, tg_id),
            )
            row = cursor.fetchone()
        return Resource(**dict(row)) if row else None

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get_candidates(self, f: ResourceFilter) -> list[Resource]:
        query = "SELECT * FROM resources WHERE tg_id = :tg_id"
        params: dict[str, Any] = {"tg_id": f.tg_id}

        if f.resource_type is not None:
            query += " AND resource_type = :resource_type"
            params["resource_type"] = f.resource_type.code

        if f.status is not None:
            query += " AND status = :status"
            params["status"] = f.status.code

        if f.platform is not None:
            query += " AND platform = :platform"
            params["platform"] = f.platform.code

        if f.kind is not None:
            query += " AND kind = :kind"
            params["kind"] = f.kind.code

        if f.max_duration is not None:
            query += " AND duration <= :max_duration"
            params["max_duration"] = f.max_duration

        if f.uncompleted_only:
            query += " AND completed_at IS NULL"
        elif f.recently_completed or f.long_ago_completed:
            query += " AND completed_at IS NOT NULL"

        query += " ORDER BY created_at DESC"

        with self.conn:
            rows = self.conn.execute(query, params).fetchall()
        return [Resource(**dict(row)) for row in rows]

    def _build_insert_query(self) -> str:
        cols = ", ".join(self.COLUMNS)
        placeholders = ", ".join(f":{col}" for col in self.COLUMNS)
        return f"INSERT INTO resources ({cols}) VALUES ({placeholders})"

    def _build_update_query(self) -> str:
        sets = ", ".join(f"{col} = :{col}" for col in self.COLUMNS)
        return f"UPDATE resources SET {sets} WHERE id = :id"


class UserDB:
    def __init__(self, path: str = "data/database.db"):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

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
                "SELECT is_active FROM users WHERE tg_id = ?", (tg_id,)
            ).fetchone()
        return bool(row and row[0])

    def delete(self, tg_id: int) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM users WHERE tg_id = ?", (tg_id,))

    def delete_all_users(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM users")
            self.conn.execute("DELETE FROM sqlite_sequence WHERE name='users'")

    def get_user(self, tg_id: int) -> Optional[User]:
        with self.conn:
            row = self.conn.execute(
                "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
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

    def get_user_by_username(self, username: str) -> Optional[User]:
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


class StatsDB:
    def __init__(self, path: str = "data/database.db"):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def upsert_daily_stats(
        self,
        date: str,
        new_users: int = 0,
        active_users: int = 0,
        new_resources: int = 0,
        banned_users: int = 0,
        total_users: int = 0,
        total_resources: int = 0,
    ) -> None:
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO daily_stats (
                    date, new_users, active_users, new_resources,
                    banned_users, total_users, total_resources
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    new_users = new_users + excluded.new_users,
                    active_users = excluded.active_users,
                    new_resources = new_resources + excluded.new_resources,
                    banned_users = excluded.banned_users,
                    total_users = excluded.total_users,
                    total_resources = excluded.total_resources
                """,
                (
                    date,
                    new_users,
                    active_users,
                    new_resources,
                    banned_users,
                    total_users,
                    total_resources,
                ),
            )

    def get_stats_for_period(self, since: str, until: str) -> dict:
        with self.conn:
            row = self.conn.execute(
                """
                SELECT
                    COALESCE(SUM(new_users), 0) as new_users,
                    COALESCE(SUM(new_resources), 0) as new_resources,
                    COALESCE(SUM(banned_users), 0) as banned_users,
                    COALESCE(MAX(total_users), 0) as total_users,
                    COALESCE(MAX(total_resources), 0) as total_resources
                FROM daily_stats
                WHERE date BETWEEN ? AND ?
                """,
                (since, until),
            ).fetchone()
        return dict(row)

    def get_active_users_for_period(self, since: str, until: str) -> int:
        with self.conn:
            row = self.conn.execute(
                """
                SELECT COALESCE(MAX(active_users), 0)
                FROM daily_stats
                WHERE date BETWEEN ? AND ?
                """,
                (since, until),
            ).fetchone()
        return row[0] if row else 0

    def get_total_new_users(self) -> int:
        with self.conn:
            return self.conn.execute(
                "SELECT COALESCE(SUM(new_users), 0) FROM daily_stats"
            ).fetchone()[0]

    def get_total_new_resources(self) -> int:
        with self.conn:
            return self.conn.execute(
                "SELECT COALESCE(SUM(new_resources), 0) FROM daily_stats"
            ).fetchone()[0]

    def get_total_banned_users(self) -> int:
        with self.conn:
            return self.conn.execute(
                "SELECT COALESCE(SUM(banned_users), 0) FROM daily_stats"
            ).fetchone()[0]

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
