"""
Marlboro Project — Shop handler
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import Database, get_db
from utils.keyboards import shop_kb, back_kb
from utils.texts import get_item_data, get_all_items, format_number
from utils.logger import log_action
from config import RARITIES

router = Router()


class BuyState(StatesGroup):
    waiting_amount = State()
    item_id = State()


@router.callback_query(F.data == "shop")
@router.message(Command("shop"))
async def show_shop(event) -> None:
    text = (
        f"🏪 <b>Магазин Marlboro</b>\n\n"
        f"Выбери категорию товаров:\n\n"
        f"⚔️ Оружие — для боёв и дуэлей\n"
        f"🛡️ Броня — защита в PvP\n"
        f"🧪 Расходники — зелья и предметы\n"
        f"🌾 Семена — для фермы\n"
        f"⛏️ Инструменты — для майнинга\n"
        f"🗝️ Ключи — для кейсов\n"
        f"💫 VIP-карты — привилегии\n"
        f"💎 Особые — редкие предметы"
    )
    kb = shop_kb()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("shop_cat:"))
async def shop_category(cb: CallbackQuery) -> None:
    category = cb.data.split(":")[1]
    db = await get_db()

    async with db.execute("SELECT item_id, price, stock FROM shop_items WHERE is_active = 1") as cur:
        shop_rows = await cur.fetchall()

    shop_dict = {r["item_id"]: r for r in shop_rows}
    all_items = get_all_items()

    cat_names = {
        "weapon": "⚔️ Оружие", "armor": "🛡️ Броня", "consumable": "🧪 Расходники",
        "farm_seed": "🌾 Семена", "mining_tool": "⛏️ Инструменты",
        "key": "🗝️ Ключи", "vip": "💫 VIP-карты", "special": "💎 Особые предметы",
    }

    cat_items = [i for i in all_items if i.get("type") == category and i["id"] in shop_dict]

    if not cat_items:
        await cb.answer("🏪 В этой категории нет товаров", show_alert=True)
        return

    lines = [f"🏪 <b>{cat_names.get(category, category)}</b>\n"]
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    b = InlineKeyboardBuilder()

    for item in cat_items[:20]:
        rar = RARITIES.get(item.get("rarity", "common"), {})
        shop_info = shop_dict[item["id"]]
        price = shop_info["price"]
        stock_txt = f" (осталось: {shop_info['stock']})" if shop_info["stock"] > 0 else ""
        lines.append(
            f"{item.get('emoji','📦')} <b>{item['name']}</b> {rar.get('emoji','')} "
            f"— {format_number(price)} монет{stock_txt}"
        )
        b.row(InlineKeyboardButton(
            text=f"{item.get('emoji','📦')} {item['name']} — {format_number(price)}💰",
            callback_data=f"buy_item:{item['id']}"
        ))

    b.row(InlineKeyboardButton(text="◀️ Назад", callback_data="shop"))
    await cb.message.edit_text("\n".join(lines), reply_markup=b.as_markup(), parse_mode="HTML")
    await cb.answer()


@router.callback_query(F.data.startswith("buy_item:"))
async def buy_item_prompt(cb: CallbackQuery, state: FSMContext) -> None:
    item_id = int(cb.data.split(":")[1])
    item = get_item_data(item_id)
    if not item:
        await cb.answer("❌ Предмет не найден", show_alert=True)
        return

    db = await get_db()
    async with db.execute("SELECT price, stock FROM shop_items WHERE item_id = ? AND is_active = 1", (item_id,)) as cur:
        shop_row = await cur.fetchone()
    if not shop_row:
        await cb.answer("❌ Предмет недоступен в магазине", show_alert=True)
        return

    rar = RARITIES.get(item.get("rarity", "common"), {})
    row = await Database.get_user(cb.from_user.id)
    price = shop_row["price"]

    text = (
        f"{item.get('emoji','📦')} <b>{item['name']}</b>\n"
        f"Редкость: {rar.get('emoji','')} {rar.get('color','')}\n"
        f"Описание: {item.get('description','')}\n\n"
        f"Цена: <b>{format_number(price)} монет</b>\n"
        f"💰 У тебя: <b>{format_number(row['balance'])} монет</b>\n\n"
        f"Сколько купить? (введи количество)"
    )
    await state.set_state(BuyState.waiting_amount)
    await state.update_data(item_id=item_id, price=price, item_name=item["name"])
    await cb.message.edit_text(text, reply_markup=back_kb("shop"), parse_mode="HTML")
    await cb.answer()


@router.message(BuyState.waiting_amount)
async def buy_item_amount(msg: Message, state: FSMContext) -> None:
    data = await state.get_data()
    item_id = data["item_id"]
    price = data["price"]
    item_name = data["item_name"]

    try:
        amount = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Введи число!")
        return

    if amount < 1:
        await msg.answer("❌ Минимум 1!")
        return

    total = price * amount
    db = await get_db()

    # Check stock
    async with db.execute("SELECT stock FROM shop_items WHERE item_id = ?", (item_id,)) as cur:
        sh = await cur.fetchone()
    if sh and sh["stock"] > 0 and sh["stock"] < amount:
        await msg.answer(f"❌ Только {sh['stock']} штук в наличии!", reply_markup=back_kb("shop"))
        await state.clear()
        return

    success = await Database.deduct_balance(msg.from_user.id, total)
    if not success:
        await msg.answer(
            f"❌ Недостаточно монет!\nНужно: <b>{format_number(total)}</b>, у тебя: меньше.",
            reply_markup=back_kb("shop"), parse_mode="HTML"
        )
        await state.clear()
        return

    await Database.add_item(msg.from_user.id, item_id, amount)

    if sh and sh["stock"] > 0:
        await db.execute("UPDATE shop_items SET stock = stock - ? WHERE item_id = ?", (amount, item_id))
        await db.commit()

    await log_action("shop", msg.from_user.id, f"Купил {item_name} x{amount} за {total}")
    item = get_item_data(item_id)
    await msg.answer(
        f"✅ Куплено: <b>{item.get('emoji','')} {item_name}</b> × {amount}\n"
        f"💰 Потрачено: <b>{format_number(total)} монет</b>",
        reply_markup=back_kb("shop"), parse_mode="HTML"
    )
    await state.clear()
