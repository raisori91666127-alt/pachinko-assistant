"""
site777.jp scraper using Playwright.
Fetches daily slot machine data for stores in Saitama.
"""
import asyncio
import os
import re
from datetime import date, timedelta
from typing import Optional

from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page

load_dotenv()

SITE7_EMAIL = os.getenv("SITE7_EMAIL", "")
SITE7_PASSWORD = os.getenv("SITE7_PASSWORD", "")
BASE_URL = "https://www.site777.jp"


async def login(page: Page) -> bool:
    await page.goto(f"{BASE_URL}/member/login", wait_until="networkidle")
    await page.fill('input[name="email"]', SITE7_EMAIL)
    await page.fill('input[name="password"]', SITE7_PASSWORD)
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("networkidle")
    return "logout" in page.url or await page.query_selector(".logout") is not None


async def search_saitama_stores(page: Page) -> list[dict]:
    """埼玉県のホール一覧を取得する"""
    await page.goto(f"{BASE_URL}/hall/search?pref=11", wait_until="networkidle")
    stores = []
    items = await page.query_selector_all(".hall-list-item, .shop-list li, [class*='hall']")
    for item in items:
        link = await item.query_selector("a")
        if not link:
            continue
        href = await link.get_attribute("href") or ""
        name_el = await item.query_selector(".hall-name, .shop-name, h3, h4")
        name = await name_el.inner_text() if name_el else await link.inner_text()
        m = re.search(r"/hall/(\d+)", href)
        if m:
            stores.append({"site7_id": m.group(1), "name": name.strip(), "area": "埼玉"})
    return stores


async def fetch_store_data(page: Page, store_id: str, target_date: Optional[date] = None) -> list[dict]:
    """指定ホールの全台データを取得する"""
    if target_date is None:
        target_date = date.today()

    date_str = target_date.strftime("%Y%m%d")
    url = f"{BASE_URL}/hall/{store_id}/slot?date={date_str}"
    await page.goto(url, wait_until="networkidle")

    # 全台データのテーブルを解析
    records = []
    rows = await page.query_selector_all("table.data-table tr, .slot-data-row, [class*='machine-row']")

    for row in rows:
        cells = await row.query_selector_all("td")
        if len(cells) < 6:
            continue
        try:
            texts = [await c.inner_text() for c in cells]
            unit_raw = texts[0].strip()
            machine_type = texts[1].strip()
            games_raw = texts[2].strip().replace(",", "")
            bb_raw = texts[3].strip().replace(",", "")
            rb_raw = texts[4].strip().replace(",", "")
            diff_raw = texts[5].strip().replace(",", "").replace("+", "")

            records.append({
                "store_id": store_id,
                "date": target_date,
                "machine_type": machine_type,
                "unit_number": int(re.sub(r"\D", "", unit_raw) or 0),
                "games": int(games_raw) if games_raw.lstrip("-").isdigit() else 0,
                "bb_count": int(bb_raw) if bb_raw.lstrip("-").isdigit() else 0,
                "rb_count": int(rb_raw) if rb_raw.lstrip("-").isdigit() else 0,
                "diff_medals": int(diff_raw) if diff_raw.lstrip("-").isdigit() else 0,
            })
        except (ValueError, IndexError):
            continue
    return records


async def scrape(store_ids: list[str], days: int = 7) -> list[dict]:
    """複数ホール・複数日のデータを一括取得"""
    all_records = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        logged_in = await login(page)
        if not logged_in:
            raise RuntimeError("site777 ログイン失敗。.env の認証情報を確認してください。")

        for store_id in store_ids:
            for i in range(days):
                target = date.today() - timedelta(days=i)
                try:
                    records = await fetch_store_data(page, store_id, target)
                    all_records.extend(records)
                    await asyncio.sleep(2)  # サーバー負荷軽減
                except Exception as e:
                    print(f"[WARN] {store_id} / {target}: {e}")

        await browser.close()
    return all_records


async def get_saitama_stores() -> list[dict]:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        await login(page)
        stores = await search_saitama_stores(page)
        await browser.close()
    return stores
