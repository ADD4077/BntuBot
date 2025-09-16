import json
import aiosqlite
from typing import Dict, Optional, Any
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.fsm.state import State
from util.config import states_db_path


class SQLiteStorage(BaseStorage):
    def __init__(
            self,
            db_path: str = states_db_path,
            table_name: str = "states"
    ):
        self.db_path = db_path
        self.table_name = table_name
        self.connection = None

    async def create_table(self) -> None:
        """Create the necessary table if it doesn't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    storage_key TEXT PRIMARY KEY,
                    state TEXT,
                    data TEXT
                )
            """
            )
            await db.commit()

    async def get_connection(self):
        """Get a database connection, creating one if needed"""
        if self.connection is None:
            self.connection = await aiosqlite.connect(self.db_path)
            await self.create_table()
        return self.connection

    async def set_state(self, key: StorageKey, state: State | str | None = None) -> None:
        """Set state for specified key"""
        conn = await self.get_connection()
        storage_key_str = str(key)

        if state is None:
            await conn.execute(
                f"DELETE FROM {self.table_name} WHERE storage_key = ?",
                (storage_key_str,)
            )
        else:
            state_str = state.state if isinstance(state, State) else str(state)

            cursor = await conn.execute(
                f"SELECT * FROM {self.table_name} WHERE storage_key = ?",
                (storage_key_str,)
            )
            exists = await cursor.fetchone()

            if exists:
                await conn.execute(
                    f"UPDATE {self.table_name} SET state = ? WHERE storage_key = ?",
                    (state_str, storage_key_str)
                )
            else:
                await conn.execute(
                    f"INSERT INTO {self.table_name} (storage_key, state, data) VALUES (?, ?, ?)",
                    (storage_key_str, state_str, "{}")
                )

        await conn.commit()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        """Get key state"""
        conn = await self.get_connection()
        storage_key_str = str(key)

        cursor = await conn.execute(
            f"SELECT state FROM {self.table_name} WHERE storage_key = ?",
            (storage_key_str,)
        )
        result = await cursor.fetchone()

        return result[0] if result else None

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        """Write data (replace)"""
        conn = await self.get_connection()
        storage_key_str = str(key)
        data_json = json.dumps(data)

        cursor = await conn.execute(
            f"SELECT * FROM {self.table_name} WHERE storage_key = ?",
            (storage_key_str,)
        )
        exists = await cursor.fetchone()

        if exists:
            await conn.execute(
                f"UPDATE {self.table_name} SET data = ? WHERE storage_key = ?",
                (data_json, storage_key_str)
            )
        else:
            await conn.execute(
                f"INSERT INTO {self.table_name} (storage_key, state, data) VALUES (?, ?, ?)",
                (storage_key_str, None, data_json)
            )

        await conn.commit()

    async def get_data(self, key: StorageKey) -> Dict[str, Any]:
        """Get current data for key"""
        conn = await self.get_connection()
        storage_key_str = str(key)

        cursor = await conn.execute(
            f"SELECT data FROM {self.table_name} WHERE storage_key = ?",
            (storage_key_str,)
        )
        result = await cursor.fetchone()

        if result and result[0]:
            return json.loads(result[0])
        return {}

    async def update_data(self, key: StorageKey, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update data in the storage for key (like dict.update)"""
        current_data = await self.get_data(key)
        current_data.update(data)
        await self.set_data(key, current_data)
        return current_data

    async def close(self) -> None:
        """Close storage (database connection)"""
        if self.connection:
            await self.connection.close()
            self.connection = None
