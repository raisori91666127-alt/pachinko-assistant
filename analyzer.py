"""
台ごとの履歴データから「狙い目スコア」を計算する。

スコア算出ロジック:
  - 直近N日間の差枚数合計 (重み: 40%)
  - BB確率の設定推測スコア (重み: 30%)
  - RB確率の設定推測スコア (重み: 20%)
  - 連続プラス日数ボーナス (重み: 10%)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class MachineScore:
    store_id: str
    machine_type: str
    unit_number: int
    total_diff: int
    avg_diff_per_day: float
    bb_prob: Optional[float]
    rb_prob: Optional[float]
    plus_days: int
    total_days: int
    score: float
    rank: int = 0


def calc_bb_setting_score(bb_prob: float) -> float:
    """BB確率から設定推測スコア(0-100)を返す。機種によって異なるが汎用値を使用"""
    # 一般的なジャグラー系の設定別BB確率参考値
    # 設定6: 1/240, 設定5: 1/252, 設定4: 1/264, 設定1: 1/297
    if bb_prob <= 0:
        return 0.0
    if bb_prob >= 1 / 240:
        return 100.0
    elif bb_prob >= 1 / 252:
        return 80.0
    elif bb_prob >= 1 / 264:
        return 60.0
    elif bb_prob >= 1 / 280:
        return 40.0
    elif bb_prob >= 1 / 297:
        return 20.0
    return 0.0


def calc_rb_setting_score(rb_prob: float) -> float:
    """RB確率から設定推測スコア(0-100)"""
    if rb_prob <= 0:
        return 0.0
    if rb_prob >= 1 / 364:
        return 100.0
    elif rb_prob >= 1 / 396:
        return 80.0
    elif rb_prob >= 1 / 455:
        return 60.0
    elif rb_prob >= 1 / 468:
        return 40.0
    return 0.0


def score_machines(records: list[dict]) -> list[MachineScore]:
    """
    records: MachineData の dict リスト（同一ホールの複数日分）
    returns: スコア降順でソートされた MachineScore リスト
    """
    # (store_id, machine_type, unit_number) でグループ化
    groups: dict[tuple, list[dict]] = {}
    for r in records:
        key = (r["store_id"], r["machine_type"], r["unit_number"])
        groups.setdefault(key, []).append(r)

    scores = []
    for (store_id, mtype, unit), days_data in groups.items():
        days_data.sort(key=lambda x: x["date"])

        total_games = sum(d["games"] for d in days_data)
        total_bb = sum(d["bb_count"] for d in days_data)
        total_rb = sum(d["rb_count"] for d in days_data)
        total_diff = sum(d["diff_medals"] for d in days_data)
        n = len(days_data)

        bb_prob = total_bb / total_games if total_games > 0 and total_bb > 0 else None
        rb_prob = total_rb / total_games if total_games > 0 and total_rb > 0 else None

        # 連続プラス日数（直近から遡る）
        plus_days = 0
        for d in reversed(days_data):
            if d["diff_medals"] > 0:
                plus_days += 1
            else:
                break

        # 差枚スコア: 7日で+3000枚以上を満点100とする
        diff_score = min(100.0, max(0.0, total_diff / 30.0))

        bb_score = calc_bb_setting_score(bb_prob) if bb_prob else 50.0
        rb_score = calc_rb_setting_score(rb_prob) if rb_prob else 50.0
        plus_score = (plus_days / max(n, 1)) * 100.0

        final_score = (
            diff_score * 0.40
            + bb_score * 0.30
            + rb_score * 0.20
            + plus_score * 0.10
        )

        scores.append(MachineScore(
            store_id=store_id,
            machine_type=mtype,
            unit_number=unit,
            total_diff=total_diff,
            avg_diff_per_day=total_diff / n if n > 0 else 0.0,
            bb_prob=bb_prob,
            rb_prob=rb_prob,
            plus_days=plus_days,
            total_days=n,
            score=round(final_score, 1),
        ))

    scores.sort(key=lambda x: x.score, reverse=True)
    for i, s in enumerate(scores):
        s.rank = i + 1
    return scores
