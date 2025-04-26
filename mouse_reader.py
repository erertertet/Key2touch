#!/usr/bin/env python3
import ctypes
import keyboard
from ctypes.wintypes import POINT

def get_mouse_position() -> tuple[int, int]:
    """Return the current cursor position as (x, y)."""
    pt = POINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
        raise ctypes.WinError()
    return pt.x, pt.y

def on_key_event(event: keyboard.KeyboardEvent) -> None:
    # Only act on key-down events
    if event.event_type == 'down':
        x, y = get_mouse_position()
        print(f"Key '{event.name}' pressed → Cursor at ({x}, {y})")

def main() -> None:
    print("Press any key; it will print the cursor position at that moment. Ctrl+C to exit.")
    keyboard.hook(on_key_event)
    keyboard.wait()  # blocks forever until Ctrl+C

if __name__ == "__main__":
    main()
