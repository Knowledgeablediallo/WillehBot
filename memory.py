# ==========================================
# FILE: memory.py
# ==========================================

import json
import os

from config import get_config_value

DB_FILE = "signals_db.json"
SUPABASE_TABLE = "user_profiles"
SUPABASE_TIMEOUT_SECONDS = 45

MAX_CONFIDENCE_BOOST = 20
MAX_CONFIDENCE_PENALTY = -35
WIN_CONFIDENCE_STEP = 3
LOSS_CONFIDENCE_STEP = -8

_supabase_warning_shown = False


def _supabase_config():
    url = get_config_value("SUPABASE_URL")
    key = (
        get_config_value("SUPABASE_SERVICE_ROLE_KEY")
        or get_config_value("SUPABASE_KEY")
    )

    return url, key


def _supabase_enabled():
    url, key = _supabase_config()
    return bool(url and key)


def _supabase_headers():
    _, key = _supabase_config()

    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }


def _supabase_rest_url():
    url, _ = _supabase_config()
    return f"{url.rstrip('/')}/rest/v1/{SUPABASE_TABLE}"


def _raise_for_supabase_error(response):
    if 200 <= response.status_code < 300:
        return

    raise RuntimeError(
        f"Supabase request failed with {response.status_code}: {response.text}"
    )


def _warn_supabase_fallback(error):
    global _supabase_warning_shown

    if _supabase_warning_shown:
        return

    print(
        "Supabase storage is unavailable. Falling back to local signals_db.json. "
        f"Reason: {error}"
    )
    _supabase_warning_shown = True


def _load_local_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f)

    with open(DB_FILE, "r") as f:
        return json.load(f)


def _save_local_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)


def _load_supabase_db():
    import requests

    response = requests.get(
        _supabase_rest_url(),
        headers=_supabase_headers(),
        params={"select": "user_id,profile"},
        timeout=SUPABASE_TIMEOUT_SECONDS
    )
    _raise_for_supabase_error(response)

    db = {
        str(row["user_id"]): _ensure_profile_shape(row.get("profile") or {})
        for row in response.json()
    }

    if not db and os.path.exists(DB_FILE):
        local_db = _load_local_db()

        if local_db:
            _save_supabase_db(local_db)
            return local_db

    return db


def _save_supabase_db(db):
    import requests

    rows = [
        {
            "user_id": str(user_id),
            "profile": _ensure_profile_shape(profile)
        }
        for user_id, profile in db.items()
    ]

    if not rows:
        return

    headers = _supabase_headers()
    headers["Prefer"] = "resolution=merge-duplicates"

    response = requests.post(
        _supabase_rest_url(),
        headers=headers,
        params={"on_conflict": "user_id"},
        json=rows,
        timeout=SUPABASE_TIMEOUT_SECONDS
    )
    _raise_for_supabase_error(response)


def load_db():
    if _supabase_enabled():
        try:
            return _load_supabase_db()
        except Exception as error:
            _warn_supabase_fallback(error)

    return _load_local_db()


def save_db(db):
    if _supabase_enabled():
        try:
            _save_supabase_db(db)
            return
        except Exception as error:
            _warn_supabase_fallback(error)

    _save_local_db(db)


def _new_profile():
    return {
        "wins": 0,
        "losses": 0,
        "bias": 0,
        "setups": {}
    }


def _setup_key(symbol, signal):
    return f"{symbol}:{signal}"


def _ensure_profile_shape(profile):
    profile.setdefault("wins", 0)
    profile.setdefault("losses", 0)
    profile.setdefault("bias", 0)
    profile.setdefault("setups", {})

    return profile


def _ensure_setup(profile, symbol, signal):
    key = _setup_key(symbol, signal)
    setups = profile.setdefault("setups", {})

    if key not in setups:
        setups[key] = {
            "wins": 0,
            "losses": 0,
            "confidence_adjustment": 0,
            "last_result": "",
            "loss_reasons": {}
        }

    setup = setups[key]
    setup.setdefault("wins", 0)
    setup.setdefault("losses", 0)
    setup.setdefault("confidence_adjustment", 0)
    setup.setdefault("last_result", "")
    setup.setdefault("loss_reasons", {})

    return setup


def get_profile(user_id):
    db = load_db()
    user_id = str(user_id)

    if user_id not in db:
        db[user_id] = _new_profile()
    else:
        _ensure_profile_shape(db[user_id])

    save_db(db)
    return db[user_id]


def get_learning_adjustment(profile, symbol, signal):
    profile = _ensure_profile_shape(profile)
    setup = profile.get("setups", {}).get(_setup_key(symbol, signal))

    if not setup:
        return {
            "confidence_adjustment": 0,
            "block": False,
            "reason": ""
        }

    wins = setup.get("wins", 0)
    losses = setup.get("losses", 0)
    confidence_adjustment = setup.get("confidence_adjustment", 0)
    total = wins + losses
    loss_rate = losses / total if total else 0
    win_rate = wins / total if total else 0

    if total >= 4 and win_rate >= 0.70:
        confidence_adjustment += 5
    elif total >= 3 and loss_rate >= 0.60:
        confidence_adjustment -= 5

    return {
        "confidence_adjustment": max(
            MAX_CONFIDENCE_PENALTY,
            min(MAX_CONFIDENCE_BOOST, confidence_adjustment)
        ),
        "block": losses >= 2 and loss_rate >= 0.70,
        "reason": top_loss_reason(setup)
    }


def top_loss_reason(setup):
    reasons = setup.get("loss_reasons", {})

    if not reasons:
        return ""

    return max(reasons, key=reasons.get)


def update_feedback(user_id, result, symbol=None, signal=None, reason=None):
    get_profile(user_id)
    db = load_db()
    user_id = str(user_id)
    profile = _ensure_profile_shape(db[user_id])

    if result == "profit":
        profile["wins"] += 1
        profile["bias"] += 0.0001
    elif result == "loss":
        profile["losses"] += 1
        profile["bias"] -= 0.0001

    if symbol and signal:
        setup = _ensure_setup(profile, symbol, signal)

        if result == "profit":
            setup["wins"] += 1
            setup["last_result"] = "profit"
            setup["confidence_adjustment"] = min(
                MAX_CONFIDENCE_BOOST,
                setup["confidence_adjustment"] + WIN_CONFIDENCE_STEP
            )
        elif result == "loss":
            setup["losses"] += 1
            setup["last_result"] = "loss"
            setup["confidence_adjustment"] = max(
                MAX_CONFIDENCE_PENALTY,
                setup["confidence_adjustment"] + LOSS_CONFIDENCE_STEP
            )

            if reason:
                setup["loss_reasons"][reason] = (
                    setup["loss_reasons"].get(reason, 0) + 1
                )

    save_db(db)
