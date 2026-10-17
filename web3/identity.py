
"""
NOVEAM Web3 Identity Service
Version: 0.1.0

Links verified EVM wallets to existing NOVEAM users.

Uses a separate SQLite database for wallet mappings.
Does not modify existing NOVEAM databases.
"""

import os
import sqlite3
import threading
from datetime import datetime, timezone

from web3 import Web3


class IdentityError(Exception):
    pass


class NoveamIdentity:
    def __init__(self, database_path=None):
        self.database_path = database_path or os.getenv(
            "NOVEAM_IDENTITY_DB_PATH",
            "noveam_identity.db"
        )
        self._lock = threading.RLock()

    def _connect(self):
        conn = sqlite3.connect(
            self.database_path,
            timeout=15
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=15000")
        return conn

    def initialize(self):
        """Create wallet mapping table if missing."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS
                    wallet_identities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        wallet_address TEXT NOT NULL UNIQUE,
                        chain_id INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        UNIQUE(user_id, wallet_address)
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS
                    idx_wallet_user
                    ON wallet_identities(user_id)
                """)

    @staticmethod
    def normalize_wallet(address):
        if not isinstance(address, str):
            raise IdentityError("Invalid wallet address")

        if not Web3.is_address(address):
            raise IdentityError("Invalid wallet address")

        return Web3.to_checksum_address(address)

    @staticmethod
    def validate_user(user_id):
        if not isinstance(user_id, str) or not user_id.strip():
            raise IdentityError("Invalid user ID")

        if len(user_id) > 128:
            raise IdentityError("User ID too long")

        return user_id.strip()

    def link_wallet(
        self,
        user_id,
        wallet_address,
        chain_id,
        *,
        verified=False
    ):
        """
        Link a wallet to an existing NOVEAM account.

        Must be called only by a trusted backend
        after Firebase authentication and fresh
        wallet signature verification.

        Never accept 'verified' from client JSON.
        """

        if verified is not True:
            raise IdentityError(
                "Wallet ownership verification required"
            )

        user_id = self.validate_user(user_id)
        wallet = self.normalize_wallet(wallet_address)

        if chain_id not in (1, 56, 97, 11155111):
            raise IdentityError("Unsupported chain")

        created_at = datetime.now(
            timezone.utc
        ).isoformat()

        with self._lock:
            try:
                with self._connect() as conn:
                    existing = conn.execute(
                        """
                        SELECT user_id
                        FROM wallet_identities
                        WHERE wallet_address = ?
                        """,
                        (wallet,)
                    ).fetchone()

                    if existing:
                        if existing["user_id"] != user_id:
                            raise IdentityError(
                                "Wallet already linked to another user"
                            )

                        return {
                            "linked": True,
                            "already_linked": True,
                            "wallet_address": wallet
                        }

                    conn.execute(
                        """
                        INSERT INTO wallet_identities
                        (user_id, wallet_address,
                         chain_id, created_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            wallet,
                            chain_id,
                            created_at
                        )
                    )

            except sqlite3.IntegrityError as exc:
                raise IdentityError(
                    "Wallet already linked"
                ) from exc

        return {
            "linked": True,
            "already_linked": False,
            "user_id": user_id,
            "wallet_address": wallet,
            "chain_id": chain_id
        }

    def get_user_wallets(self, user_id):
        """List wallets linked to a NOVEAM user."""

        user_id = self.validate_user(user_id)

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT wallet_address,
                       chain_id,
                       created_at
                FROM wallet_identities
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            ).fetchall()

        return [dict(row) for row in rows]

    def get_wallet_owner(self, wallet_address):
        """Look up the NOVEAM user linked to a wallet."""

        wallet = self.normalize_wallet(wallet_address)

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT user_id
                FROM wallet_identities
                WHERE wallet_address = ?
                """,
                (wallet,)
            ).fetchone()

        if row is None:
            return None

        return row["user_id"]

    def unlink_wallet(
        self,
        user_id,
        wallet_address
    ):
        """
        Remove a wallet link.

        Caller must authenticate and authorize
        the NOVEAM user before invoking.
        """

        user_id = self.validate_user(user_id)
        wallet = self.normalize_wallet(wallet_address)

        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM wallet_identities
                    WHERE user_id = ?
                    AND wallet_address = ?
                    """,
                    (user_id, wallet)
                )

                removed = cursor.rowcount > 0

        return {
            "unlinked": removed,
            "wallet_address": wallet
        }
