"""Backlot system tray icon (Windows only).

The server process shows a tray icon for as long as it lives, so the board
always has a taskbar presence:

- left-click  -> open the board in the browser
- right-click -> menu with Mở Backlot / Restart / Thoát

``Restart`` spawns a replacement ``backlot serve`` process and then shuts the
current one down; the replacement waits for the port to be released before
binding (see ``backlot.__main__``).

Implemented with ctypes against the plain Win32 API — no extra dependency
beyond Pillow, which already draws the icon. Every failure degrades to
"no tray icon" and never takes the server down. Set ``BACKLOT_TRAY=0`` to
disable the icon entirely.
"""

from __future__ import annotations

import ctypes
import io
import os
import sys
import threading
import webbrowser
from typing import Callable, Optional

from backlot import __version__

_WINDOW_CLASS = "BacklotTrayWindow"
_WM_APP = 0x8000
_WM_CLOSE = 0x0010
_WM_DESTROY = 0x0002
_WM_NULL = 0x0000
_WM_LBUTTONUP = 0x0202
_WM_LBUTTONDBLCLK = 0x0203
_WM_RBUTTONUP = 0x0205
_NIM_ADD = 0
_NIM_DELETE = 2
_NIF_MESSAGE = 0x01
_NIF_ICON = 0x02
_NIF_TIP = 0x04
_MF_STRING = 0x00
_MF_SEPARATOR = 0x800
_TPM_RIGHTBUTTON = 0x0002
_TPM_BOTTOMALIGN = 0x0020
_TPM_RIGHTALIGN = 0x0008
_TPM_RETURNCMD = 0x0100
_CMD_OPEN = 1
_CMD_RESTART = 2
_CMD_QUIT = 3
_AMBER = (240, 168, 60, 255)
_SLATE = (16, 17, 22, 255)


def _warn(message: str) -> None:
    print(f"backlot tray: {message}", file=sys.stderr, flush=True)


def _enabled() -> bool:
    if sys.platform != "win32":
        return False
    flag = os.environ.get("BACKLOT_TRAY", "1").strip().lower()
    return flag not in {"0", "false", "off", "no"}


