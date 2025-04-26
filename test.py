#!/usr/bin/env python3
import threading
import time
import ctypes
from ctypes import Structure, byref
from ctypes.wintypes import UINT, INT, HANDLE, HWND, POINT, RECT, DWORD, BOOL
import keyboard
import argparse
from ast import literal_eval

# --- WinAPI constants ---
PT_TOUCH               = 0x00000002
POINTER_FLAG_DOWN      = 0x00010000
POINTER_FLAG_INRANGE   = 0x00000002
POINTER_FLAG_INCONTACT = 0x00000004
POINTER_FLAG_UPDATE    = 0x00020000
POINTER_FLAG_UP        = 0x00040000
TOUCH_MASK_ALL         = 0x00000007
TOUCH_FLAG_NONE        = 0x00000000
POINTER_FLAG_CANCELED  = 0x00008000

# --- ctypes STRUCTs ---
class POINTER_INFO(Structure):
    _fields_ = [
        ("pointerType",      UINT),
        ("pointerId",        UINT),
        ("frameId",          UINT),
        ("pointerFlags",     INT),
        ("sourceDevice",     HANDLE),
        ("hwndTarget",       HWND),
        ("ptPixelLocation",  POINT),
        ("ptHimetricLocation", POINT),
        ("ptPixelLocationRaw", POINT),
        ("ptHimetricLocationRaw", POINT),
        ("dwTime",           DWORD),
        ("historyCount",     UINT),
        ("inputData",        INT),
        ("dwKeyStates",      DWORD),
        ("PerformanceCount", ctypes.c_uint64),
        ("ButtonChangeType", INT),
    ]

class POINTER_TOUCH_INFO(Structure):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("touchFlags",  INT),
        ("touchMask",   INT),
        ("rcContact",   RECT),
        ("rcContactRaw", RECT),
        ("orientation", UINT),
        ("pressure",    UINT),
    ]

# --- Load config file ---
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file",)


args = parser.parse_args()
filename = args.file

# --- Your key→screen‐coords mapping ---
key_positions = literal_eval(open(f"mappings/{filename}", "r").read())

_multiples = {key: pos for key, pos in key_positions.items() if isinstance(key, tuple)}

# Unique pointer ID per key
pointer_ids = {key: idx for idx, key in enumerate(key_positions)}

# Track pressed keys (to suppress auto-repeat) & active touches
pressed_keys = set()
active_touches = {}
touch_lock = threading.Lock()

# Load and initialize touch injection
user32 = ctypes.windll.user32
if not user32.InitializeTouchInjection(len(key_positions), 1):
    raise OSError(f"InitializeTouchInjection failed: {ctypes.FormatError(ctypes.GetLastError())}")
user32.InjectTouchInput.argtypes = (UINT, ctypes.POINTER(POINTER_TOUCH_INFO))
user32.InjectTouchInput.restype  = BOOL

def make_touch_info(key: str) -> POINTER_TOUCH_INFO:
    """Create a POINTER_TOUCH_INFO for key’s mapped position."""
    x, y = key_positions[key]
    pid = pointer_ids[key]
    pi = POINTER_INFO(
        pointerType=PT_TOUCH,
        pointerId=pid,
        ptPixelLocation=POINT(x, y)  # other fields default to zero
    )
    return POINTER_TOUCH_INFO(
        pointerInfo=pi,
        touchFlags=TOUCH_FLAG_NONE,
        touchMask=TOUCH_MASK_ALL,
        rcContact=RECT(x-5, y-5, x+5, y+5)  # contact area
    )

def inject_contacts(contacts: list[POINTER_TOUCH_INFO]):
    """Batch-inject all provided contacts in one InjectTouchInput call."""
    count = len(contacts)
    if count == 0:
        return
    ArrayType = POINTER_TOUCH_INFO * count
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
            # if not active_touches:
            #     break
            # Mark all as UPDATE
            for pti in active_touches.values():
                pti.pointerInfo.pointerFlags = (
                    POINTER_FLAG_UPDATE | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT
                )
            inject_contacts(list(active_touches.values()))

def on_key_event(event):
    key = event.name
    if key not in key_positions:
        return

    if event.event_type == "down":
        # ignore OS auto-repeat
        if key in pressed_keys:
            return
        
        for k in pressed_keys:
            if key in k:
                return

        print(active_touches, pressed_keys)

        with touch_lock:
            # existing → UPDATE
            for pti in active_touches.values():
                pti.pointerInfo.pointerFlags = (
                    POINTER_FLAG_UPDATE | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT
                )
            
            for multiple_key in _multiples:
                if key in multiple_key and set(multiple_key).issubset(pressed_keys | {key}):
                    pressed_keys.add(multiple_key)
                    pti = make_touch_info(multiple_key)
                    pti.pointerInfo.pointerFlags = (
                        POINTER_FLAG_DOWN | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT
                    )
                    active_touches[multiple_key] = pti

                    for m in set(multiple_key) - {key}:
                        active_touches[m].pointerInfo.pointerFlags = (
                            POINTER_FLAG_CANCELED | POINTER_FLAG_UP
                        )
                    
                    inject_contacts(list(active_touches.values()))
                    
                    for m in set(multiple_key) - {key}:
                        del active_touches[m]
                        pressed_keys.remove(m)
                    
                    print(active_touches, pressed_keys)
                    return

            # new → DOWN
            pti = make_touch_info(key)
            pti.pointerInfo.pointerFlags = (
                POINTER_FLAG_DOWN | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT
            )
            active_touches[key] = pti
            inject_contacts(list(active_touches.values()))

            pressed_keys.add(key)
            print(active_touches, pressed_keys)

        # start the updater thread (if not already)
        # global updater_thread
        # if not updater_thread.is_alive():
        #     updater_thread = threading.Thread(target=update_loop, daemon=True)
        #     updater_thread.start()

    elif event.event_type == "up":
        for k in pressed_keys:
            if key in k or k == key:
                break
        else:
            return

        with touch_lock:
            # this one → UP; others → UPDATE
            multiples_to_remove = []

            print(active_touches, pressed_keys)
            for k, pti in list(active_touches.items()):
                if k == key:
                    if len(active_touches) == 1:
                        pti.pointerInfo.pointerFlags = POINTER_FLAG_UP | POINTER_FLAG_INRANGE
                    else:
                        pti.pointerInfo.pointerFlags = POINTER_FLAG_UP | POINTER_FLAG_CANCELED
                elif key in k:
                    pti.pointerInfo.pointerFlags = POINTER_FLAG_CANCELED | POINTER_FLAG_UP
                    multiples_to_remove.append(k)
                    for m in set(k) - {key}:
                        npti = make_touch_info(m)
                        npti.pointerInfo.pointerFlags = (
                            POINTER_FLAG_DOWN | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT
                        )
                        active_touches[m] = npti
                        pressed_keys.add(m)
                else:
                    pti.pointerInfo.pointerFlags = (
                        POINTER_FLAG_UPDATE | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT
                    )
            inject_contacts(list(active_touches.values()))
            # remove the lifted contact
            if key in active_touches:
                del active_touches[key]
                pressed_keys.remove(key)

            for k in multiples_to_remove:
                del active_touches[k]
                pressed_keys.remove(k)

            print(active_touches, pressed_keys)

# prepare the updater thread placeholder
updater_thread = threading.Thread(target=update_loop, daemon=True)
updater_thread.start()

# hook into global keyboard events
keyboard.hook(on_key_event)

print("Touch-injection mapping active. Press & hold mapped keys (a, s, d, f). Ctrl+C to quit.")
keyboard.wait()
