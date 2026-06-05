from __future__ import annotations
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, delete
from db.database import async_session
from db.models import User, SearchQuery, SeenAd

router = Router(name="user_handlers")

class MonitorForm(StatesGroup):
    keyword = State()
    max_price = State()

@router.message(CommandStart())
async def cmd_start(message: types.Message) -> None:
    await message.answer(
        "👋 <b>Lalafo.kg — Мониторинг объявлений</b>\n\n"
        "Я отслеживаю новые объявления каждые 60 секунд.\n\n"
        "📋 Команды:\n"
        "/monitor — добавить фильтр\n"
        "/stop — удалить все фильтры\n"
        "/list — показать активные фильтры",
        parse_mode="HTML",
    )

@router.message(Command("monitor"))
async def cmd_monitor(message: types.Message, state: FSMContext) -> None:
    await state.set_state(MonitorForm.keyword)
    await message.answer("🔍 Что ищем?\n<i>Например: iPhone 15, самокат, диван</i>", parse_mode="HTML")

@router.message(MonitorForm.keyword)
async def process_keyword(message: types.Message, state: FSMContext) -> None:
    await state.update_data(keyword=message.text.strip().lower())
    await state.set_state(MonitorForm.max_price)
    await message.answer("💰 Максимальная цена (сом):")

@router.message(MonitorForm.max_price)
async def process_price(message: types.Message, state: FSMContext) -> None:
    try:
        price = float(message.text.strip().replace(",", ".").replace(" ", ""))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное положительное число.")
        return
    data = await state.get_data()
    keyword: str = data["keyword"]
    async with async_session() as session:
        old_user = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        old_user = old_user.scalar_one_or_none()
        if old_user:
            old_query_id = old_user.query_id
            await session.delete(old_user)
            await session.commit()
            remaining = await session.execute(select(User).where(User.query_id == old_query_id))
            if not remaining.scalars().all():
                await session.execute(delete(SeenAd).where(SeenAd.query_id == old_query_id))
                await session.execute(delete(SearchQuery).where(SearchQuery.id == old_query_id))
                await session.commit()
        query_result = await session.execute(select(SearchQuery).where(SearchQuery.keyword == keyword))
        query = query_result.scalar_one_or_none()
        if not query:
            query = SearchQuery(keyword=keyword)
            session.add(query)
            await session.flush()
        user = User(telegram_id=message.from_user.id, max_price=price, query_id=query.id)
        session.add(user)
        await session.commit()
    await state.clear()
    await message.answer(f"✅ <b>Мониторинг активирован!</b>\n\n🔎 Поиск: <i>{keyword}</i>\n💵 До: {price:,.0f} сом\n⏱ Проверка: каждые 60 сек\n\nЖдите уведомлений 🔔", parse_mode="HTML")

@router.message(Command("stop"))
async def cmd_stop(message: types.Message) -> None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("У вас нет активных фильтров.")
            return
        query_id = user.query_id
        await session.delete(user)
        await session.commit()
        remaining = await session.execute(select(User).where(User.query_id == query_id))
        if not remaining.scalars().all():
            await session.execute(delete(SeenAd).where(SeenAd.query_id == query_id))
            await session.execute(delete(SearchQuery).where(SearchQuery.id == query_id))
            await session.commit()
    await message.answer("🛑 Мониторинг остановлен. Фильтры удалены.")

@router.message(Command("list"))
async def cmd_list(message: types.Message) -> None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        filters = result.scalars().all()
    if not filters:
        await message.answer("У вас нет активных фильтров.")
        return
    text = "<b>📌 Ваши фильтры:</b>\n\n"
    for f in filters:
        text += f"🔹 <i>{f.query.keyword}</i> — до {f.max_price:,.0f} сом\n"
    await message.answer(text, parse_mode="HTML")
