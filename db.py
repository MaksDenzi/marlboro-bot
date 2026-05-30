"""
Marlboro Project — Database Layer (aiosqlite)
All CREATE TABLE statements and CRUD helpers live here.
"""

import asyncio
import aiosqlite
import os
import logging
from typing import Optional, Any
from config import DB_PATH

logger = logging.getLogger(__name__)

# ── Singleton ────────────────────────────────────────────────────────────────
_db: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        raise RuntimeError("Database not initialised. Call Database.init() first.")
    return _db


class Database:
    """Async SQLite wrapper."""

    @classmethod
    async def init(cls) -> None:
        global _db
        os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
        _db = await aiosqlite.connect(DB_PATH, check_same_thread=False)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
        await cls._create_tables()
        await _db.commit()
        logger.info("Database initialised at %s", DB_PATH)

    @classmethod
    async def close(cls) -> None:
        global _db
        if _db:
            await _db.close()
            _db = None

    @classmethod
    async def _create_tables(cls) -> None:
        db = await get_db()

        # ── Users ────────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                username      TEXT,
                first_name    TEXT NOT NULL DEFAULT '',
                last_name     TEXT DEFAULT '',
                balance       INTEGER NOT NULL DEFAULT 1000,
                bank          INTEGER NOT NULL DEFAULT 0,
                level         INTEGER NOT NULL DEFAULT 1,
                xp            INTEGER NOT NULL DEFAULT 0,
                energy        INTEGER NOT NULL DEFAULT 100,
                health        INTEGER NOT NULL DEFAULT 100,
                max_health    INTEGER NOT NULL DEFAULT 100,
                attack        INTEGER NOT NULL DEFAULT 10,
                defense       INTEGER NOT NULL DEFAULT 5,
                vip_status    TEXT NOT NULL DEFAULT 'none',
                vip_expires   INTEGER DEFAULT NULL,
                is_banned     INTEGER NOT NULL DEFAULT 0,
                ban_reason    TEXT DEFAULT NULL,
                ban_expires   INTEGER DEFAULT NULL,
                is_muted      INTEGER NOT NULL DEFAULT 0,
                mute_expires  INTEGER DEFAULT NULL,
                referrer_id   INTEGER DEFAULT NULL,
                referrals     INTEGER NOT NULL DEFAULT 0,
                total_earned  INTEGER NOT NULL DEFAULT 0,
                total_spent   INTEGER NOT NULL DEFAULT 0,
                pvp_wins      INTEGER NOT NULL DEFAULT 0,
                pvp_losses    INTEGER NOT NULL DEFAULT 0,
                daily_streak  INTEGER NOT NULL DEFAULT 0,
                last_daily    INTEGER DEFAULT NULL,
                last_work     INTEGER DEFAULT NULL,
                last_farm     INTEGER DEFAULT NULL,
                last_mine     INTEGER DEFAULT NULL,
                last_seen     INTEGER DEFAULT NULL,
                registered_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                is_admin      INTEGER NOT NULL DEFAULT 0,
                admin_level   INTEGER NOT NULL DEFAULT 0,
                spouse_id     INTEGER DEFAULT NULL,
                FOREIGN KEY(referrer_id) REFERENCES users(user_id)
            )
        """)

        # ── Inventory ────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                item_id   INTEGER NOT NULL,
                amount    INTEGER NOT NULL DEFAULT 1,
                equipped  INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                UNIQUE(user_id, item_id)
            )
        """)

        # ── Shop items (custom admin-created) ────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS shop_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id     INTEGER NOT NULL UNIQUE,
                price       INTEGER NOT NULL,
                stock       INTEGER DEFAULT -1,
                is_active   INTEGER NOT NULL DEFAULT 1,
                added_at    INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            )
        """)

        # ── Clans ─────────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clans (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                tag         TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                owner_id    INTEGER NOT NULL,
                level       INTEGER NOT NULL DEFAULT 1,
                xp          INTEGER NOT NULL DEFAULT 0,
                balance     INTEGER NOT NULL DEFAULT 0,
                members     INTEGER NOT NULL DEFAULT 1,
                created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                FOREIGN KEY(owner_id) REFERENCES users(user_id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role    TEXT NOT NULL DEFAULT 'member',
                joined  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                PRIMARY KEY(clan_id, user_id),
                FOREIGN KEY(clan_id) REFERENCES clans(id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        # ── Duels / PvP ──────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS duels (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                challenger  INTEGER NOT NULL,
                opponent    INTEGER NOT NULL,
                bet         INTEGER NOT NULL DEFAULT 0,
                status      TEXT NOT NULL DEFAULT 'pending',
                winner      INTEGER DEFAULT NULL,
                created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                finished_at INTEGER DEFAULT NULL,
                FOREIGN KEY(challenger) REFERENCES users(user_id),
                FOREIGN KEY(opponent)   REFERENCES users(user_id)
            )
        """)

        # ── Auction ───────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS auction (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id   INTEGER NOT NULL,
                item_id     INTEGER NOT NULL,
                amount      INTEGER NOT NULL DEFAULT 1,
                start_price INTEGER NOT NULL,
                current_bid INTEGER NOT NULL DEFAULT 0,
                buyer_id    INTEGER DEFAULT NULL,
                status      TEXT NOT NULL DEFAULT 'active',
                expires_at  INTEGER NOT NULL,
                created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                FOREIGN KEY(seller_id) REFERENCES users(user_id)
            )
        """)

        # ── Trade offers ──────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id   INTEGER NOT NULL,
                offer_item_id   INTEGER,
                offer_amount    INTEGER DEFAULT 1,
                offer_coins     INTEGER DEFAULT 0,
                request_item_id INTEGER,
                request_amount  INTEGER DEFAULT 1,
                request_coins   INTEGER DEFAULT 0,
                status       TEXT NOT NULL DEFAULT 'pending',
                created_at   INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                FOREIGN KEY(from_user_id) REFERENCES users(user_id),
                FOREIGN KEY(to_user_id)   REFERENCES users(user_id)
            )
        """)

        # ── Farm plots ────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS farm_plots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                slot        INTEGER NOT NULL,
                seed_id     INTEGER DEFAULT NULL,
                planted_at  INTEGER DEFAULT NULL,
                ready_at    INTEGER DEFAULT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                UNIQUE(user_id, slot)
            )
        """)

        # ── Businesses ────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                type        TEXT NOT NULL,
                level       INTEGER NOT NULL DEFAULT 1,
                income      INTEGER NOT NULL DEFAULT 0,
                last_collect INTEGER DEFAULT NULL,
                purchased_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        # ── Promo codes ───────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code        TEXT PRIMARY KEY,
                reward_type TEXT NOT NULL DEFAULT 'coins',
                reward_amount INTEGER NOT NULL DEFAULT 0,
                reward_item_id INTEGER DEFAULT NULL,
                uses_left   INTEGER DEFAULT -1,
                used_count  INTEGER NOT NULL DEFAULT 0,
                expires_at  INTEGER DEFAULT NULL,
                created_by  INTEGER NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_uses (
                code    TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                used_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                PRIMARY KEY(code, user_id)
            )
        """)

        # ── Achievements ──────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                achievement TEXT NOT NULL,
                unlocked_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                UNIQUE(user_id, achievement),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        # ── Friends ───────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS friends (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                friend_id   INTEGER NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                UNIQUE(user_id, friend_id),
                FOREIGN KEY(user_id)   REFERENCES users(user_id),
                FOREIGN KEY(friend_id) REFERENCES users(user_id)
            )
        """)

        # ── RPG Events ───────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rpg_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                event_type  TEXT NOT NULL,
                reward_coins INTEGER DEFAULT 0,
                reward_xp   INTEGER DEFAULT 0,
                reward_item_id INTEGER DEFAULT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1,
                starts_at   INTEGER DEFAULT NULL,
                ends_at     INTEGER DEFAULT NULL,
                created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            )
        """)

        # ── Event participations ──────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS event_participants (
                event_id INTEGER NOT NULL,
                user_id  INTEGER NOT NULL,
                score    INTEGER NOT NULL DEFAULT 0,
                joined   INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                PRIMARY KEY(event_id, user_id)
            )
        """)

        # ── Staff roles ───────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS staff_roles (
                user_id   INTEGER PRIMARY KEY,
                role      TEXT NOT NULL DEFAULT 'tester',
                added_by  INTEGER NOT NULL,
                added_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        # ── Transaction log ───────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                type        TEXT NOT NULL,
                amount      INTEGER NOT NULL,
                description TEXT DEFAULT '',
                timestamp   INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        # ── Bot logs ──────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_logs (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                level     TEXT NOT NULL DEFAULT 'INFO',
                category  TEXT NOT NULL DEFAULT 'system',
                user_id   INTEGER DEFAULT NULL,
                message   TEXT NOT NULL,
                timestamp INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            )
        """)

        # ── Admin log ─────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id    INTEGER NOT NULL,
                action      TEXT NOT NULL,
                target_id   INTEGER DEFAULT NULL,
                details     TEXT DEFAULT '',
                timestamp   INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            )
        """)

        # ── Default shop items (seed) ─────────────────────────────────────────
        await db.execute("""
            INSERT OR IGNORE INTO shop_items (item_id, price, stock) VALUES
                (1, 150, -1),(2, 500, -1),(3, 1500, -1),(7, 200, -1),(8, 700, -1),
                (13, 50, -1),(14, 200, -1),(15, 600, -1),(18, 30, -1),(19, 50, -1),
                (20, 100, -1),(22, 300, -1),(23, 1000, -1),(32, 200, -1),(33, 800, -1),
                (34, 2500, -1),(35, 10000, -1),(39, 5000, 10),(40, 15000, 5),(41, 50000, 2)
        """)

        logger.info("All tables created/verified.")

    # ── User helpers ─────────────────────────────────────────────────────────

    @staticmethod
    async def get_user(user_id: int) -> Optional[aiosqlite.Row]:
        db = await get_db()
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone()

    @staticmethod
    async def create_user(user_id: int, username: str, first_name: str, last_name: str = "",
                          referrer_id: Optional[int] = None) -> None:
        db = await get_db()
        from config import STARTING_BALANCE
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, balance, referrer_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, STARTING_BALANCE, referrer_id))

        # initialise 3 farm plots
        for slot in range(3):
            await db.execute(
                "INSERT OR IGNORE INTO farm_plots (user_id, slot) VALUES (?, ?)", (user_id, slot)
            )
        await db.commit()

    @staticmethod
    async def update_user(user_id: int, **kwargs) -> None:
        if not kwargs:
            return
        db = await get_db()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [user_id]
        await db.execute(f"UPDATE users SET {sets} WHERE user_id = ?", vals)
        await db.commit()

    @staticmethod
    async def get_top_users(field: str = "balance", limit: int = 10):
        db = await get_db()
        allowed = {"balance", "level", "xp", "pvp_wins", "referrals", "total_earned"}
        if field not in allowed:
            field = "balance"
        async with db.execute(
            f"SELECT user_id, first_name, username, {field} FROM users WHERE is_banned = 0 ORDER BY {field} DESC LIMIT ?",
            (limit,)
        ) as cur:
            return await cur.fetchall()

    # ── Inventory helpers ─────────────────────────────────────────────────────

    @staticmethod
    async def get_inventory(user_id: int):
        db = await get_db()
        async with db.execute(
            "SELECT * FROM inventory WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchall()

    @staticmethod
    async def add_item(user_id: int, item_id: int, amount: int = 1) -> None:
        db = await get_db()
        await db.execute("""
            INSERT INTO inventory (user_id, item_id, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET amount = amount + excluded.amount
        """, (user_id, item_id, amount))
        await db.commit()

    @staticmethod
    async def remove_item(user_id: int, item_id: int, amount: int = 1) -> bool:
        db = await get_db()
        async with db.execute(
            "SELECT amount FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)
        ) as cur:
            row = await cur.fetchone()
        if not row or row["amount"] < amount:
            return False
        if row["amount"] == amount:
            await db.execute(
                "DELETE FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)
            )
        else:
            await db.execute(
                "UPDATE inventory SET amount = amount - ? WHERE user_id = ? AND item_id = ?",
                (amount, user_id, item_id)
            )
        await db.commit()
        return True

    @staticmethod
    async def get_item_in_inventory(user_id: int, item_id: int) -> Optional[aiosqlite.Row]:
        db = await get_db()
        async with db.execute(
            "SELECT * FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)
        ) as cur:
            return await cur.fetchone()

    # ── Economy helpers ───────────────────────────────────────────────────────

    @staticmethod
    async def add_balance(user_id: int, amount: int) -> None:
        db = await get_db()
        await db.execute(
            "UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id = ?",
            (amount, max(0, amount), user_id)
        )
        await db.execute(
            "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'credit', ?, 'balance_add')",
            (user_id, amount)
        )
        await db.commit()

    @staticmethod
    async def deduct_balance(user_id: int, amount: int) -> bool:
        db = await get_db()
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if not row or row["balance"] < amount:
            return False
        await db.execute(
            "UPDATE users SET balance = balance - ?, total_spent = total_spent + ? WHERE user_id = ?",
            (amount, amount, user_id)
        )
        await db.execute(
            "INSERT INTO transactions (user_id, type, amount, description) VALUES (?, 'debit', ?, 'balance_deduct')",
            (user_id, amount)
        )
        await db.commit()
        return True

    @staticmethod
    async def add_xp(user_id: int, xp: int) -> int:
        """Add XP and return new level (handles level-up)."""
        from config import xp_to_next
        db = await get_db()
        async with db.execute("SELECT level, xp FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return 1
        current_lvl, current_xp = row["level"], row["xp"]
        new_xp = current_xp + xp
        new_lvl = current_lvl
        while new_xp >= xp_to_next(new_lvl):
            new_xp -= xp_to_next(new_lvl)
            new_lvl += 1
        await db.execute(
            "UPDATE users SET level = ?, xp = ? WHERE user_id = ?", (new_lvl, new_xp, user_id)
        )
        await db.commit()
        return new_lvl

    # ── Clan helpers ──────────────────────────────────────────────────────────

    @staticmethod
    async def get_clan(clan_id: int) -> Optional[aiosqlite.Row]:
        db = await get_db()
        async with db.execute("SELECT * FROM clans WHERE id = ?", (clan_id,)) as cur:
            return await cur.fetchone()

    @staticmethod
    async def get_user_clan(user_id: int) -> Optional[aiosqlite.Row]:
        db = await get_db()
        async with db.execute("""
            SELECT c.*, cm.role FROM clans c
            JOIN clan_members cm ON c.id = cm.clan_id
            WHERE cm.user_id = ?
        """, (user_id,)) as cur:
            return await cur.fetchone()

    # ── Promo helpers ─────────────────────────────────────────────────────────

    @staticmethod
    async def get_promo(code: str) -> Optional[aiosqlite.Row]:
        db = await get_db()
        async with db.execute("SELECT * FROM promo_codes WHERE code = ?", (code,)) as cur:
            return await cur.fetchone()

    @staticmethod
    async def use_promo(code: str, user_id: int) -> bool:
        db = await get_db()
        async with db.execute(
            "SELECT 1 FROM promo_uses WHERE code = ? AND user_id = ?", (code, user_id)
        ) as cur:
            if await cur.fetchone():
                return False
        await db.execute("INSERT INTO promo_uses (code, user_id) VALUES (?, ?)", (code, user_id))
        await db.execute("UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?", (code,))
        await db.commit()
        return True

    # ── Auction helpers ───────────────────────────────────────────────────────

    @staticmethod
    async def get_active_auctions(limit: int = 20):
        db = await get_db()
        async with db.execute("""
            SELECT a.*, u.first_name as seller_name
            FROM auction a
            JOIN users u ON a.seller_id = u.user_id
            WHERE a.status = 'active' AND a.expires_at > strftime('%s','now')
            ORDER BY a.created_at DESC LIMIT ?
        """, (limit,)) as cur:
            return await cur.fetchall()

    # ── Logging helpers ───────────────────────────────────────────────────────

    # ── Staff roles CRUD ──────────────────────────────────────────────────────

    @staticmethod
    async def get_staff_role(user_id: int) -> Optional[str]:
        """Return 'admin' | 'tester' | None. Owner always returns 'owner'."""
        from config import OWNER_ID
        if user_id == OWNER_ID:
            return "owner"
        db = await get_db()
        async with db.execute(
            "SELECT role FROM staff_roles WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        return row["role"] if row else None

    @staticmethod
    async def add_staff_role(user_id: int, role: str, added_by: int) -> None:
        db = await get_db()
        await db.execute(
            "INSERT OR REPLACE INTO staff_roles (user_id, role, added_by) VALUES (?, ?, ?)",
            (user_id, role, added_by)
        )
        await db.commit()

    @staticmethod
    async def remove_staff_role(user_id: int) -> None:
        db = await get_db()
        await db.execute("DELETE FROM staff_roles WHERE user_id = ?", (user_id,))
        await db.commit()

    @staticmethod
    async def get_all_staff() -> list:
        db = await get_db()
        async with db.execute(
            "SELECT sr.user_id, sr.role, sr.added_at, u.first_name, u.username "
            "FROM staff_roles sr LEFT JOIN users u ON u.user_id = sr.user_id "
            "ORDER BY sr.role, sr.added_at"
        ) as cur:
            return await cur.fetchall()

    @staticmethod
    async def log(level: str, category: str, message: str, user_id: int = None) -> None:
        try:
            db = await get_db()
            await db.execute(
                "INSERT INTO bot_logs (level, category, user_id, message) VALUES (?, ?, ?, ?)",
                (level, category, user_id, message)
            )
            await db.commit()
        except Exception:
            pass

    @staticmethod
    async def admin_log(admin_id: int, action: str, target_id: int = None, details: str = "") -> None:
        try:
            db = await get_db()
            await db.execute(
                "INSERT INTO admin_logs (admin_id, action, target_id, details) VALUES (?, ?, ?, ?)",
                (admin_id, action, target_id, details)
            )
            await db.commit()
        except Exception:
            pass

    # ── Statistics ────────────────────────────────────────────────────────────

    @staticmethod
    async def get_stats() -> dict:
        db = await get_db()
        async with db.execute("SELECT COUNT(*) as cnt FROM users") as cur:
            users_total = (await cur.fetchone())["cnt"]
        async with db.execute("SELECT COUNT(*) as cnt FROM users WHERE is_banned = 0") as cur:
            users_active = (await cur.fetchone())["cnt"]
        async with db.execute("SELECT COUNT(*) as cnt FROM clans") as cur:
            clans_total = (await cur.fetchone())["cnt"]
        async with db.execute("SELECT SUM(balance) as s FROM users") as cur:
            total_money = (await cur.fetchone())["s"] or 0
        async with db.execute("SELECT COUNT(*) as cnt FROM auction WHERE status='active'") as cur:
            auctions = (await cur.fetchone())["cnt"]
        async with db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE last_seen > strftime('%s','now') - 300"
        ) as cur:
            online = (await cur.fetchone())["cnt"]
        return {
            "users_total": users_total,
            "users_active": users_active,
            "clans_total": clans_total,
            "total_money": total_money,
            "auctions": auctions,
            "online": online,
        }
