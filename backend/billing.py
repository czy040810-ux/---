"""拾题积分账本：试用与扣费规则。支付入账只能由未来已验签回调触发。"""
from datetime import datetime, timedelta
from uuid import uuid4

from .services import now

TRIAL_DAYS = 3
TRIAL_QUESTIONS = 10
PLANS = (
    {"id": "starter", "name": "体验包", "amount_fen": 490, "credits": 20},
    {"id": "basic", "name": "基础包", "amount_fen": 990, "credits": 50},
    {"id": "student", "name": "学生包", "amount_fen": 1990, "credits": 120},
    {"id": "frequent", "name": "高频包", "amount_fen": 3990, "credits": 280},
)


class CreditExhausted(Exception):
    """免费次数用尽或余额不足。"""


def init_billing(c, postgres: bool):
    user_ref = "BIGINT" if postgres else "INTEGER"
    primary_id = "BIGSERIAL PRIMARY KEY" if postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    c.executescript(f"""
    CREATE TABLE IF NOT EXISTS billing_wallets (
        user_id {user_ref} PRIMARY KEY REFERENCES users(id),
        trial_started TEXT NOT NULL,
        trial_used INTEGER NOT NULL DEFAULT 0,
        credits INTEGER NOT NULL DEFAULT 0,
        CHECK(trial_used >= 0 AND trial_used <= {TRIAL_QUESTIONS}),
        CHECK(credits >= 0)
    );
    CREATE TABLE IF NOT EXISTS billing_reservations (
        id TEXT PRIMARY KEY,
        user_id {user_ref} NOT NULL REFERENCES users(id),
        kind TEXT NOT NULL CHECK(kind IN ('trial','credit')),
        status TEXT NOT NULL CHECK(status IN ('reserved','committed','refunded')),
        created TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS billing_orders (
        id TEXT PRIMARY KEY,
        user_id {user_ref} NOT NULL REFERENCES users(id),
        plan_id TEXT NOT NULL,
        amount_fen INTEGER NOT NULL CHECK(amount_fen > 0),
        credits INTEGER NOT NULL CHECK(credits > 0),
        status TEXT NOT NULL CHECK(status IN ('pending','paid','cancelled','refunded')),
        provider_trade_id TEXT UNIQUE,
        created TEXT NOT NULL,
        paid_at TEXT
    );
    CREATE TABLE IF NOT EXISTS billing_ledger (
        id {primary_id},
        user_id {user_ref} NOT NULL REFERENCES users(id),
        delta INTEGER NOT NULL,
        reason TEXT NOT NULL,
        external_id TEXT UNIQUE NOT NULL,
        created TEXT NOT NULL
    );
    """)


def status(c, user_id: int, active: bool):
    row = c.execute("SELECT * FROM billing_wallets WHERE user_id=?", (user_id,)).fetchone()
    current = now()
    if row:
        started = datetime.fromisoformat(row["trial_started"])
        days_left = max(0, (started + timedelta(days=TRIAL_DAYS) - current).total_seconds() / 86400)
        trial_remaining = max(0, TRIAL_QUESTIONS - row["trial_used"]) if days_left > 0 else 0
        credits = row["credits"]
    else:
        days_left, trial_remaining, credits = TRIAL_DAYS, TRIAL_QUESTIONS, 0
    return {
        "billing_enabled": active,
        "payment_enabled": False,
        "trial_days_left": round(days_left, 2),
        "trial_questions_left": trial_remaining,
        "credits": credits,
        "cost_per_question": 1,
        "plans": list(PLANS),
    }


def reserve(c, user_id: int, postgres: bool) -> str:
    current = now()
    c.execute(
        "INSERT INTO billing_wallets(user_id,trial_started,trial_used,credits) VALUES(?,?,0,0) "
        "ON CONFLICT(user_id) DO NOTHING",
        (user_id, current.isoformat()),
    )
    # PostgreSQL 与 SQLite 均通过条件 UPDATE 原子扣减，避免同时分析时超用。
    cutoff = (current - timedelta(days=TRIAL_DAYS)).isoformat()
    cursor = c.execute(
        "UPDATE billing_wallets SET trial_used=trial_used+1 "
        "WHERE user_id=? AND trial_used<? AND trial_started>?",
        (user_id, TRIAL_QUESTIONS, cutoff),
    )
    if cursor.rowcount:
        kind = "trial"
    else:
        cursor = c.execute(
            "UPDATE billing_wallets SET credits=credits-1 WHERE user_id=? AND credits>=1",
            (user_id,),
        )
        if not cursor.rowcount:
            raise CreditExhausted("试用期或免费题数已用尽，积分余额不足。充值服务开通前请联系平台管理员。")
        kind = "credit"
    reservation_id = uuid4().hex
    c.execute(
        "INSERT INTO billing_reservations(id,user_id,kind,status,created) VALUES(?,?,?,'reserved',?)",
        (reservation_id, user_id, kind, current.isoformat()),
    )
    return reservation_id


def complete(c, reservation_id: str):
    c.execute("UPDATE billing_reservations SET status='committed' "
              "WHERE id=? AND status='reserved'", (reservation_id,))


def refund(c, reservation_id: str):
    row = c.execute(
        "SELECT user_id,kind,status FROM billing_reservations WHERE id=?",
        (reservation_id,),
    ).fetchone()
    if not row or row["status"] != "reserved":
        return
    field = "trial_used=trial_used-1" if row["kind"] == "trial" else "credits=credits+1"
    c.execute(f"UPDATE billing_wallets SET {field} WHERE user_id=?", (row["user_id"],))
    c.execute("UPDATE billing_reservations SET status='refunded' WHERE id=?", (reservation_id,))


def record_verified_payment(c, user_id: int, order_id: str, provider_trade_id: str):
    """仅供未来支付回调验签成功后使用。绝不能暴露成无需鉴权的充值接口。"""
    row = c.execute("SELECT * FROM billing_orders WHERE id=? AND user_id=?",
                    (order_id, user_id)).fetchone()
    if not row or row["status"] != "pending" or not provider_trade_id:
        return False
    update = c.execute(
        "UPDATE billing_orders SET status='paid',provider_trade_id=?,paid_at=? "
        "WHERE id=? AND status='pending'",
        (provider_trade_id, now().isoformat(), order_id),
    )
    if not update.rowcount:
        return False
    c.execute("INSERT INTO billing_wallets(user_id,trial_started,trial_used,credits) VALUES(?,?,0,0) "
              "ON CONFLICT(user_id) DO NOTHING", (user_id, now().isoformat()))
    c.execute("UPDATE billing_wallets SET credits=credits+? WHERE user_id=?",
              (row["credits"], user_id))
    c.execute("INSERT INTO billing_ledger(user_id,delta,reason,external_id,created) VALUES(?,?,?,?,?)",
              (user_id, row["credits"], "recharge", order_id, now().isoformat()))
    return True
