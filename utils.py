import ctypes
from ctypes import Structure
from ctypes.wintypes import UINT, INT, HANDLE, HWND, POINT, RECT, DWORD
from enum import IntEnum


class Const(IntEnum):
    """WinAPI constants."""
    pt_touch   = 0x00000002
    down       = 0x00010000
    in_range   = 0x00000002
    in_contact = 0x00000004
    update     = 0x00020000
    up         = 0x00040000
    mask_all   = 0x00000007
    none       = 0x00000000
    canceled   = 0x00008000

# --- ctypes STRUCTs ---
class Pointer_Info(Structure):
    _fields_ = [
        ("pointerType",           UINT),
        ("pointerId",             UINT),
        ("frameId",               UINT),
        ("pointerFlags",          INT),
        ("sourceDevice",          HANDLE),
        ("hwndTarget",            HWND),
        ("ptPixelLocation",       POINT),
        ("ptHimetricLocation",    POINT),
        ("ptPixelLocationRaw",    POINT),
        ("ptHimetricLocationRaw", POINT),
        ("dwTime",                DWORD),
        ("historyCount",          UINT),
        ("inputData",             INT),
        ("dwKeyStates",           DWORD),
        ("PerformanceCount",      ctypes.c_uint64),
        ("ButtonChangeType",      INT),
    ]

class Pointer_Touch_Info(Structure):
    _fields_ = [
        ("pointerInfo",  Pointer_Info),
        ("touchFlags",   INT),
        ("touchMask",    INT),
        ("rcContact",    RECT),
        ("rcContactRaw", RECT),
        ("orientation",  UINT),
        ("pressure",     UINT),
    ]

    def __repr__(self):
        return f"POINTER_TOUCH_INFO({self.pointerInfo.pointerId}, {self.pointerInfo.ptPixelLocation.x}, {self.pointerInfo.ptPixelLocation.y}, {self.parse_flag(self.pointerInfo.pointerFlags)})"

    @staticmethod
    def parse_flag(flag: int) -> str:
        """Convert a flag to a human-readable string."""
        temp = []
        for flags, flagname in {
            Const.down: "DOWN",
            Const.in_range: "INRANGE",
            Const.in_contact: "INCONTACT",
            Const.update: "UPDATE",
            Const.up: "UP",
            Const.canceled: "CANCELED",
        }.items():
            if flag & flags:
                temp.append(flagname)
        return " | ".join(temp) if temp else "0"