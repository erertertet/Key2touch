#!/usr/bin/env python3
import threading
import time
import ctypes
from ctypes import byref
from ctypes.wintypes import UINT, POINT, RECT, BOOL
import keyboard
from ast import literal_eval
from utils import Const, Pointer_Info, Pointer_Touch_Info

# Track pressed keys (to suppress auto-repeat) & active touches
active_touches = {}
touch_lock = threading.Lock()
inited = False

# Load and initialize touch injection
user32 = ctypes.windll.user32
user32.InjectTouchInput.argtypes = (UINT, ctypes.POINTER(Pointer_Touch_Info))
user32.InjectTouchInput.restype  = BOOL

def init_values(key2pos: dict[str, tuple[int, int]]):
    """Initialize global variables for touch injection."""
    global _multiples, pointer_ids
    _multiples = {key for key, pos in key2pos.items() if isinstance(key, tuple)}
    pointer_ids = {key: idx for idx, key in enumerate(key2pos)}

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
    # TODO: quit the loop depending on main worker thread
    while True:
        time.sleep(interval)
        with touch_lock:
            for pti in active_touches.values():
                pti.pointerInfo.pointerFlags = (
                    Const.update | Const.in_range | Const.in_contact
                )
            inject_contacts(list(active_touches.values()))

def on_key_event(event):
    # TODO refactor out the key function
    """Handle keyboard events and inject touch events accordingly."""
    key = event.name
    if key not in KEY_POSITION:
        return

    if event.event_type == "down":
        # ignore OS auto-repeat
        for k in active_touches.keys():
            if key in k or k == key:
                return

        with touch_lock:
            # existing → UPDATE
            for pti in active_touches.values():
                pti.pointerInfo.pointerFlags = (
                    Const.update | Const.in_range | Const.in_contact
                )
            
            for multiple_key in _multiples:
                if key in multiple_key and set(multiple_key).issubset(set(active_touches.keys()) | {key}):
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
                    
                    return

            # new → DOWN
            pti = make_touch_info(key)
            pti.pointerInfo.pointerFlags = (
                Const.down | Const.in_range | Const.in_contact
            )
            active_touches[key] = pti
            inject_contacts(list(active_touches.values()))


    elif event.event_type == "up":
        for k in active_touches.keys():
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
                else:
                    pti.pointerInfo.pointerFlags = (
                        Const.update | Const.in_range | Const.in_contact
                    )
            inject_contacts(list(active_touches.values()))
            # remove the lifted contact
            if key in active_touches:
                del active_touches[key]

            for k in multiples_to_remove:
                del active_touches[k]


# TODO make this main to be directly callable from other scripts
def main(mapping_file: str, target: str):
    """Main function to set up the touch injection and keyboard hooks."""
    global KEY_POSITION, TARGET, FILENAME

    FILENAME = mapping_file
    KEY_POSITION = literal_eval(open(f"mappings/{FILENAME}", "r").read())
    TARGET = target

    init_values(KEY_POSITION)
    # prepare the updater thread placeholder
    updater_thread = threading.Thread(target=update_loop, daemon=True)
    updater_thread.start()

    # hook into global keyboard events
    keyboard.hook(on_key_event)
    keyboard.wait()

if __name__ == "__main__":
    main("shadow.txt", "Shadow Fight 2")