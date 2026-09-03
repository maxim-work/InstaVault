import sqlite3
from typing import Any

from core.exceptions import ResourceNotFoundError
from core.models.resource import Resource
from data.db.base import BaseDB
from data.exceptions import DuplicateResourceError
from data.filter import ResourceFilter, calculate_scores


class ResourceDB(BaseDB):
    COLUMNS = (
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
        "created_at",
    )

    def insert(self, resource: Resource) -> int:
        try:
            data = resource.to_db_dict()
            with self.conn:
                cursor = self.conn.execute(self._build_insert_query(), data)
                if cursor.lastrowid is None:
                    raise RuntimeError("Failed to insert resource")
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise DuplicateResourceError(resource.url) from None

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

    def get_resource(self, resource_id: int, tg_id: int) -> Resource | None:
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
            row = self.conn.execute("SELECT COUNT(*) FROM resources").fetchone()
        return row[0] if row else 0

    def search(
        self, tg_id: int, resource_filter: ResourceFilter | None = None
    ) -> list[tuple[Resource, int]]:
        if resource_filter is None:
            resource_filter = ResourceFilter(tg_id=tg_id)
        resources = self._get_candidates(resource_filter)
        return calculate_scores(resources, resource_filter)

    def export_urls(self, tg_id: int) -> list[str]:
        with self.conn:
            rows = self.conn.execute(
                "SELECT url FROM resources WHERE tg_id = ?", (tg_id,)
            ).fetchall()
        return [row["url"] for row in rows]

    def export_data(self, tg_id: int) -> list[Resource]:
        with self.conn:
            rows = self.conn.execute("SELECT * FROM resources WHERE tg_id = ?", (tg_id,)).fetchall()
        return [Resource(**dict(row)) for row in rows]

    def import_data(self, data: list[Resource], tg_id: int) -> tuple[int, int, list[str]]:
        count = 0
        errors = []

        with self.conn as conn:
            for resource in data:
                try:
                    resource_data = resource.to_db_dict()
                    resource_data["tg_id"] = tg_id
                    conn.execute(self._build_insert_query(), resource_data)
                    count += 1
                except sqlite3.IntegrityError:
                    errors.append(f"Дубликат: {resource.url}")
                except (ValueError, TypeError) as e:
                    errors.append(f"Ошибка данных: {e}")
                except Exception as e:  # noqa: BLE001
                    errors.append(f"{resource.url}: {e}")

        return count, len(data), errors

    def get_by_url(self, url: str, tg_id: int) -> Resource | None:
        with self.conn as conn:
            cursor = conn.execute(
                "SELECT * FROM resources WHERE url = ? AND tg_id = ?",
                (url, tg_id),
            )
            row = cursor.fetchone()
        return Resource(**dict(row)) if row else None

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
        return f"INSERT INTO resources ({cols}) VALUES ({placeholders})"  # noqa: S608

    def _build_update_query(self) -> str:
        sets = ", ".join(f"{col} = :{col}" for col in self.COLUMNS)
        return f"UPDATE resources SET {sets} WHERE id = :id"  # noqa: S608
