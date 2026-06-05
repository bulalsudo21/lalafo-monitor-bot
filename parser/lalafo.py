from __future__ import annotations
import asyncio, os, re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

@dataclass(slots=True)
class Ad:
    title: str
    price: float
    url: str
    image_url: Optional[str] = None

class LalafoParser:
    BASE_URL = "https://lalafo.kg"
    PROXY = os.getenv("PROXY_URL")

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Browser:
        if self._browser is None or not self._browser.is_connected():
            async with self._lock:
                if self._browser is None or not self._browser.is_connected():
                    self._playwright = await async_playwright().start()
                    launch_options = {
                        "headless": True,
                        "args": [
                            "--no-sandbox", "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage", "--disable-gpu",
                            "--disable-blink-features=AutomationControlled",
                        ],
                    }
                    if self.PROXY:
                        launch_options["proxy"] = {"server": self.PROXY}
                    self._browser = await self._playwright.chromium.launch(**launch_options)
        return self._browser

    async def search(self, keyword: str) -> list[Ad]:
        encoded = quote_plus(keyword)
        url = f"{self.BASE_URL}/kg/search/{encoded}"
        browser = await self._ensure_browser()
        context = await self._new_context()
        page: Page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_selector('article[data-testid="ad-card"], .AdTileV2, [class*="adCard"]', timeout=15000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await asyncio.sleep(1.5)
            return await self._extract_ads(page)
        except Exception:
            return []
        finally:
            await context.close()

    async def _new_context(self) -> BrowserContext:
        browser = await self._ensure_browser()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru'] });
        """)
        return context

    async def _extract_ads(self, page: Page) -> list[Ad]:
        ads: list[Ad] = []
        cards = await page.locator('article[data-testid="ad-card"], .AdTileV2, [class*="adCard"]').all()
        for card in cards:
            try:
                title_el = card.locator('[data-testid="ad-card-title"], .ad-title, h3, h4, a[title]').first
                price_el = card.locator('[data-testid="ad-card-price"], .ad-price, .price, [class*="price"]').first
                link_el = card.locator("a[href]").first
                img_el = card.locator("img[src]").first
                title = await title_el.text_content()
                raw_price = await price_el.text_content()
                href = await link_el.get_attribute("href")
                img_src = await img_el.get_attribute("src")
                if not title or not raw_price or not href:
                    continue
                price = self._extract_price(raw_price.strip())
                if href and not href.startswith("http"):
                    href = self.BASE_URL + href
                ads.append(Ad(title=title.strip(), price=price, url=href, image_url=img_src))
            except Exception:
                continue
        return ads

    @staticmethod
    def _extract_price(raw: str) -> float:
        cleaned = re.sub(r"[^\d]", "", raw)
        return float(cleaned) if cleaned else float("inf")

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
