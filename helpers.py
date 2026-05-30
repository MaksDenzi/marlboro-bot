"""
Marlboro Project — Helper utilities
"""

import time
import random
from typing import Optional


def ts_now() -> int:
    return int(time.time())


def cooldown_remaining(last_ts: Optional[int], cooldown_secs: int) -> int:
    """Returns remaining seconds (0 if ready)."""
    if last_ts is None:
        return 0
    elapsed = ts_now() - last_ts
    return max(0, cooldown_secs - elapsed)


def format_cooldown(seconds: int) -> str:
    if seconds <= 0:
        return "Готово!"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h:
        parts.append(f"{h}ч")
    if m:
        parts.append(f"{m}м")
    if s and not h:
        parts.append(f"{s}с")
    return " ".join(parts) or "Готово!"


def weighted_choice(rewards: list) -> dict:
    """Pick a reward by 'chance' weights."""
    total = sum(r["chance"] for r in rewards)
    r = random.uniform(0, total)
    running = 0.0
    for reward in rewards:
        running += reward["chance"]
        if r <= running:
            return reward
    return rewards[-1]


def roll_slots() -> tuple[str, str, str]:
    symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "⭐", "🔔"]
    return tuple(random.choice(symbols) for _ in range(3))


def slots_result(s1: str, s2: str, s3: str) -> tuple[float, str]:
    """Returns (multiplier, message)."""
    if s1 == s2 == s3:
        if s3 == "💎":
            return 50.0, "💎 ДЖЕКПОТ! АЛМАЗ! 💎"
        if s3 == "7️⃣":
            return 10.0, "7️⃣ УДАЧА! 7️⃣"
        if s3 == "⭐":
            return 7.0, "⭐ Три звезды! ⭐"
        return 5.0, "🎉 Три одинаковых!"
    if s1 == s2 or s2 == s3 or s1 == s3:
        return 1.5, "🎊 Два одинаковых!"
    return 0.0, "😞 Нет совпадений"


def blackjack_card() -> tuple[str, int]:
    suits = ["♠️", "♥️", "♦️", "♣️"]
    ranks = [("2", 2), ("3", 3), ("4", 4), ("5", 5), ("6", 6), ("7", 7),
             ("8", 8), ("9", 9), ("10", 10), ("J", 10), ("Q", 10), ("K", 10), ("A", 11)]
    suit = random.choice(suits)
    rank, val = random.choice(ranks)
    return f"{rank}{suit}", val


def blackjack_total(cards: list[int]) -> int:
    total = sum(cards)
    aces = cards.count(11)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def generate_promo_code(length: int = 8) -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(chars, k=length))


