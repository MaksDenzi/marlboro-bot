"""
Marlboro Project — Inline Keyboards
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ── Main Menu ─────────────────────────────────────────────────────────────────
def main_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory"),
    )
    b.row(
        InlineKeyboardButton(text="💰 Экономика", callback_data="economy_menu"),
        InlineKeyboardButton(text="🏪 Магазин", callback_data="shop"),
    )
    b.row(
        InlineKeyboardButton(text="⚔️ PvP / Дуэли", callback_data="pvp_menu"),
        InlineKeyboardButton(text="🎲 Казино", callback_data="casino_menu"),
    )
    b.row(
        InlineKeyboardButton(text="⛏️ Майнинг", callback_data="mine"),
        InlineKeyboardButton(text="🌾 Ферма", callback_data="farm_menu"),
    )
    b.row(
        InlineKeyboardButton(text="💼 Бизнес", callback_data="business_menu"),
        InlineKeyboardButton(text="🏴 Кланы", callback_data="clan_menu"),
    )
    b.row(
        InlineKeyboardButton(text="📦 Кейсы", callback_data="cases_menu"),
        InlineKeyboardButton(text="🏛️ Аукцион", callback_data="auction_menu"),
    )
    b.row(
        InlineKeyboardButton(text="🏆 Топ игроков", callback_data="top_menu"),
        InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily"),
    )
    b.row(
        InlineKeyboardButton(text="👨‍👩‍👧‍👦 Семья / Друзья", callback_data="social_menu"),
        InlineKeyboardButton(text="🎭 RP Команды", callback_data="rp_menu"),
    )
    b.row(
        InlineKeyboardButton(text="💫 VIP", callback_data="vip_menu"),
        InlineKeyboardButton(text="🏅 Достижения", callback_data="achievements"),
    )
    b.row(
        InlineKeyboardButton(text="💼 Работа", callback_data="work"),
        InlineKeyboardButton(text="🔁 Обмен", callback_data="trade_menu"),
    )
    b.row(
        InlineKeyboardButton(text="🎟️ Промокод", callback_data="promo"),
        InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"),
    )
    b.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help"),
    )
    return b.as_markup()


def back_kb(callback: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)]
    ])


def back_and_refresh_kb(back: str, refresh: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data=refresh),
            InlineKeyboardButton(text="◀️ Назад", callback_data=back),
        ]
    ])


# ── Economy ───────────────────────────────────────────────────────────────────
def economy_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
        InlineKeyboardButton(text="🏦 Банк", callback_data="bank_menu"),
    )
    b.row(
        InlineKeyboardButton(text="📤 Перевести деньги", callback_data="transfer_start"),
        InlineKeyboardButton(text="📋 История транзакций", callback_data="tx_history"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


def bank_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="⬆️ Положить в банк", callback_data="bank_deposit"),
        InlineKeyboardButton(text="⬇️ Снять из банка", callback_data="bank_withdraw"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="economy_menu"))
    return b.as_markup()


# ── Shop ──────────────────────────────────────────────────────────────────────
def shop_kb(page: int = 0) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="⚔️ Оружие", callback_data="shop_cat:weapon"),
        InlineKeyboardButton(text="🛡️ Броня",  callback_data="shop_cat:armor"),
    )
    b.row(
        InlineKeyboardButton(text="🧪 Расходники",  callback_data="shop_cat:consumable"),
        InlineKeyboardButton(text="🌾 Семена",      callback_data="shop_cat:farm_seed"),
    )
    b.row(
        InlineKeyboardButton(text="⛏️ Инструменты", callback_data="shop_cat:mining_tool"),
        InlineKeyboardButton(text="🗝️ Ключи",       callback_data="shop_cat:key"),
    )
    b.row(
        InlineKeyboardButton(text="💫 VIP-карты", callback_data="shop_cat:vip"),
        InlineKeyboardButton(text="💎 Особые",    callback_data="shop_cat:special"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


# ── Casino ────────────────────────────────────────────────────────────────────
def casino_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🎰 Слоты",      callback_data="slots"),
        InlineKeyboardButton(text="🎲 Кости",      callback_data="dice_game"),
    )
    b.row(
        InlineKeyboardButton(text="🃏 Блэкджек",   callback_data="blackjack"),
        InlineKeyboardButton(text="🎡 Рулетка",    callback_data="roulette_menu"),
    )
    b.row(
        InlineKeyboardButton(text="🪙 Монетка",    callback_data="coinflip"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="casino_stats"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


def roulette_color_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🔴 Красное (2x)", callback_data="roulette:red"),
        InlineKeyboardButton(text="⚫ Чёрное (2x)", callback_data="roulette:black"),
    )
    b.row(
        InlineKeyboardButton(text="🟢 Зелёное (14x)", callback_data="roulette:green"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="casino_menu"),
    )
    return b.as_markup()


# ── PvP ───────────────────────────────────────────────────────────────────────
def pvp_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="⚔️ Начать дуэль",    callback_data="duel_start"),
        InlineKeyboardButton(text="📋 Мои дуэли",       callback_data="duel_list"),
    )
    b.row(
        InlineKeyboardButton(text="🏆 Рейтинг PvP",    callback_data="top_pvp"),
        InlineKeyboardButton(text="📊 Моя статистика",  callback_data="pvp_stats"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


def duel_accept_kb(duel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"duel_accept:{duel_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"duel_decline:{duel_id}"),
        ]
    ])


# ── Farm ──────────────────────────────────────────────────────────────────────
def farm_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🌱 Посадить", callback_data="farm_plant"),
        InlineKeyboardButton(text="🌾 Собрать урожай", callback_data="farm_harvest"),
    )
    b.row(
        InlineKeyboardButton(text="🗺️ Мои грядки", callback_data="farm_status"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"),
    )
    return b.as_markup()


# ── Business ──────────────────────────────────────────────────────────────────
def business_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🏭 Купить бизнес", callback_data="business_buy"),
        InlineKeyboardButton(text="💰 Собрать доход", callback_data="business_collect"),
    )
    b.row(
        InlineKeyboardButton(text="⬆️ Улучшить", callback_data="business_upgrade"),
        InlineKeyboardButton(text="📊 Мои бизнесы", callback_data="business_list"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


# ── Clan ──────────────────────────────────────────────────────────────────────
def clan_menu_kb(in_clan: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if in_clan:
        b.row(
            InlineKeyboardButton(text="🏴 Мой клан",   callback_data="clan_info"),
            InlineKeyboardButton(text="👥 Участники",  callback_data="clan_members"),
        )
        b.row(
            InlineKeyboardButton(text="💰 Казна клана", callback_data="clan_treasury"),
            InlineKeyboardButton(text="📜 Покинуть",    callback_data="clan_leave"),
        )
    else:
        b.row(
            InlineKeyboardButton(text="➕ Создать клан",  callback_data="clan_create"),
            InlineKeyboardButton(text="🔍 Найти клан",   callback_data="clan_search"),
        )
        b.row(
            InlineKeyboardButton(text="📋 Список кланов", callback_data="clan_list"),
        )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


# ── Auction ───────────────────────────────────────────────────────────────────
def auction_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🏛️ Активные лоты", callback_data="auction_list"),
        InlineKeyboardButton(text="➕ Выставить лот",  callback_data="auction_sell"),
    )
    b.row(
        InlineKeyboardButton(text="📋 Мои лоты", callback_data="auction_my"),
        InlineKeyboardButton(text="◀️ Назад",    callback_data="main_menu"),
    )
    return b.as_markup()


# ── Cases ─────────────────────────────────────────────────────────────────────
def cases_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="📦 Обычный кейс",      callback_data="case_open:1"),
        InlineKeyboardButton(text="📫 Редкий кейс",       callback_data="case_open:2"),
    )
    b.row(
        InlineKeyboardButton(text="💼 Эпический кейс",    callback_data="case_open:3"),
        InlineKeyboardButton(text="🌟 Легендарный кейс",  callback_data="case_open:4"),
    )
    b.row(
        InlineKeyboardButton(text="🎁 Праздничный кейс",  callback_data="case_open:5"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


# ── Top ───────────────────────────────────────────────────────────────────────
def top_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="💰 По балансу", callback_data="top:balance"),
        InlineKeyboardButton(text="📈 По уровню",  callback_data="top:level"),
    )
    b.row(
        InlineKeyboardButton(text="⚔️ По PvP",     callback_data="top:pvp_wins"),
        InlineKeyboardButton(text="👥 По рефералам", callback_data="top:referrals"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


# ── Social ────────────────────────────────────────────────────────────────────
def social_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="👫 Предложить руку",  callback_data="marry_propose"),
        InlineKeyboardButton(text="💔 Развод",           callback_data="marry_divorce"),
    )
    b.row(
        InlineKeyboardButton(text="🤝 Добавить в друзья", callback_data="friend_add"),
        InlineKeyboardButton(text="👥 Мои друзья",        callback_data="friend_list"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


# ── VIP ───────────────────────────────────────────────────────────────────────
def vip_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🥈 Silver — 5,000 💰", callback_data="vip_buy:silver"),
        InlineKeyboardButton(text="🥇 Gold — 15,000 💰",  callback_data="vip_buy:gold"),
    )
    b.row(
        InlineKeyboardButton(text="💎 Platinum — 50,000 💰", callback_data="vip_buy:platinum"),
    )
    b.row(
        InlineKeyboardButton(text="ℹ️ Привилегии VIP",    callback_data="vip_info"),
        InlineKeyboardButton(text="◀️ Назад",             callback_data="main_menu"),
    )
    return b.as_markup()


# ── Admin ─────────────────────────────────────────────────────────────────────
def admin_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="💰 Выдать деньги",    callback_data="adm_give_coins"),
        InlineKeyboardButton(text="🎒 Выдать предмет",   callback_data="adm_give_item"),
    )
    b.row(
        InlineKeyboardButton(text="💫 Выдать VIP",       callback_data="adm_give_vip"),
        InlineKeyboardButton(text="🚫 Забанить",         callback_data="adm_ban"),
    )
    b.row(
        InlineKeyboardButton(text="✅ Разбанить",        callback_data="adm_unban"),
        InlineKeyboardButton(text="🔇 Мут",              callback_data="adm_mute"),
    )
    b.row(
        InlineKeyboardButton(text="🎟️ Создать промокод", callback_data="adm_promo"),
        InlineKeyboardButton(text="📊 Статистика",       callback_data="adm_stats"),
    )
    b.row(
        InlineKeyboardButton(text="👥 Управление стаффом", callback_data="adm_staff"),
        InlineKeyboardButton(text="📋 Список предметов",   callback_data="adm_itemlist"),
    )
    b.row(
        InlineKeyboardButton(text="📋 Логи",             callback_data="adm_logs"),
        InlineKeyboardButton(text="💾 Backup",           callback_data="adm_backup"),
    )
    b.row(
        InlineKeyboardButton(text="📤 Экспорт БД",       callback_data="adm_export"),
        InlineKeyboardButton(text="🔄 Рестарт бота",     callback_data="adm_restart"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


def staff_manage_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="➕ Добавить администратора", callback_data="adm_add_admin"),
    )
    b.row(
        InlineKeyboardButton(text="🔬 Добавить тестировщика",   callback_data="adm_add_tester"),
    )
    b.row(
        InlineKeyboardButton(text="➖ Снять роль",              callback_data="adm_remove_staff"),
    )
    b.row(
        InlineKeyboardButton(text="📋 Список стаффа",           callback_data="adm_staff_list"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="adm_main"))
    return b.as_markup()


def tester_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🎒 Выдать себе предмет", callback_data="test_give_item"),
        InlineKeyboardButton(text="💰 Выдать себе монеты",  callback_data="test_give_coins"),
    )
    b.row(
        InlineKeyboardButton(text="⏰ Сбросить кулдауны",   callback_data="test_reset_cd"),
        InlineKeyboardButton(text="📈 Установить уровень",  callback_data="test_set_level"),
    )
    b.row(
        InlineKeyboardButton(text="📋 Список предметов",    callback_data="test_itemlist"),
        InlineKeyboardButton(text="🔍 Инфо об игроке",      callback_data="test_userinfo"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


# ── RP ────────────────────────────────────────────────────────────────────────
def rp_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🤗 Обнять",  callback_data="rp:hug"),
        InlineKeyboardButton(text="👋 Помахать", callback_data="rp:wave"),
    )
    b.row(
        InlineKeyboardButton(text="😘 Поцеловать", callback_data="rp:kiss"),
        InlineKeyboardButton(text="👊 Ударить",    callback_data="rp:punch"),
    )
    b.row(
        InlineKeyboardButton(text="🤝 Пожать руку", callback_data="rp:handshake"),
        InlineKeyboardButton(text="😄 Засмеяться",  callback_data="rp:laugh"),
    )
    b.row(
        InlineKeyboardButton(text="🎵 Потанцевать", callback_data="rp:dance"),
        InlineKeyboardButton(text="😭 Поплакать",   callback_data="rp:cry"),
    )
    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu"))
    return b.as_markup()


def confirm_kb(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да", callback_data=yes_cb),
        InlineKeyboardButton(text="❌ Нет", callback_data=no_cb),
    ]])
