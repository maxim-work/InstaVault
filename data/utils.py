import sqlite3


def start_db(path: str = "data/database.db") -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL UNIQUE,
                username TEXT,
                first_name TEXT NOT NULL,
                last_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                last_active_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            INSERT OR IGNORE INTO users (id, tg_id, first_name)
            VALUES (1, 0, 'cli_user')
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL,
                description TEXT DEFAULT NULL,
                resource_type TEXT NOT NULL DEFAULT 'other',
                platform TEXT NOT NULL DEFAULT 'other',
                kind TEXT NOT NULL DEFAULT 'other',
                external_id TEXT DEFAULT NULL,
                url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'to_teach',
                tags TEXT NOT NULL DEFAULT '[]',
                my_notes TEXT,
                my_rating INTEGER,
                engagement INTEGER,
                views INTEGER,
                duration INTEGER,
                published_at DATETIME,
                completed_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tg_id) REFERENCES users(tg_id) ON DELETE CASCADE
            )
        """)

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_resources_tg_id ON resources(tg_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_resources_status ON resources(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_resources_resource_type ON resources(resource_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_resources_external_id ON resources(external_id)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_resources_user_url ON resources(tg_id, url)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_resources_created_at ON resources(created_at)"
        )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                new_users INTEGER NOT NULL DEFAULT 0,
                active_users INTEGER NOT NULL DEFAULT 0,
                new_resources INTEGER NOT NULL DEFAULT 0,
                banned_users INTEGER NOT NULL DEFAULT 0,
                total_users INTEGER NOT NULL DEFAULT 0,
                total_resources INTEGER NOT NULL DEFAULT 0,
                UNIQUE(date)
            )
        """)

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date)"
        )
