import ctypes
from ctypes import Structure, byref
from ctypes.wintypes import UINT, INT, HANDLE, HWND, POINT, RECT, DWORD, BOOL
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
        temp: list[str] = []
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

user32 = ctypes.windll.user32
user32.InjectTouchInput.argtypes = (UINT, ctypes.POINTER(Pointer_Touch_Info))
user32.InjectTouchInput.restype = BOOL

def is_foreground_target(target: str) -> bool:
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value == target


inited = False

def inject_contacts(
    contacts: dict[str | tuple[str, ...], Pointer_Touch_Info], keycount: int
):
    global inited
    """Batch-inject all provided contacts in one InjectTouchInput call."""
    count = len(contacts)
    if count == 0:
        return

    # TODO uncomment this when using in-game
    # if not is_foreground_target(TARGET):
    #     return

    cont_list = list(contacts.values())

    if not inited:
        if not user32.InitializeTouchInjection(keycount, 1):
            raise OSError(
                (
                    "InitializeTouchInjection failed: ",
                    f"{ctypes.FormatError(ctypes.GetLastError())}",
                )
            )
        inited = True
    if count == 1 and cont_list[0].pointerInfo.pointerFlags & Const.up:
        inited = False
    ArrayType = Pointer_Touch_Info * count
    arr = ArrayType(*cont_list)
    # ByRef the first element to get POINTER_TOUCH_INFO*
    if not user32.InjectTouchInput(count, byref(arr[0])):
        err = ctypes.GetLastError()
        print(f"InjectTouchInput failed: {ctypes.FormatError(err)}")

def make_touch_info(
    key: str | tuple[str, ...], flags: int, pos: tuple[int, int], pid: int
) -> Pointer_Touch_Info:
    """Create a POINTER_TOUCH_INFO for key’s mapped position."""
    x, y = pos
    pi = Pointer_Info(
        pointerFlags=flags,
        pointerType=Const.pt_touch,
        pointerId=pid,
        ptPixelLocation=POINT(x, y),  # other fields default to zero
    )
    return Pointer_Touch_Info(
        pointerInfo=pi,
        touchFlags=Const.none,
        touchMask=Const.mask_all,
        rcContact=RECT(x - 5, y - 5, x + 5, y + 5),  # contact area
    )