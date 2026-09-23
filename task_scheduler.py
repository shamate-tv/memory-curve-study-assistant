# -*- coding: utf-8 -*-
"""Windows 任务计划程序封装。

用于创建/删除一个每天运行的定时提醒任务。
任务运行 reminder.py，即使主程序没有打开，也能弹出 Windows 通知。
"""

import subprocess
import sys
from pathlib import Path

TASK_NAME = "MemoryCurve_Study_Reminder"
PROJECT_DIR = Path(__file__).resolve().parent
REMINDER_SCRIPT = PROJECT_DIR / "reminder.py"


def _run(args):
    """执行命令，返回 (是否成功, 输出信息)。"""
    try:
        completed = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        output = (completed.stdout or "").strip()
        return completed.returncode == 0, output
    except Exception as exc:
        return False, str(exc)


def _pythonw_path():
    """优先使用 pythonw.exe，避免出现黑色命令行窗口。"""
    executable = Path(sys.executable)
    pythonw = executable.with_name("pythonw.exe")
    if pythonw.exists():
        return str(pythonw)
    return str(executable)


def task_exists():
    """判断定时任务是否已经存在。"""
    if not sys.platform.startswith("win"):
        return False
    ok, _ = _run(["schtasks", "/Query", "/TN", TASK_NAME])
    return ok


def create_daily_task(time_text="19:00"):
    """创建或更新每天运行的提醒任务。"""
    if not sys.platform.startswith("win"):
        return False, "当前系统不是 Windows，无法创建任务计划。"

    pythonw = _pythonw_path()
    task_command = f'"{pythonw}" "{REMINDER_SCRIPT}"'
    ok, output = _run([
        "schtasks",
        "/Create",
        "/TN",
        TASK_NAME,
        "/TR",
        task_command,
        "/SC",
        "DAILY",
        "/ST",
        time_text,
        "/F",
    ])
    if ok:
        return True, f"已创建每天 {time_text} 运行的提醒任务。"
    return False, output or "创建任务失败。"


def delete_task():
    """删除提醒任务。"""
    if not sys.platform.startswith("win"):
        return False, "当前系统不是 Windows。"
    if not task_exists():
        return True, "提醒任务不存在，无需删除。"
    ok, output = _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    if ok:
        return True, "提醒任务已删除。"
    return False, output or "删除任务失败。"


def task_status_text():
    """返回任务状态文字。"""
    return "已创建" if task_exists() else "未创建"
