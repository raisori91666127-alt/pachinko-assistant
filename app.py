from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
import asyncio

from db import init_db, get_db, Store, MachineData, SessionLocal
from scraper import scrape, get_saitama_stores
from analyzer import score_machines

app = FastAPI(title="パチスロ台選びアシスタント")

init_db()


@app.get("/")
def root():
    return FileResponse("index.html")


@app.get("/api/stores")
def list_stores(db: Session = Depends(get_db)):
    return db.query(Store).all()


@app.post("/api/stores/sync")
async def sync_stores(db: Session = Depends(get_db)):
    """さいたま市のホール一覧をsite777から取得してDBに保存"""
    stores = await get_saitama_stores()
    for s in stores:
        existing = db.query(Store).filter(Store.site7_id == s["site7_id"]).first()
        if not existing:
            db.add(Store(**s))
    db.commit()
    return {"synced": len(stores)}


_scrape_status = {"running": False, "message": ""}


@app.post("/api/data/fetch")
async def fetch_data(store_ids: list[str], days: int = 7, background_tasks: BackgroundTasks = None):
    """指定ホールの台データをバックグラウンドで取得"""
    if _scrape_status["running"]:
        raise HTTPException(409, "すでにスクレイピング中です")

    async def run():
        _scrape_status["running"] = True
        _scrape_status["message"] = "取得中..."
        try:
            records = await scrape(store_ids, days=days)
            db = SessionLocal()
            saved = 0
            for r in records:
                exists = db.query(MachineData).filter(
                    MachineData.store_id == r["store_id"],
                    MachineData.date == r["date"],
                    MachineData.unit_number == r["unit_number"],
                    MachineData.machine_type == r["machine_type"],
                ).first()
                if not exists:
                    db.add(MachineData(**r))
                    saved += 1
            db.commit()
            db.close()
            _scrape_status["message"] = f"完了: {saved}件保存"
        except Exception as e:
            _scrape_status["message"] = f"エラー: {e}"
        finally:
            _scrape_status["running"] = False

    background_tasks.add_task(run)
    return {"status": "started"}


@app.get("/api/data/status")
def scrape_status():
    return _scrape_status


@app.get("/api/ranking")
def ranking(
    store_id: str | None = None,
    machine_type: str | None = None,
    days: int = 7,
    top_n: int = 30,
    db: Session = Depends(get_db),
):
    """スコアランキングを返す"""
    since = date.today() - timedelta(days=days)
    query = db.query(MachineData).filter(MachineData.date >= since)
    if store_id:
        query = query.filter(MachineData.store_id == store_id)
    if machine_type:
        query = query.filter(MachineData.machine_type.contains(machine_type))

    records = [
        {
            "store_id": r.store_id,
            "machine_type": r.machine_type,
            "unit_number": r.unit_number,
            "date": r.date,
            "games": r.games,
            "bb_count": r.bb_count,
            "rb_count": r.rb_count,
            "diff_medals": r.diff_medals,
        }
        for r in query.all()
    ]

    scores = score_machines(records)
    return [
        {
            "rank": s.rank,
            "store_id": s.store_id,
            "machine_type": s.machine_type,
            "unit_number": s.unit_number,
            "score": s.score,
            "total_diff": s.total_diff,
            "avg_diff_per_day": round(s.avg_diff_per_day, 0),
            "bb_prob": f"1/{round(1/s.bb_prob)}" if s.bb_prob else "-",
            "rb_prob": f"1/{round(1/s.rb_prob)}" if s.rb_prob else "-",
            "plus_days": s.plus_days,
            "total_days": s.total_days,
        }
        for s in scores[:top_n]
    ]


@app.get("/api/machine/history")
def machine_history(
    store_id: str,
    unit_number: int,
    machine_type: str,
    days: int = 30,
    db: Session = Depends(get_db),
):
    """特定台の履歴データ"""
    since = date.today() - timedelta(days=days)
    rows = (
        db.query(MachineData)
        .filter(
            MachineData.store_id == store_id,
            MachineData.unit_number == unit_number,
            MachineData.machine_type == machine_type,
            MachineData.date >= since,
        )
        .order_by(MachineData.date)
        .all()
    )
    return [
        {
            "date": r.date,
            "games": r.games,
            "bb_count": r.bb_count,
            "rb_count": r.rb_count,
            "diff_medals": r.diff_medals,
        }
        for r in rows
    ]
