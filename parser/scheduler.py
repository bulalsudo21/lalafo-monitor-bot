from __future__ import annotations
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from aiogram import Bot
from db.database import async_session
from db.models import User, SeenAd, SearchQuery
from parser.lalafo import LalafoParser

scheduler = AsyncIOScheduler()
parser = LalafoParser()

async def check_ads(bot: Bot) -> None:
    async with async_session() as session:
        result = await session.execute(select(SearchQuery))
        queries = result.scalars().all()
        if not queries:
            return
        for query in queries:
            ads = await parser.search(query.keyword)
            if not ads:
                continue
            user_result = await session.execute(select(User).where(User.query_id == query.id))
            users = user_result.scalars().all()
            for ad in ads:
                seen_result = await session.execute(select(SeenAd).where(SeenAd.ad_url == ad.url, SeenAd.query_id == query.id))
                if seen_result.scalar_one_or_none():
                    continue
                session.add(SeenAd(ad_url=ad.url, query_id=query.id))
                await session.commit()
                for user in users:
                    if ad.price <= user.max_price:
                        text = f"🔔 <b>Новое объявление на Lalafo!</b>\n\n📦 {ad.title}\n💰 {ad.price:,.0f} сом\n🔗 <a href='{ad.url}'>Открыть объявление</a>"
                        try:
                            await bot.send_message(user.telegram_id, text, parse_mode="HTML", disable_web_page_preview=False)
                        except Exception:
                            continue
            query.last_checked = datetime.now(timezone.utc)
            await session.commit()

def start_scheduler(bot: Bot) -> None:
    scheduler.add_job(check_ads, "interval", seconds=60, args=[bot])
    scheduler.start()
