"""
Marlboro Project — Configuration Module
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot credentials ──────────────────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OWNER_ID: int = int(os.getenv("OWNER_ID", "5341321001"))
LOG_GROUP_ID: int = int(os.getenv("LOG_GROUP_ID", "0"))

# ── Project info ─────────────────────────────────────────────────────────────
BOT_NAME: str = os.getenv("BOT_NAME", "Marlboro Project")
BOT_VERSION: str = os.getenv("BOT_VERSION", "1.0.0")
PROJECT_CHANNEL = "https://t.me/MarlboroProject_RPG"
PROJECT_CHAT = "https://t.me/MarlboroProjectChat"

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "data/marlboro.db")
BACKUP_DIR: str = "backups"
LOG_FILE: str = "logs/marlboro.log"

# ── Economy ──────────────────────────────────────────────────────────────────
STARTING_BALANCE: int = int(os.getenv("STARTING_BALANCE", "1000"))
DAILY_BONUS: int = int(os.getenv("DAILY_BONUS", "500"))
REFERRAL_BONUS: int = int(os.getenv("REFERRAL_BONUS", "750"))

# Work / Farm / Mining cooldowns (seconds)
WORK_COOLDOWN: int = int(os.getenv("WORK_COOLDOWN", "3600"))
FARM_COOLDOWN: int = int(os.getenv("FARM_COOLDOWN", "14400"))
MINE_COOLDOWN: int = int(os.getenv("MINE_COOLDOWN", "7200"))

# Anti-spam
SPAM_LIMIT: int = 5          # max messages per window
SPAM_WINDOW: int = 5         # seconds

# ── VIP prices (in-game currency) ────────────────────────────────────────────
VIP_SILVER_PRICE: int = int(os.getenv("VIP_SILVER_PRICE", "5000"))
VIP_GOLD_PRICE: int = int(os.getenv("VIP_GOLD_PRICE", "15000"))
VIP_PLATINUM_PRICE: int = int(os.getenv("VIP_PLATINUM_PRICE", "50000"))

# VIP bonuses (multipliers)
VIP_BONUSES = {
    "none":     {"xp": 1.0, "coins": 1.0, "drop": 1.0},
    "silver":   {"xp": 1.2, "coins": 1.2, "drop": 1.1},
    "gold":     {"xp": 1.5, "coins": 1.5, "drop": 1.25},
    "platinum": {"xp": 2.0, "coins": 2.0, "drop": 1.5},
}

# ── XP / Level system ────────────────────────────────────────────────────────
XP_PER_LEVEL_BASE: int = 100   # XP needed for level 1→2
XP_LEVEL_MULTIPLIER: float = 1.35

def xp_for_level(lvl: int) -> int:
    """Total XP needed to reach `lvl` from 0."""
    total = 0
    for i in range(1, lvl):
        total += int(XP_PER_LEVEL_BASE * (XP_LEVEL_MULTIPLIER ** (i - 1)))
    return total

def xp_to_next(lvl: int) -> int:
    return int(XP_PER_LEVEL_BASE * (XP_LEVEL_MULTIPLIER ** (lvl - 1)))

# ── Item rarities ─────────────────────────────────────────────────────────────
RARITIES = {
    "common":    {"emoji": "⬜", "color": "Обычный",     "multiplier": 1.0},
    "uncommon":  {"emoji": "🟩", "color": "Необычный",   "multiplier": 1.5},
    "rare":      {"emoji": "🟦", "color": "Редкий",      "multiplier": 2.5},
    "epic":      {"emoji": "🟪", "color": "Эпический",   "multiplier": 4.0},
    "legendary": {"emoji": "🟧", "color": "Легендарный", "multiplier": 8.0},
    "mythic":    {"emoji": "🔴", "color": "Мифический",  "multiplier": 15.0},
}

# ── Energy system ────────────────────────────────────────────────────────────
MAX_ENERGY: int = 100
ENERGY_REGEN_PER_HOUR: int = 10

# ── Casino limits ────────────────────────────────────────────────────────────
CASINO_MIN_BET: int = 10
CASINO_MAX_BET: int = 100_000

# ── Clan settings ────────────────────────────────────────────────────────────
CLAN_CREATE_PRICE: int = 10_000
CLAN_MAX_MEMBERS: int = 50

# ── Auction settings ─────────────────────────────────────────────────────────
AUCTION_FEE_PERCENT: float = 0.05   # 5% listing fee
AUCTION_MIN_PRICE: int = 100
AUCTION_MAX_DURATION_HOURS: int = 72

# ── Emoji palette ────────────────────────────────────────────────────────────
E = {
    "coin":       "💰",
    "bank":       "🏦",
    "gem":        "💎",
    "bag":        "🎒",
    "sword":      "⚔️",
    "shield":     "🛡️",
    "potion":     "🧪",
    "scroll":     "📜",
    "crown":      "👑",
    "star":       "⭐",
    "fire":       "🔥",
    "lightning":  "⚡",
    "heart":      "❤️",
    "skull":      "💀",
    "trophy":     "🏆",
    "map":        "🗺️",
    "house":      "🏠",
    "pick":       "⛏️",
    "farm":       "🌾",
    "factory":    "🏭",
    "dice":       "🎲",
    "card":       "🃏",
    "gift":       "🎁",
    "case":       "📦",
    "hammer":     "🔨",
    "lock":       "🔒",
    "key":        "🗝️",
    "warning":    "⚠️",
    "check":      "✅",
    "cross":      "❌",
    "info":       "ℹ️",
    "arrow":      "➡️",
    "up":         "⬆️",
    "down":       "⬇️",
    "id":         "🆔",
    "calendar":   "📅",
    "clock":      "🕐",
    "chart":      "📊",
    "rocket":     "🚀",
    "vip":        "💫",
    "family":     "👨‍👩‍👧‍👦",
    "ring":       "💍",
    "friends":    "🤝",
    "energy":     "⚡",
    "xp":         "🎯",
    "level":      "📈",
    "ban":        "🚫",
    "mute":       "🔇",
    "admin":      "🛠️",
    "log":        "📋",
    "divider":    "━━━━━━━━━━━━━━━",
}
