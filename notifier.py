# -*- coding: utf-8 -*-
"""Windows 提醒工具。

- Windows 10/11：优先使用 Windows Toast 系统通知；
- Windows 7：使用标准消息框 + 提示音；
- Toast 调用失败时，也会自动退回消息框。
"""

import base64
import subprocess
import sys
import xml.sax.saxutils as saxutils


def _xml_escape(text):
    return saxutils.escape(str(text))


def _is_windows():
    return sys.platform.startswith("win")


def _is_win7_or_older():
    if not _is_windows():
        return False
    try:
        return sys.getwindowsversion().major < 10
    except Exception:
        return False


def show_compat_message(title, message):
    """Win7 或 Toast 失败时使用的兼容提醒：消息框 + 提示音。"""
    if not _is_windows():
        return False
    try:
        import ctypes
        import winsound

        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        ctypes.windll.user32.MessageBoxW(
            0,
            str(message),
            str(title),
            0x40,  # MB_ICONINFORMATION
        )
        return True
    except Exception:
        return False


def _build_powershell_script(title, message, app_id):
    safe_title = _xml_escape(title)
    safe_message = _xml_escape(str(message).replace("\r", " ").replace("\n", " "))
    safe_app_id = str(app_id).replace("'", "''")

    template = (
        '<toast>'
        '<visual>'
        '<binding template="ToastText02">'
        f'<text id="1">{safe_title}</text>'
        f'<text id="2">{safe_message}</text>'
        '</binding>'
        '</visual>'
        '</toast>'
    )

    return (
        "$ErrorActionPreference = 'Stop'\n"
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null\n"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null\n"
        '$template = @\"\n'
        f"{template}\n"
        '"@\n'
        "$xml = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
        "$xml.LoadXml($template)\n"
        "$toast = New-Object Windows.UI.Notifications.ToastNotification $xml\n"
        f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{safe_app_id}').Show($toast)\n"
    )


def _show_toast(title, message, app_id):
    try:
        script = _build_powershell_script(title, message, app_id)
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
            creationflags=creationflags,
            check=False,
        )
        return completed.returncode == 0
    except Exception:
        return False


def show_windows_toast(title, message, app_id="记忆曲线复习助手", force_compat=False):
    """显示提醒。成功返回 True，失败返回 False。

    force_compat=True 时强制使用 Win7 兼容模式。
    """
    if not _is_windows():
        return False

    if force_compat or _is_win7_or_older():
        return show_compat_message(title, message)

    if _show_toast(title, message, app_id):
        return True

    return show_compat_message(title, message)
