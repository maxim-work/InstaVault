from data.db.base import BaseDB


class StatsDB(BaseDB):
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
            row = self.conn.execute(
                "SELECT COALESCE(SUM(new_users), 0) FROM daily_stats"
            ).fetchone()
        return row[0] if row else 0

    def get_total_new_resources(self) -> int:
        with self.conn:
            row = self.conn.execute(
                "SELECT COALESCE(SUM(new_resources), 0) FROM daily_stats"
            ).fetchone()
        return row[0] if row else 0

    def get_total_banned_users(self) -> int:
        with self.conn:
            row = self.conn.execute(
                "SELECT COALESCE(SUM(banned_users), 0) FROM daily_stats"
            ).fetchone()
        return row[0] if row else 0
