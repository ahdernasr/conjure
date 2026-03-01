import aiosqlite
from .config import settings


async def get_db():
    """Async generator yielding a database connection."""
    db = await aiosqlite.connect(settings.DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Create tables if they don't exist."""
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS apps (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                theme_color TEXT DEFAULT '#6366f1',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        """)
        # Phase 3: Command Plane reads these to know app capabilities
        await db.execute("""
            CREATE TABLE IF NOT EXISTS app_schemas (
                app_id TEXT PRIMARY KEY,
                schema_json TEXT DEFAULT '{}',
                FOREIGN KEY (app_id) REFERENCES apps(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                version INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (app_id) REFERENCES apps(id) ON DELETE CASCADE
            )
        """)
        # Migration: add version column to existing apps
        try:
            await db.execute("ALTER TABLE apps ADD COLUMN version INTEGER DEFAULT 1")
        except Exception:
            pass  # Column already exists

        await db.commit()
