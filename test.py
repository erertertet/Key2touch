#!/usr/bin/env python3
import threading
import time
import ctypes
from ctypes import Structure, byref
from ctypes.wintypes import UINT, INT, HANDLE, HWND, POINT, RECT, DWORD, BOOL
import keyboard
import argparse
from ast import literal_eval
import sys
from enum import IntEnum
# import utils

# --- WinAPI constants ---

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

# --- Load config file ---
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file",)


args = parser.parse_args()
filename = args.file

KEY_POSITION = literal_eval(open(f"mappings/{filename}", "r").read())
TARGET = "Shadow Fight 2"

_multiples = {key: pos for key, pos in KEY_POSITION.items() if isinstance(key, tuple)}

# Unique pointer ID per key
pointer_ids = {key: idx for idx, key in enumerate(KEY_POSITION)}

# Track pressed keys (to suppress auto-repeat) & active touches
pressed_keys = set()
active_touches = {}
touch_lock = threading.Lock()
inited = False

# Load and initialize touch injection
user32 = ctypes.windll.user32
user32.InjectTouchInput.argtypes = (UINT, ctypes.POINTER(Pointer_Touch_Info))
user32.InjectTouchInput.restype  = BOOL

def is_foreground_target() -> bool:
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value == TARGET

def make_touch_info(key: str) -> Pointer_Touch_Info:
    """Create a POINTER_TOUCH_INFO for key’s mapped position."""
    x, y = KEY_POSITION[key]
    pid = pointer_ids[key]
    pi = Pointer_Info(
        pointerType=Const.pt_touch,
        pointerId=pid,
        ptPixelLocation=POINT(x, y)  # other fields default to zero
    )
    return Pointer_Touch_Info(
        pointerInfo=pi,
        touchFlags=Const.none,
        touchMask=Const.mask_all,
        rcContact=RECT(x-5, y-5, x+5, y+5)  # contact area
    )

def inject_contacts(contacts: list[Pointer_Touch_Info]):
    global inited
    """Batch-inject all provided contacts in one InjectTouchInput call."""
    count = len(contacts)
    if count == 0:
        return

    # TODO uncomment this when using in-game
    # if not is_foreground_target():
    #     return

    if not inited:
        if not user32.InitializeTouchInjection(len(KEY_POSITION), 1):
            raise OSError(f"InitializeTouchInjection failed: {ctypes.FormatError(ctypes.GetLastError())}")
        inited = True
    if count == 1 and contacts[0].pointerInfo.pointerFlags & Const.up:
        inited = False
    ArrayType = Pointer_Touch_Info * count
    arr = ArrayType(*contacts)
    # ByRef the first element to get POINTER_TOUCH_INFO*
    if not user32.InjectTouchInput(count, byref(arr[0])):
        err = ctypes.GetLastError()
        print(f"InjectTouchInput failed: {ctypes.FormatError(err)}")

def update_loop(interval: float = 0.05):
    """
    While any keys are held, send UPDATE frames every `interval` seconds
    so the system doesn’t cancel your press-and-hold.
    """
    while True:
        time.sleep(interval)
        with touch_lock:
            for pti in active_touches.values():
                pti.pointerInfo.pointerFlags = (
                    Const.update | Const.in_range | Const.in_contact
                )
            inject_contacts(list(active_touches.values()))

def on_key_event(event):
    key = event.name
    if key not in KEY_POSITION:
        return

    if event.event_type == "down":
        # ignore OS auto-repeat
        if key in pressed_keys:
            return
        
        for k in pressed_keys:
            if key in k:
                return

        with touch_lock:
            # existing → UPDATE
            for pti in active_touches.values():
                pti.pointerInfo.pointerFlags = (
                    Const.update | Const.in_range | Const.in_contact
                )
            
            for multiple_key in _multiples:
                if key in multiple_key and set(multiple_key).issubset(pressed_keys | {key}):
                    pressed_keys.add(multiple_key)
                    pti = make_touch_info(multiple_key)
                    pti.pointerInfo.pointerFlags = (
                        Const.down | Const.in_range | Const.in_contact
                    )
                    active_touches[multiple_key] = pti

                    for m in set(multiple_key) - {key}:
                        active_touches[m].pointerInfo.pointerFlags = (
                            Const.canceled | Const.up
                        )
                    
                    inject_contacts(list(active_touches.values()))
                    
                    for m in set(multiple_key) - {key}:
                        del active_touches[m]
                        pressed_keys.remove(m)
                    
                    return

            # new → DOWN
            pti = make_touch_info(key)
            pti.pointerInfo.pointerFlags = (
                Const.down | Const.in_range | Const.in_contact
            )
            active_touches[key] = pti
            inject_contacts(list(active_touches.values()))

            pressed_keys.add(key)

    elif event.event_type == "up":
        for k in pressed_keys:
            if key in k or k == key:
                break
        else:
            return

        with touch_lock:
            # this one → UP; others → UPDATE
            multiples_to_remove = []

            for k, pti in list(active_touches.items()):
                if k == key:
                    if len(active_touches) == 1:
                        pti.pointerInfo.pointerFlags = Const.up | Const.in_range
                    else:
                        pti.pointerInfo.pointerFlags = Const.up | Const.canceled
                elif key in k:
                    pti.pointerInfo.pointerFlags = Const.canceled | Const.up
                    multiples_to_remove.append(k)
                    for m in set(k) - {key}:
                        npti = make_touch_info(m)
                        npti.pointerInfo.pointerFlags = (
                            Const.down | Const.in_range | Const.in_contact
                        )
                        active_touches[m] = npti
                        pressed_keys.add(m)
                else:
                    pti.pointerInfo.pointerFlags = (
                        Const.update | Const.in_range | Const.in_contact
                    )
            inject_contacts(list(active_touches.values()))
            # remove the lifted contact
            if key in active_touches:
                del active_touches[key]
                pressed_keys.remove(key)

            for k in multiples_to_remove:
                del active_touches[k]
                pressed_keys.remove(k)


# prepare the updater thread placeholder
updater_thread = threading.Thread(target=update_loop, daemon=True)
updater_thread.start()

# hook into global keyboard events
keyboard.hook(on_key_event)

print("Touch-injection mapping active. Press & hold mapped keys (a, s, d, f). Ctrl+C to quit.")
keyboard.wait()
