import json
import shutil
from pathlib import Path
from ..config import settings


class AppService:
    def __init__(self, db):
        self.db = db
        self.apps_dir = Path(settings.APPS_DIR)

    async def list_apps(self) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM apps WHERE status = 'active' ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_app(self, app_id: str) -> dict | None:
        cursor = await self.db.execute("SELECT * FROM apps WHERE id = ?", (app_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def create_app(
        self,
        app_id: str,
        name: str,
        description: str = "",
        theme_color: str = "#6366f1",
    ) -> dict:
        """Create app metadata in DB and directory on disk.
        Called by Phase 2 generator after code generation."""
        await self.db.execute(
            "INSERT INTO apps (id, name, description, theme_color) VALUES (?, ?, ?, ?)",
            (app_id, name, description, theme_color),
        )
        await self.db.commit()
        app_dir = self.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        return await self.get_app(app_id)

    async def delete_app(self, app_id: str) -> bool:
        app = await self.get_app(app_id)
        if not app:
            return False
        await self.db.execute("DELETE FROM apps WHERE id = ?", (app_id,))
        await self.db.commit()
        app_dir = self.apps_dir / app_id
        if app_dir.exists():
            shutil.rmtree(app_dir)
        return True

    async def sync_data(self, app_id: str, raw_body: bytes) -> None:
        """Write synced localStorage data to apps/{uuid}/data.json."""
        app_dir = self.apps_dir / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        data_path = app_dir / "data.json"
        data_path.write_bytes(raw_body)

    async def get_app_data(self, app_id: str) -> dict:
        """Read app data from disk. Used by Command Plane (Phase 3)."""
        data_path = self.apps_dir / app_id / "data.json"
        if not data_path.exists():
            return {}
        return json.loads(data_path.read_text())

    def get_app_html(self, app_id: str) -> str | None:
        """Read the generated HTML for an app."""
        html_path = self.apps_dir / app_id / "index.html"
        if not html_path.exists():
            return None
        return html_path.read_text(encoding="utf-8")

    async def update_theme(self, app_id: str, theme_color: str) -> None:
        """Update the theme color in the database."""
        await self.db.execute(
            "UPDATE apps SET theme_color = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (theme_color, app_id),
        )
        await self.db.commit()

    async def get_messages(self, app_id: str) -> list[dict]:
        """Get all chat messages for an app."""
        cursor = await self.db.execute(
            "SELECT id, role, content, version, created_at FROM chat_messages WHERE app_id = ? ORDER BY id ASC",
            (app_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def add_message(self, app_id: str, role: str, content: str, version: int | None = None) -> dict:
        """Add a chat message for an app."""
        cursor = await self.db.execute(
            "INSERT INTO chat_messages (app_id, role, content, version) VALUES (?, ?, ?, ?)",
            (app_id, role, content, version),
        )
        await self.db.commit()
        return {"id": cursor.lastrowid, "role": role, "content": content, "version": version}
