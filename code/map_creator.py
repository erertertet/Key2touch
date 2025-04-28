#!/usr/bin/env python3
import ctypes
from ctypes.wintypes import POINT
import time
import os

def get_mouse_position() -> tuple[int, int]:
    """Return the current cursor position as (x, y)."""
    pt = POINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
        raise ctypes.WinError()
    return pt.x, pt.y

def wait_for_mouse_click() -> None:
    """Wait until the user clicks the left mouse button."""
    print("Please click at the desired location...")
    # 0x01 is the virtual key code for the left mouse button
    while True:
        if ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000:
            # Wait for button release to avoid multiple detections
            time.sleep(0.1)
            return

def get_mouse_click_position() -> tuple[int, int]:
    """Wait for mouse click and return position as (x, y)."""
    wait_for_mouse_click()
    return get_mouse_position()

def main():
    print("press Ctrl+C to exit")
    while True:
        name = input("name of the mapping to create: ")
        if os.path.exists(f"mappings/{name}.txt"):
            print("File already exists, please choose a different name.")
            continue
        else:
            break

    mapper: dict[str | tuple[str, ...], tuple[int, int]] = dict()

    while True:
        key = input("Enter the key(s) to map: ")
        print("click to confirm the position")
        if key == 'done':
            break

        if len(key) > 1:
            mapper[tuple(key)] = get_mouse_click_position()
        else:
            mapper[key] = get_mouse_click_position()

    with open(f"mappings/{name}.txt", "w") as f:
        f.write(f"{mapper}")

if __name__ == "__main__":
    main()