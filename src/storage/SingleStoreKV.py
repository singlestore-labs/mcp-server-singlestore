import json
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence, SupportsFloat

import singlestoredb as s2
from key_value.aio.protocols import AsyncKeyValue


class SingleStoreKV(AsyncKeyValue):
    """A key-value store implementation using SingleStoreDB."""

    _DEFAULT_COLLECTION = "default"
    _TABLE_NAME = "mcp_kv_store"

    def __init__(self, connection_str: str):
        """Initialize the SingleStoreKV store.

        Args:
            connection_str: The SingleStoreDB connection string.
        """
        self.connection_str = connection_str
        self._create_table_task = self._create_table_if_not_exists()

    def _get_conn(self):
        return s2.connect(self.connection_str)  # type: ignore

    def _create_table_if_not_exists(self) -> None:
        """Create the key-value table if it does not exist."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._TABLE_NAME} (
                        collection VARCHAR(255) NOT NULL,
                        key_id VARCHAR(255) NOT NULL,
                        value JSON NOT NULL,
                        expires_at DATETIME(6),
                        PRIMARY KEY (collection, key_id)
                    );
                    """,
                )

    # Get methods
    async def get(
        self,
        key: str,
        *,
        collection: str | None = None,
    ) -> dict[str, Any] | None:
        """Retrieve a value by key from the specified collection."""
        coll = collection or self._DEFAULT_COLLECTION
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT value FROM {self._TABLE_NAME} WHERE key_id = %s AND collection = %s AND (expires_at IS NULL OR expires_at > NOW())",
                    (key, coll),
                )
                row = cur.fetchone()
                if row:
                    return row[0]
                return None

    async def get_many(
        self, keys: Sequence[str], *, collection: str | None = None
    ) -> list[dict[str, Any] | None]:
        """Retrieve multiple values by key."""
        if not keys:
            return []
        coll = collection or self._DEFAULT_COLLECTION
        placeholders = ", ".join(["%s"] * len(keys))
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT key_id, value FROM {self._TABLE_NAME} WHERE key_id IN ({placeholders}) AND collection = %s AND (expires_at IS NULL OR expires_at > NOW())",
                    (*keys, coll),
                )
                rows = cur.fetchall()

                # Ensure the results are in the same order as the input keys
                results_map = {row[0]: row[1] for row in rows}
                return [results_map.get(key) for key in keys]

    # Put methods
    async def put(
        self,
        key: str,
        value: Mapping[str, Any],
        *,
        collection: str | None = None,
        ttl: SupportsFloat | None = None,
    ) -> None:
        """Store a key-value pair."""
        coll = collection or self._DEFAULT_COLLECTION
        expires_at = None
        if ttl is not None:
            expires_at = datetime.now() + timedelta(seconds=float(ttl))

        json_value = json.dumps(value)

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._TABLE_NAME} (collection, key_id, value, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE value = VALUES(value), expires_at = VALUES(expires_at)
                    """,
                    (coll, key, json_value, expires_at),
                )

    async def put_many(
        self,
        keys: Sequence[str],
        values: Sequence[Mapping[str, Any]],
        *,
        collection: str | None = None,
        ttl: SupportsFloat | None = None,
    ) -> None:
        """Store multiple key-value pairs."""
        if not keys:
            return
        if len(keys) != len(values):
            raise ValueError("The number of keys must match the number of values.")

        coll = collection or self._DEFAULT_COLLECTION
        expires_at = None
        if ttl is not None:
            expires_at = datetime.now() + timedelta(seconds=float(ttl))

        records = [
            (coll, key, json.dumps(value), expires_at)
            for key, value in zip(keys, values)
        ]

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    f"""
                    INSERT INTO {self._TABLE_NAME} (collection, key_id, value, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE value = VALUES(value), expires_at = VALUES(expires_at)
                    """,
                    records,
                )

    # Delete methods
    async def delete(self, key: str, *, collection: str | None = None) -> bool:
        """Delete a key-value pair."""
        coll = collection or self._DEFAULT_COLLECTION
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self._TABLE_NAME} WHERE key_id = %s AND collection = %s",
                    (key, coll),
                )
                return cur.rowcount > 0

    async def delete_many(
        self, keys: Sequence[str], *, collection: str | None = None
    ) -> int:
        """Delete multiple key-value pairs."""
        if not keys:
            return 0
        coll = collection or self._DEFAULT_COLLECTION
        placeholders = ", ".join(["%s"] * len(keys))
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self._TABLE_NAME} WHERE key_id IN ({placeholders}) AND collection = %s",
                    (*keys, coll),
                )
                return cur.rowcount

    # TTL methods
    async def ttl(
        self, key: str, *, collection: str | None = None
    ) -> tuple[dict[str, Any] | None, float | None]:
        """Retrieve the value and TTL information for a key-value pair."""
        coll = collection or self._DEFAULT_COLLECTION
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT value, expires_at FROM {self._TABLE_NAME} WHERE key_id = %s AND collection = %s",
                    (key, coll),
                )
                row = cur.fetchone()
                if row:
                    value, expires_at = row
                    if expires_at:
                        if expires_at > datetime.now():
                            ttl = (expires_at - datetime.now()).total_seconds()
                            return value, ttl
                        else:
                            # Key has expired
                            return None, None
                    return value, None
                return None, None

    async def ttl_many(
        self, keys: Sequence[str], *, collection: str | None = None
    ) -> list[tuple[dict[str, Any] | None, float | None]]:
        """Retrieve multiple values and TTL information."""
        if not keys:
            return []
        coll = collection or self._DEFAULT_COLLECTION
        placeholders = ", ".join(["%s"] * len(keys))
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT key_id, value, expires_at FROM {self._TABLE_NAME} WHERE key_id IN ({placeholders}) AND collection = %s",
                    (*keys, coll),
                )
                rows = cur.fetchall()
                results_map: dict[str, tuple[dict[str, Any], datetime | None]] = {
                    row[0]: (row[1], row[2]) for row in rows
                }

                results: list[tuple[dict[str, Any] | None, float | None]] = []
                for key in keys:
                    if key in results_map:
                        value, expires_at = results_map[key]
                        if expires_at:
                            if expires_at > datetime.now():
                                ttl = (expires_at - datetime.now()).total_seconds()
                                results.append((value, ttl))
                            else:
                                results.append((None, None))
                        else:
                            results.append((value, None))
                    else:
                        results.append((None, None))
                return results
