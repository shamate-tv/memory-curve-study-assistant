# -*- coding: utf-8 -*-
"""数据读写：负责把学习记录保存到 cache/user_data.json。

目录约定：
- data.json              程序自带的原始题库，不记录用户使用痕迹；
- cache/user_data.json   用户实际学习数据，首次运行自动生成；
- cache/settings.json    用户设置，例如深色模式、每日学习量；
- cache/daily_stats.json 今日完成量，用于每日上限控制。
"""

import json
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "cache"
DEFAULT_DATA_FILE = BASE_DIR / "data.json"
USER_DATA_FILE = CACHE_DIR / "user_data.json"
SETTINGS_FILE = CACHE_DIR / "settings.json"
DAILY_STATS_FILE = CACHE_DIR / "daily_stats.json"
STREAK_FILE = CACHE_DIR / "spark.json"

DEFAULT_SETTINGS = {
    "dark_mode": False,
    "daily_new_limit": 20,
    "daily_review_limit": 100,
    "reminder_startup": True,
    "reminder_daily": True,
    "reminder_time": "19:00",
    "use_windows_toast": True,
    "compat_mode": False,
}


def _today_text():
    return date.today().isoformat()


def ensure_cache_dir():
    """确保 cache 文件夹存在。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _make_fresh_card(item, index):
    """把原始知识点转换成一张全新的、没有使用痕迹的卡片。"""
    today = _today_text()
    return {
        "id": int(item.get("id", index) or index),
        "subject": str(item.get("subject", "未分类")),
        "book": str(item.get("book", "必修一")),
        "chapter": str(item.get("chapter", "")),
        "question": str(item.get("question", "")),
        "answer": str(item.get("answer", "")),
        "interval": 0,
        "next_review": today,
        "last_review": "",
        "first_review": "",
        "correct_count": 0,
        "wrong_count": 0,
    }


def _normalize_card(card, index):
    """补齐旧数据中缺失的字段，防止程序报错。"""
    fresh = _make_fresh_card(card, index)
    fresh["interval"] = int(card.get("interval", 0) or 0)
    fresh["next_review"] = str(card.get("next_review", fresh["next_review"]) or fresh["next_review"])
    fresh["last_review"] = str(card.get("last_review", "") or "")
    fresh["first_review"] = str(card.get("first_review", "") or "")
    fresh["correct_count"] = int(card.get("correct_count", 0) or 0)
    fresh["wrong_count"] = int(card.get("wrong_count", 0) or 0)
    return fresh


def _default_cards():
    """从 default_data.py 读取预置的高中必修一、二知识点。"""
    try:
        from default_data import DEFAULT_CARDS
    except ImportError:
        return []
    return [_make_fresh_card(item, index) for index, item in enumerate(DEFAULT_CARDS, start=1)]


def _read_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _load_seed_cards():
    """读取原始题库 data.json；如果没有或损坏，就使用 default_data.py。"""
    if DEFAULT_DATA_FILE.exists():
        try:
            data = _read_json(DEFAULT_DATA_FILE)
            raw_cards = data.get("cards", []) if isinstance(data, dict) else data
            if isinstance(raw_cards, list) and raw_cards:
                return [_make_fresh_card(card, index) for index, card in enumerate(raw_cards, start=1)]
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return _default_cards()


def load_cards(path=None):
    """读取用户学习数据；如果不存在，就从 data.json 初始化一份新数据。"""
    if path is None:
        ensure_cache_dir()
        path = USER_DATA_FILE
    else:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        cards = _load_seed_cards()
        save_cards(cards, path)
        return cards

    try:
        data = _read_json(path)
    except (OSError, json.JSONDecodeError, TypeError):
        cards = _load_seed_cards()
        save_cards(cards, path)
        return cards

    raw_cards = data.get("cards", []) if isinstance(data, dict) else data
    if not isinstance(raw_cards, list):
        raw_cards = []

    return [_normalize_card(card, index) for index, card in enumerate(raw_cards, start=1)]


def save_cards(cards, path=None):
    """保存学习数据到缓存文件。"""
    if path is None:
        ensure_cache_dir()
        path = USER_DATA_FILE
    else:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": 1,
        "saved_at": _today_text(),
        "cards": cards,
    }
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def next_card_id(cards):
    """生成新的卡片编号。"""
    if not cards:
        return 1
    return max(int(card.get("id", 0) or 0) for card in cards) + 1


def clear_user_cache():
    """删除用户学习数据和今日完成量；保留 data.json 和 settings.json。"""
    ensure_cache_dir()
    deleted = []
    for path in (USER_DATA_FILE, DAILY_STATS_FILE, STREAK_FILE):
        if path.exists():
            path.unlink()
            deleted.append(str(path))
    backup = CACHE_DIR / "user_data.backup.json"
    if backup.exists():
        backup.unlink()
        deleted.append(str(backup))
    return deleted


def clear_all_user_data():
    """删除全部用户数据：学习记录、今日完成量、火花、设置和提醒文件。"""
    ensure_cache_dir()
    deleted = []
    for path in (USER_DATA_FILE, DAILY_STATS_FILE, STREAK_FILE, SETTINGS_FILE):
        if path.exists():
            path.unlink()
            deleted.append(str(path))
    ics_file = CACHE_DIR / "记忆曲线提醒.ics"
    if ics_file.exists():
        ics_file.unlink()
        deleted.append(str(ics_file))
    return deleted


def reset_user_data():
    """清理缓存后，用 data.json 重新生成一份全新的用户数据。"""
    clear_user_cache()
    cards = _load_seed_cards()
    save_cards(cards)
    return cards


def load_spark():
    """读取“火花”数据：连续学习天数和最近一次学习日期。"""
    ensure_cache_dir()
    default = {"streak": 0, "last_study_date": ""}
    if not STREAK_FILE.exists():
        return default
    try:
        data = _read_json(STREAK_FILE)
    except (OSError, json.JSONDecodeError, TypeError):
        return default
    if not isinstance(data, dict):
        return default
    return {
        "streak": int(data.get("streak", 0) or 0),
        "last_study_date": str(data.get("last_study_date", "") or ""),
    }


def save_spark(spark):
    """保存“火花”数据。"""
    ensure_cache_dir()
    data = {
        "streak": int(spark.get("streak", 0) or 0),
        "last_study_date": str(spark.get("last_study_date", "") or ""),
    }
    with open(STREAK_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_settings():
    """读取用户设置，并补齐默认值。"""
    ensure_cache_dir()
    settings = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            data = _read_json(SETTINGS_FILE)
            if isinstance(data, dict):
                settings.update(data)
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return settings


def save_settings(settings):
    """保存用户设置。"""
    ensure_cache_dir()
    data = dict(DEFAULT_SETTINGS)
    data.update(settings)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_daily_stats():
    """读取今日完成量；如果日期不是今天，就自动重置。"""
    ensure_cache_dir()
    today = _today_text()
    default = {"date": today, "new_count": 0, "review_count": 0, "reminder_shown_date": ""}
    if not DAILY_STATS_FILE.exists():
        return default
    try:
        data = _read_json(DAILY_STATS_FILE)
    except (OSError, json.JSONDecodeError, TypeError):
        return default
    if not isinstance(data, dict) or data.get("date") != today:
        return default
    data["new_count"] = int(data.get("new_count", 0) or 0)
    data["review_count"] = int(data.get("review_count", 0) or 0)
    data["reminder_shown_date"] = str(data.get("reminder_shown_date", "") or "")
    return data


def save_daily_stats(stats):
    """保存今日完成量。"""
    ensure_cache_dir()
    data = {
        "date": _today_text(),
        "new_count": int(stats.get("new_count", 0) or 0),
        "review_count": int(stats.get("review_count", 0) or 0),
        "reminder_shown_date": str(stats.get("reminder_shown_date", "") or ""),
    }
    with open(DAILY_STATS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
