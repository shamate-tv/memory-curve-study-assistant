# -*- coding: utf-8 -*-
"""Windows 定时提醒脚本。

由任务计划程序调用。主程序没有打开时，也会读取学习数据，
如果有待复习卡片，就弹出 Windows 系统通知。
"""

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import notifier  # noqa: E402
import scheduler  # noqa: E402
import storage  # noqa: E402


def _fallback_message_box(message):
    """Windows Toast 失败时，使用标准消息框兜底。"""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, "学习提醒", 0x40)
        return True
    except Exception:
        return False


def main():
    settings = storage.load_settings()
    if not bool(settings.get("reminder_daily", True)):
        return 0

    cards = storage.load_cards()
    daily_stats = storage.load_daily_stats()
    due_cards = scheduler.select_daily_cards(
        cards,
        daily_new_limit=int(settings.get("daily_new_limit", 20) or 20),
        daily_review_limit=int(settings.get("daily_review_limit", 100) or 0),
        daily_stats=daily_stats,
    )

    if not due_cards:
        return 0

    done_new = int(daily_stats.get("new_count", 0) or 0)
    done_review = int(daily_stats.get("review_count", 0) or 0)
    message = f"今天还有 {len(due_cards)} 张卡片待完成，完成后可以续火花。"
    if done_new or done_review:
        message += f" 已学新卡 {done_new} 张，复习 {done_review} 张。"

    if bool(settings.get("use_windows_toast", True)):
        if notifier.show_windows_toast(
            "记忆曲线 · 学习提醒",
            message,
            force_compat=bool(settings.get("compat_mode", False)),
        ):
            return 0

    _fallback_message_box(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