def _icon_image(size: int = 64):
    """Render the tray icon (slate square, amber B) as a Pillow RGBA image."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([2, 2, size - 2, size - 2], radius=size // 4, fill=_SLATE)
    font_path = os.path.join(os.path.dirname(__file__), "ui", "fonts", "BeVietnamPro-SemiBold.ttf")
    try:
        font = ImageFont.truetype(font_path, int(size * 0.66))
    except OSError:
        font = ImageFont.load_default(size=int(size * 0.66))
    left, top, right, bottom = draw.textbbox((0, 0), "B", font=font)
    draw.text(
        ((size - (right - left)) / 2 - left, (size - (bottom - top)) / 2 - top),
        "B",
        font=font,
        fill=_AMBER,
    )
    return img


def _icon_bytes() -> bytes:
    """In-memory ICO rendering of the tray icon (diagnostics and tests)."""
    buf = io.BytesIO()
    _icon_image(64).save(buf, format="ICO", sizes=[(32, 32), (16, 16)])
    return buf.getvalue()


class _Win32:
    """Lazy ctypes bindings; imported only on Windows when the tray starts."""

    def __init__(self) -> None:
        import ctypes.wintypes as w

        if not hasattr(w, "LRESULT"):  # older Pythons lack it in wintypes
            w.LRESULT = ctypes.c_ssize_t

        self.w = w
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)

        self.WNDPROC = ctypes.WINFUNCTYPE(w.LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)

        class POINT(ctypes.Structure):
            _fields_ = [("x", w.LONG), ("y", w.LONG)]

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", w.HWND),
                ("message", w.UINT),
                ("wParam", w.WPARAM),
                ("lParam", w.LPARAM),
                ("time", w.DWORD),
                ("pt", POINT),
                ("lPrivate", w.DWORD),
            ]

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [
                ("style", w.UINT),
                ("lpfnWndProc", self.WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", w.HINSTANCE),
                ("hIcon", w.HICON),
                ("hCursor", w.HANDLE),
                ("hbrBackground", w.HBRUSH),
                ("lpszMenuName", w.LPCWSTR),
                ("lpszClassName", w.LPCWSTR),
            ]

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [
                ("cbSize", w.DWORD),
                ("hWnd", w.HWND),
                ("uID", w.UINT),
                ("uFlags", w.UINT),
                ("uCallbackMessage", w.UINT),
                ("hIcon", w.HICON),
                ("szTip", ctypes.c_wchar * 128),
                ("dwState", w.DWORD),
                ("dwStateMask", w.DWORD),
                ("szInfo", ctypes.c_wchar * 256),
                ("uVersion", w.UINT),
                ("szInfoTitle", ctypes.c_wchar * 64),
                ("dwInfoFlags", w.DWORD),
                ("guidItem", ctypes.c_byte * 16),
                ("hBalloonIcon", w.HICON),
            ]

        self.POINT = POINT
        self.MSG = MSG
        self.WNDCLASSW = WNDCLASSW
        self.NOTIFYICONDATAW = NOTIFYICONDATAW

        kernel32.GetModuleHandleW.restype = w.HMODULE
        kernel32.GetModuleHandleW.argtypes = [w.LPCWSTR]
        user32.DefWindowProcW.restype = w.LRESULT
        user32.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        user32.CreateWindowExW.restype = w.HWND
        user32.CreateWindowExW.argtypes = [
            w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            w.HWND, w.HMENU, w.HINSTANCE, w.LPVOID,
        ]
        user32.RegisterClassW.restype = w.ATOM
        user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
        user32.GetMessageW.restype = ctypes.c_int
        user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), w.HWND, w.UINT, w.UINT]
        user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
        user32.DispatchMessageW.restype = w.LRESULT
        user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
        user32.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        user32.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        user32.DestroyWindow.argtypes = [w.HWND]
        user32.PostQuitMessage.argtypes = [ctypes.c_int]
        user32.SetForegroundWindow.argtypes = [w.HWND]
        user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
        user32.CreatePopupMenu.restype = w.HMENU
        user32.CreatePopupMenu.argtypes = []
        user32.AppendMenuW.restype = w.BOOL
        user32.AppendMenuW.argtypes = [w.HMENU, w.UINT, ctypes.c_void_p, w.LPCWSTR]
        user32.DestroyMenu.argtypes = [w.HMENU]
        user32.TrackPopupMenuEx.restype = w.BOOL
        user32.TrackPopupMenuEx.argtypes = [w.HMENU, w.UINT, ctypes.c_int, ctypes.c_int, w.HWND, w.LPVOID]
        user32.GetDC.restype = w.HDC
        user32.GetDC.argtypes = [w.HWND]
        user32.ReleaseDC.argtypes = [w.HWND, w.HDC]
        user32.CreateIconIndirect.restype = w.HICON
        user32.CreateIconIndirect.argtypes = [ctypes.c_void_p]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        shell32.Shell_NotifyIconW.restype = w.BOOL
        shell32.Shell_NotifyIconW.argtypes = [w.UINT, ctypes.c_void_p]

        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        gdi32.CreateDIBSection.restype = w.HBITMAP
        gdi32.CreateDIBSection.argtypes = [
            w.HDC, ctypes.c_void_p, w.UINT,
            ctypes.POINTER(ctypes.c_void_p), w.HANDLE, w.DWORD,
        ]
        gdi32.CreateBitmap.restype = w.HBITMAP
        gdi32.CreateBitmap.argtypes = [
            ctypes.c_int, ctypes.c_int, w.UINT, w.UINT, w.LPVOID,
        ]
        gdi32.DeleteObject.argtypes = [w.HGDIOBJ]

        self.user32 = user32
        self.kernel32 = kernel32
        self.shell32 = shell32
        self.gdi32 = gdi32
        self.taskbar_created = user32.RegisterWindowMessageW("TaskbarCreated")


class _TrayIcon:
    """A tray icon owning a hidden window and its message loop (one thread)."""

    def __init__(
        self,
        port: int,
        on_restart: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._port = port
        self._url = f"http://127.0.0.1:{port}/"
        self._on_restart = on_restart
        self._on_quit = on_quit
        self._ready = threading.Event()
        self._stopped = threading.Event()
        self._error: Optional[str] = None
        self._win: Optional[_Win32] = None
        self._hwnd: Optional[int] = None
        self._nid: Optional[object] = None
        self._hicon: Optional[int] = None
        self._wndproc_ref: Optional[object] = None  # keep callback alive
        self._thread: Optional[threading.Thread] = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> bool:
        self._thread = threading.Thread(target=self._run, name="backlot-tray", daemon=True)
        self._thread.start()
        if not self._ready.wait(4.0):
            self._error = self._error or "timed out"
            return False
        return self._error is None

    def stop(self, timeout: float = 3.0) -> None:
        if self._hwnd and self._win:
            self._win.user32.PostMessageW(self._hwnd, _WM_CLOSE, 0, 0)
        self._stopped.wait(timeout)

    # -- internals ---------------------------------------------------------

    def _run(self) -> None:
        try:
            win = _Win32()
            u32 = win.user32
            self._win = win
            self._wndproc_ref = win.WNDPROC(self._wnd_proc)
            wc = win.WNDCLASSW()
            wc.lpfnWndProc = self._wndproc_ref
            wc.hInstance = win.kernel32.GetModuleHandleW(None)
            wc.lpszClassName = _WINDOW_CLASS
            wc.hIcon = self._load_hicon(win)
            if not u32.RegisterClassW(ctypes.byref(wc)):
                raise ctypes.WinError(ctypes.get_last_error())
            hwnd = u32.CreateWindowExW(
                0, _WINDOW_CLASS, "Backlot Tray", 0, 0, 0, 0, 0,
                None, None, wc.hInstance, None,
            )
            if not hwnd:
                raise ctypes.WinError(ctypes.get_last_error())
            self._hwnd = hwnd
            self._add_icon()
            self._ready.set()
            msg = win.MSG()
            while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                u32.TranslateMessage(ctypes.byref(msg))
                u32.DispatchMessageW(ctypes.byref(msg))
        except Exception as exc:  # noqa: BLE001 - the server must survive tray failures
            self._error = str(exc)
            self._ready.set()
        finally:
            self._stopped.set()

    def _load_hicon(self, win: "_Win32") -> int:
        """Build the tray HICON directly from pixels (CreateIconIndirect).

        CreateIconFromResource silently rejects Pillow's ICO bytes (its
        PNG-compressed entries), so the icon is drawn into a 32bpp top-down
        DIB section and wrapped with a monochrome mask instead.
        """
        u32, gdi32 = win.user32, win.gdi32

        # 2x the small-icon metric, capped at 64, keeps the glyph crisp on scaled DPI.
        metric = u32.GetSystemMetrics(49)  # SM_CXSMICON
        size = min(64, max(32, (metric if metric > 0 else 16) * 2))
        img = _icon_image(size)
        raw = img.tobytes("raw", "BGRA")

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", win.w.DWORD), ("biWidth", win.w.LONG), ("biHeight", win.w.LONG),
                ("biPlanes", win.w.WORD), ("biBitCount", win.w.WORD), ("biCompression", win.w.DWORD),
                ("biSizeImage", win.w.DWORD), ("biXPelsPerMeter", win.w.LONG),
                ("biYPelsPerMeter", win.w.LONG), ("biClrUsed", win.w.DWORD),
                ("biClrImportant", win.w.DWORD),
            ]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", win.w.BYTE * 4)]

        bmi = BITMAPINFO()
        bmi.bmiHeader = BITMAPINFOHEADER(
            biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=size, biHeight=-size,
            biPlanes=1, biBitCount=32, biCompression=0, biSizeImage=len(raw),
        )
        bits = ctypes.c_void_p()
        hdc = u32.GetDC(None)
        try:
            color = gdi32.CreateDIBSection(hdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
            if not color:
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            u32.ReleaseDC(None, hdc)
        ctypes.memmove(bits, raw, len(raw))
        mask = gdi32.CreateBitmap(size, size, 1, 1, None)

        class ICONINFO(ctypes.Structure):
            _fields_ = [
                ("fIcon", win.w.BOOL), ("xHotspot", win.w.DWORD), ("yHotspot", win.w.DWORD),
                ("hbmMask", win.w.HBITMAP), ("hbmColor", win.w.HBITMAP),
            ]

        info = ICONINFO(fIcon=True, xHotspot=0, yHotspot=0, hbmMask=mask, hbmColor=color)
        hicon = u32.CreateIconIndirect(ctypes.byref(info))
        gdi32.DeleteObject(color)
        gdi32.DeleteObject(mask)
        if not hicon:
            raise ctypes.WinError(ctypes.get_last_error())
        self._hicon = hicon
        return hicon

    def _notify(self, message: int) -> None:
        win = self._win
        nid = win.NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(nid)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = _NIF_MESSAGE | _NIF_ICON | _NIF_TIP
        nid.uCallbackMessage = _WM_APP
        nid.hIcon = self._hicon
        nid.szTip = f"Backlot {__version__} — {self._url}"
        if not win.shell32.Shell_NotifyIconW(message, ctypes.byref(nid)):
            raise ctypes.WinError(ctypes.get_last_error())
        self._nid = nid

    def _add_icon(self) -> None:
        self._notify(_NIM_ADD)

    def _delete_icon(self) -> None:
        try:
            self._notify(_NIM_DELETE)
        except Exception as exc:  # noqa: BLE001 - best effort during teardown
            _warn(f"could not remove icon: {exc}")

    def _wnd_proc(self, hwnd, message, wparam, lparam):
        u32 = self._win.user32
        try:
            if message == _WM_APP:
                mouse = lparam & 0xFFFF
                if mouse in (_WM_LBUTTONUP, _WM_LBUTTONDBLCLK):
                    self._safe(self._open_board)
                elif mouse == _WM_RBUTTONUP:
                    self._show_menu()
                return 0
            if message == self._win.taskbar_created and self._hwnd:
                # Explorer restarted: re-register the icon.
                try:
                    self._add_icon()
                except Exception as exc:  # noqa: BLE001
                    _warn(f"could not re-add icon: {exc}")
                return 0
            if message == _WM_CLOSE:
                self._delete_icon()
                u32.DestroyWindow(hwnd)
                return 0
            if message == _WM_DESTROY:
                u32.PostQuitMessage(0)
                return 0
        except Exception as exc:  # noqa: BLE001 - never raise through the ABI
            _warn(f"tray handler error: {exc}")
        return u32.DefWindowProcW(hwnd, message, wparam, lparam)

    def _open_board(self) -> None:
        webbrowser.open(self._url)

    def _show_menu(self) -> None:
        u32 = self._win.user32
        menu = u32.CreatePopupMenu()
        if not menu:
            return
        try:
            u32.AppendMenuW(menu, _MF_STRING, _CMD_OPEN, "Mở Backlot")
            u32.AppendMenuW(menu, _MF_STRING, _CMD_RESTART, "Restart")
            u32.AppendMenuW(menu, _MF_SEPARATOR, 0, None)
            u32.AppendMenuW(menu, _MF_STRING, _CMD_QUIT, "Thoát")
            pt = self._win.POINT()
            u32.GetCursorPos(ctypes.byref(pt))
            u32.SetForegroundWindow(self._hwnd)
            cmd = u32.TrackPopupMenuEx(
                menu,
                _TPM_RETURNCMD | _TPM_RIGHTBUTTON | _TPM_RIGHTALIGN | _TPM_BOTTOMALIGN,
                pt.x, pt.y, self._hwnd, None,
            )
            u32.PostMessageW(self._hwnd, _WM_NULL, 0, 0)
        finally:
            u32.DestroyMenu(menu)
        if cmd == _CMD_OPEN:
            self._safe(self._open_board)
        elif cmd == _CMD_RESTART:
            self._safe(self._on_restart)
        elif cmd == _CMD_QUIT:
            self._safe(self._on_quit)

    @staticmethod
    def _safe(action: Callable[[], None]) -> None:
        try:
            action()
        except Exception as exc:  # noqa: BLE001 - menu actions must never kill the loop
            _warn(f"action failed: {exc}")


def start_tray(
    port: int,
    on_restart: Callable[[], None],
    on_quit: Callable[[], None],
) -> Optional[_TrayIcon]:
    """Start the tray icon; return the handle, or None when unavailable."""
    if not _enabled():
        return None
    try:
        icon = _TrayIcon(port=port, on_restart=on_restart, on_quit=on_quit)
        if not icon.start():
            icon.stop(timeout=1.0)
            _warn(f"disabled after failure: {icon._error}")
            return None
        return icon
    except Exception as exc:  # noqa: BLE001 - the server must never die for the tray
        _warn(f"unavailable: {exc}")
        return None
