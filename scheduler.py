# -*- coding: utf-8 -*-
"""间隔重复算法和每日学习队列。

- 根据一次复习评价，安排下一次复习日期；
- 根据每日新卡上限、每日复习上限和今日完成量，生成今天的学习队列。
"""

from datetime import date, timedelta

# 三种评价：0=忘记，1=模糊，2=记住
RATING_FORGOT = 0
RATING_VAGUE = 1
RATING_KNOWN = 2

MAX_INTERVAL = 180  # 最长间隔，单位：天


def review_card(card, rating, today=None):
    """修改并返回一张卡片，计算它下一次复习的时间。

    card 是一个字典，至少包含 interval、correct_count、wrong_count 字段。
    rating 取 0、1、2。
    """
    if today is None:
        today = date.today()

    # 第一次复习时记录首次复习日期，用于区分新卡和复习卡。
    if not card.get("first_review"):
        card["first_review"] = today.isoformat()

    interval = int(card.get("interval", 0) or 0)

    if rating == RATING_FORGOT:
        interval = 1
        card["wrong_count"] = int(card.get("wrong_count", 0)) + 1
    elif rating == RATING_VAGUE:
        if interval <= 0:
            interval = 1
        else:
            interval = max(1, int(interval * 1.6))
        card["correct_count"] = int(card.get("correct_count", 0)) + 1
    else:
        if interval <= 0:
            interval = 1
        else:
            interval = max(2, int(interval * 2.2))
        card["correct_count"] = int(card.get("correct_count", 0)) + 1

    interval = min(interval, MAX_INTERVAL)
    card["interval"] = interval
    card["last_review"] = today.isoformat()
    card["next_review"] = (today + timedelta(days=interval)).isoformat()
    return card


def is_due(card, today=None):
    """判断一张卡片今天是否应该复习。"""
    if today is None:
        today = date.today()
    next_review = card.get("next_review") or today.isoformat()
    return next_review <= today.isoformat()


def get_due_cards(cards, today=None):
    """返回所有已经到期的卡片。"""
    due = [card for card in cards if is_due(card, today)]
    due.sort(key=lambda card: (
        card.get("next_review", ""),
        card.get("subject", ""),
        int(card.get("id", 0) or 0),
    ))
    return due


def is_new_card(card):
    """从未复习过的卡片视为新卡。"""
    return not bool(card.get("first_review"))


def select_daily_cards(cards, daily_new_limit=20, daily_review_limit=100, daily_stats=None, today=None):
    """根据每日上限生成今天的学习队列。

    规则：
    1. 优先安排已经到期的复习卡；
    2. 再安排新卡；
    3. 已到期的复习卡按逾期时间从早到晚排序；
    4. daily_review_limit 为 0 时表示不限制复习卡数量。
    """
    if today is None:
        today = date.today()
    if daily_stats is None:
        daily_stats = {}

    due_cards = get_due_cards(cards, today)
    review_due = [card for card in due_cards if not is_new_card(card)]
    new_due = [card for card in due_cards if is_new_card(card)]

    review_due.sort(key=lambda card: (
        card.get("next_review", ""),
        card.get("subject", ""),
        int(card.get("id", 0) or 0),
    ))
    new_due.sort(key=lambda card: (
        card.get("subject", ""),
        card.get("book", ""),
        int(card.get("id", 0) or 0),
    ))

    done_new = int(daily_stats.get("new_count", 0) or 0)
    done_review = int(daily_stats.get("review_count", 0) or 0)

    new_limit = int(daily_new_limit or 0)
    review_limit = int(daily_review_limit or 0)

    new_remaining = max(0, new_limit - done_new) if new_limit > 0 else len(new_due)

    if review_limit > 0:
        review_remaining = max(0, review_limit - done_review)
    else:
        review_remaining = len(review_due)

    selected = review_due[:review_remaining] + new_due[:new_remaining]
    return selected


def is_mastered(card):
    """间隔达到 30 天，视为已掌握。"""
    return int(card.get("interval", 0) or 0) >= 30


def get_accuracy(card):
    """返回单张卡片的正确率，0~1。"""
    correct = int(card.get("correct_count", 0) or 0)
    wrong = int(card.get("wrong_count", 0) or 0)
    total = correct + wrong
    if total == 0:
        return 0.0
    return correct / total


def next_interval_preview(card, rating, today=None):
    """不修改原卡片，预览选择某个评价后的间隔天数。"""
    temp = dict(card)
    review_card(temp, rating, today)
    return temp["interval"]