def paginate(items: list, page: int, per_page: int = 10) -> tuple[list, int]:
    """Returns (page_items, total_pages)."""
    total = max(1, (len(items) + per_page - 1) // per_page)
    start = page * per_page
    return items[start: start + per_page], total


def mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'


WORK_JOBS = [
    {"name": "Грузчик", "min_coins": 80, "max_coins": 150, "xp": 20,
     "texts": ["Разгрузил фуру с товарами", "Перетаскал ящики на склад"]},
    {"name": "Курьер", "min_coins": 100, "max_coins": 200, "xp": 25,
     "texts": ["Доставил посылки по городу", "Привёз заказ клиенту"]},
    {"name": "Строитель", "min_coins": 120, "max_coins": 250, "xp": 30,
     "texts": ["Построил стену на объекте", "Уложил плитку в новом здании"]},
    {"name": "Повар", "min_coins": 150, "max_coins": 300, "xp": 35,
     "texts": ["Приготовил блюда на банкет", "Сварил борщ для ресторана"]},
    {"name": "Программист", "min_coins": 200, "max_coins": 500, "xp": 50,
     "texts": ["Написал скрипт автоматизации", "Исправил баги в проекте"]},
    {"name": "Врач", "min_coins": 250, "max_coins": 600, "xp": 60,
     "texts": ["Принял пациентов в клинике", "Сделал операцию"]},
    {"name": "Адвокат", "min_coins": 300, "max_coins": 800, "xp": 70,
     "texts": ["Выиграл судебный процесс", "Составил договор для клиента"]},
    {"name": "Пилот", "min_coins": 500, "max_coins": 1200, "xp": 100,
     "texts": ["Совершил рейс в другой город", "Обучил нового пилота"]},
]

MINE_RESOURCES = [
    {"item_id": 26, "name": "Уголь",      "emoji": "🪨", "chance": 40.0, "min": 1, "max": 5},
    {"item_id": 27, "name": "Железо",     "emoji": "⚙️", "chance": 30.0, "min": 1, "max": 3},
    {"item_id": 28, "name": "Золото",     "emoji": "🥇", "chance": 15.0, "min": 1, "max": 2},
    {"item_id": 29, "name": "Изумруд",    "emoji": "💚", "chance": 8.0,  "min": 1, "max": 1},
    {"item_id": 30, "name": "Рубин",      "emoji": "❤️", "chance": 4.5,  "min": 1, "max": 1},
    {"item_id": 31, "name": "Алмаз",      "emoji": "💎", "chance": 2.0,  "min": 1, "max": 1},
    {"item_id": 13, "name": "Мал. зелье", "emoji": "🧪", "chance": 0.5,  "min": 1, "max": 1},
]

BUSINESS_TYPES = {
    "bakery":    {"name": "🥖 Пекарня",      "buy_price": 5_000,   "base_income": 200,  "upgrade_mult": 1.5},
    "restaurant":{"name": "🍽️ Ресторан",     "buy_price": 15_000,  "base_income": 600,  "upgrade_mult": 1.5},
    "hotel":     {"name": "🏨 Отель",         "buy_price": 40_000,  "base_income": 1500, "upgrade_mult": 1.6},
    "factory":   {"name": "🏭 Завод",         "buy_price": 100_000, "base_income": 4000, "upgrade_mult": 1.7},
    "casino_biz":{"name": "🎰 Казино",        "buy_price": 250_000, "base_income": 10000,"upgrade_mult": 1.8},
    "bank_biz":  {"name": "🏦 Банк",          "buy_price": 500_000, "base_income": 25000,"upgrade_mult": 2.0},
}

RP_ACTIONS = {
    "hug":       {"text": "{from} нежно обнял(а) {to} 🤗", "emoji": "🤗"},
    "wave":      {"text": "{from} помахал(а) {to} рукой 👋", "emoji": "👋"},
    "kiss":      {"text": "{from} поцеловал(а) {to} в щёчку 😘", "emoji": "😘"},
    "punch":     {"text": "{from} ударил(а) {to} кулаком 👊", "emoji": "👊"},
    "handshake": {"text": "{from} пожал(а) руку {to} 🤝", "emoji": "🤝"},
    "laugh":     {"text": "{from} засмеялся(лась) над {to} 😄", "emoji": "😄"},
    "dance":     {"text": "{from} потанцевал(а) вместе с {to} 🎵", "emoji": "🎵"},
    "cry":       {"text": "{from} поплакал(а) на плече у {to} 😭", "emoji": "😭"},
    "slap":      {"text": "{from} дал(а) пощёчину {to} 👋💢", "emoji": "💢"},
    "feed":      {"text": "{from} угостил(а) {to} вкусняшкой 🍬", "emoji": "🍬"},
    "gift":      {"text": "{from} подарил(а) подарок {to} 🎁", "emoji": "🎁"},
    "highfive":  {"text": "{from} дал(а) «пятёрку» {to} ✋", "emoji": "✋"},
}

ACHIEVEMENTS_DEF = {
    "first_login":   {"name": "🌟 Первый вход", "desc": "Впервые вошёл в игру"},
    "lvl5":          {"name": "📈 5 уровень", "desc": "Достиг 5 уровня"},
    "lvl10":         {"name": "📈 10 уровень", "desc": "Достиг 10 уровня"},
    "lvl25":         {"name": "🏆 25 уровень", "desc": "Достиг 25 уровня"},
    "rich1000":      {"name": "💰 Тысячник", "desc": "Накопил 1 000 монет"},
    "rich10000":     {"name": "💰 Десятитысячник", "desc": "Накопил 10 000 монет"},
    "rich100000":    {"name": "💎 Миллионер", "desc": "Накопил 100 000 монет"},
    "pvp_first":     {"name": "⚔️ Первая победа", "desc": "Победил в первой дуэли"},
    "pvp10":         {"name": "⚔️ Ветеран", "desc": "Выиграл 10 дуэлей"},
    "pvp50":         {"name": "🏆 Чемпион", "desc": "Выиграл 50 дуэлей"},
    "daily7":        {"name": "📅 Неделя подряд", "desc": "7 дней ежедневных бонусов"},
    "daily30":       {"name": "📅 Месяц подряд", "desc": "30 дней ежедневных бонусов"},
    "clan_created":  {"name": "🏴 Основатель", "desc": "Создал клан"},
    "married":       {"name": "💍 Женат/Замужем", "desc": "Вступил(а) в брак"},
    "referral1":     {"name": "👥 Вербовщик", "desc": "Пригласил 1 реферала"},
    "referral10":    {"name": "👥 Агент", "desc": "Пригласил 10 рефералов"},
    "miner":         {"name": "⛏️ Шахтёр", "desc": "Добыл 100 ресурсов"},
    "farmer":        {"name": "🌾 Фермер", "desc": "Собрал 50 урожаев"},
    "businessman":   {"name": "💼 Бизнесмен", "desc": "Купил первый бизнес"},
    "legendary_item":{"name": "🌟 Коллекционер", "desc": "Получил легендарный предмет"},
}
