"""
Marlboro Project — Text Templates (Russian)
"""

from config import BOT_NAME, BOT_VERSION, PROJECT_CHANNEL, PROJECT_CHAT, E


def welcome_text(first_name: str) -> str:
    return (
        f"🚬 <b>Добро пожаловать в {BOT_NAME}!</b>\n\n"
        f"Привет, <b>{first_name}</b>!\n\n"
        f"Ты попал в один из крупнейших RPG-ботов Telegram.\n"
        f"Здесь тебя ждут:\n"
        f"  ⚔️ Эпические битвы и дуэли\n"
        f"  💰 Богатая экономика и бизнес\n"
        f"  🏴 Кланы и союзы\n"
        f"  🌾 Фермерство и майнинг\n"
        f"  🎲 Казино и азартные игры\n"
        f"  💍 Браки и дружба\n"
        f"  📦 Редкие предметы и кейсы\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 Канал: {PROJECT_CHANNEL}\n"
        f"💬 Чат: {PROJECT_CHAT}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"Используй меню ниже для навигации 👇"
    )


def already_registered_text(first_name: str) -> str:
    return (
        f"🎮 <b>С возвращением, {first_name}!</b>\n\n"
        f"Выбери действие в меню ниже 👇"
    )


def profile_text(user: dict, clan_name: str = None, spouse_name: str = None) -> str:
    from config import RARITIES, xp_to_next, VIP_BONUSES
    vip = user["vip_status"]
    vip_emoji = {"none": "", "silver": "🥈", "gold": "🥇", "platinum": "💎"}.get(vip, "")
    lvl = user["level"]
    xp = user["xp"]
    xp_need = xp_to_next(lvl)
    bar_filled = int(xp / xp_need * 10) if xp_need else 10
    xp_bar = "█" * bar_filled + "░" * (10 - bar_filled)

    lines = [
        f"👤 <b>Профиль — {user['first_name']} {vip_emoji}</b>",
        f"🆔 ID: <code>{user['user_id']}</code>",
        f"",
        f"📈 Уровень: <b>{lvl}</b>  [{xp_bar}]  {xp}/{xp_need} XP",
        f"",
        f"💰 Баланс:  <b>{user['balance']:,} монет</b>",
        f"🏦 Банк:    <b>{user['bank']:,} монет</b>",
        f"",
        f"❤️ HP: {user['health']}/{user['max_health']}  ⚡ Энергия: {user['energy']}/100",
        f"⚔️ Атака: {user['attack']}   🛡️ Защита: {user['defense']}",
        f"",
        f"⚔️ PvP — Победы: {user['pvp_wins']} / Поражения: {user['pvp_losses']}",
        f"📅 Стрик ежедневных: {user['daily_streak']} дней",
        f"👥 Рефералов: {user['referrals']}",
    ]
    if clan_name:
        lines.append(f"🏴 Клан: <b>{clan_name}</b>")
    if spouse_name:
        lines.append(f"💍 Супруг(а): <b>{spouse_name}</b>")
    if vip != "none":
        bonus = VIP_BONUSES[vip]
        lines.append(f"💫 VIP: <b>{vip.capitalize()}</b>  (×{bonus['xp']} XP, ×{bonus['coins']} монет)")
    return "\n".join(lines)


def inventory_text(items_list: list) -> str:
    if not items_list:
        return "🎒 <b>Инвентарь пуст</b>\n\nПосети магазин или открой кейс!"
    lines = ["🎒 <b>Инвентарь</b>\n"]
    for row in items_list:
        item = get_item_data(row["item_id"])
        if item:
            from config import RARITIES
            rar = RARITIES.get(item.get("rarity", "common"), {})
            eq = " [EQUIPPED]" if row["equipped"] else ""
            lines.append(
                f"{item.get('emoji','📦')} <b>{item['name']}</b> × {row['amount']}"
                f"  {rar.get('emoji','')} {rar.get('color','')}{eq}"
            )
    return "\n".join(lines)


def help_text() -> str:
    return (
        f"ℹ️ <b>{BOT_NAME} v{BOT_VERSION} — Помощь</b>\n\n"
        f"<b>Основные команды:</b>\n"
        f"/start — главное меню\n"
        f"/profile — профиль\n"
        f"/inventory — инвентарь\n"
        f"/balance — баланс\n"
        f"/top — топ игроков\n"
        f"/daily — ежедневный бонус\n"
        f"/work — работать\n"
        f"/mine — добывать ресурсы\n"
        f"/duel — вызвать на дуэль\n"
        f"/send — перевести деньги\n"
        f"/promo — активировать промокод\n"
        f"/trade — предложить обмен\n"
        f"/marry — предложить руку\n\n"
        f"<b>Клановые команды:</b>\n"
        f"/clan — информация о клане\n"
        f"/claninvite — пригласить в клан\n\n"
        f"<b>Развлечения:</b>\n"
        f"/slots — игровые автоматы\n"
        f"/roulette — рулетка\n"
        f"/dice — кости\n"
        f"/coinflip — монетка\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 {PROJECT_CHANNEL}\n"
        f"💬 {PROJECT_CHAT}"
    )


def get_item_data(item_id: int) -> dict | None:
    """Load item data from items.json by id."""
    import json, os
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "items.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for item in data["items"]:
            if item["id"] == item_id:
                return item
    except Exception:
        pass
    return None


def get_case_data(case_id: int) -> dict | None:
    import json, os
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cases.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for case in data["cases"]:
            if case["id"] == case_id:
                return case
    except Exception:
        pass
    return None


def get_all_items() -> list:
    import json, os
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "items.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)["items"]
    except Exception:
        return []


def format_number(n: int) -> str:
    return f"{n:,}".replace(",", " ")
