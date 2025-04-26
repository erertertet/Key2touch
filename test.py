#!/usr/bin/env python3
import threading
import time
import keyboard
from ast import literal_eval
from utils import Const, Pointer_Touch_Info, inject_contacts, make_touch_info


def update_loop(interval: float = 0.05):
    """
    While any keys are held, send UPDATE frames every `interval` seconds
    so the system doesn’t cancel your press-and-hold.
    """
    # TODO: quit the loop depending on main worker thread
    while True:
        time.sleep(interval)
        if ending:
            break
        with touch_lock:
            for pti in active_touches.values():
                pti.pointerInfo.pointerFlags = (
                    Const.update | Const.in_range | Const.in_contact
                )
            inject_contacts(active_touches, len(key_position), TARGET)


def on_key_event(event: keyboard.KeyboardEvent):
    # TODO refactor out the key function
    """Handle keyboard events and inject touch events accordingly."""
    key = event.name
    if key not in key_position:
        return

    if event.event_type == "down":
        # ignore OS auto-repeat
        for k in active_touches.keys():
            if (isinstance(k, tuple) and key in k) or k == key:
                return

        with touch_lock:
            # existing → UPDATE
            for pti in active_touches.values():
                pti.pointerInfo.pointerFlags = (
                    Const.update | Const.in_range | Const.in_contact
                )

            for multiple_key in _multiples:
                if key in multiple_key and set(multiple_key).issubset(
                    set(active_touches.keys()) | {key}
                ):
                    active_touches[multiple_key] = make_touch_info(
                        (Const.down | Const.in_range | Const.in_contact),
                        key_position[multiple_key],
                        pointer_ids[multiple_key],
                    )

                    for m in set(multiple_key) - {key}:
                        active_touches[m].pointerInfo.pointerFlags = (
                            Const.canceled | Const.up
                        )

                    inject_contacts(active_touches, len(key_position), TARGET)

                    for m in set(multiple_key) - {key}:
                        del active_touches[m]

                    return

            # new → DOWN
            active_touches[key] = make_touch_info(
                (Const.down | Const.in_range | Const.in_contact),
                key_position[key],
                pointer_ids[key],
            )
            inject_contacts(active_touches, len(key_position), TARGET)

    elif event.event_type == "up":
        for k in active_touches.keys():
            if key in k or k == key:
                break
        else:
            return

        with touch_lock:
            # this one → UP; others → UPDATE
            multiples_to_remove: list[str | tuple[str, ...]] = []

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
                        active_touches[m] = make_touch_info(
                            (Const.down | Const.in_range | Const.in_contact),
                            key_position[m],
                            pointer_ids[m],
                        )
                else:
                    pti.pointerInfo.pointerFlags = (
                        Const.update | Const.in_range | Const.in_contact
                    )
            inject_contacts(active_touches, len(key_position), TARGET)
            # remove the lifted contact
            if key in active_touches:
                del active_touches[key]

            for k in multiples_to_remove:
                del active_touches[k]


key_position: dict[str | tuple[str, ...], tuple[int, int]] = {}
active_touches: dict[str | tuple[str, ...], Pointer_Touch_Info] = {}
touch_lock = threading.Lock()
main_thread: threading.Thread | None = None
ending = False

def main(mapping_file: str, target: str):
    """Main function to set up the touch injection and keyboard hooks."""
    global key_position, TARGET, _multiples, pointer_ids, main_thread

    TARGET = target

    main_thread = threading.current_thread()

    key_position = literal_eval(open(f"mappings/{mapping_file}", "r").read())

    _multiples = {key for key in key_position.keys() if isinstance(key, tuple)}
    pointer_ids = {key: idx for idx, key in enumerate(key_position)}

    # init_values(KEY_POSITION)
    # prepare the updater thread placeholder
    updater_thread = threading.Thread(target=update_loop, daemon=True)
    updater_thread.start()

    # hook into global keyboard events
    keyboard.hook(on_key_event)
    keyboard.wait("ctrl+q")  # wait for Ctrl+Q to exit

    global ending
    ending = True  # signal the updater thread to stop

    keyboard.unhook_all()
    updater_thread.join()

    print("mapper stopped")


if __name__ == "__main__":
    main("shadow.txt", "Shadow Fight 2")
