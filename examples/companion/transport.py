"""Animated-QR transport for talking to a real SeedSigner, modelled on the
proven ``scripts/cardano_companion_test.py`` GUI.

A single Tkinter window shows the request QR (animated, left) and the live
webcam (right) at the same time, and decodes the device's animated QR response
with pyzbar on grayscale frames. Tkinter is used instead of OpenCV's GUI so it
works with headless OpenCV builds. ``cv2``/``pyzbar``/``qrcode``/``pillow`` are
imported lazily so the rest of the companion (and the --simulator path) need
none of them.
"""

import time

from . import _paths  # noqa: F401

from seedsigner.helpers.ur2.ur_decoder import URDecoder

PANEL = 520


def _require(modname):
    import importlib
    try:
        return importlib.import_module(modname)
    except ImportError as e:
        raise ImportError(
            f"'{modname}' is required for hardware QR transport. "
            f"Install the demo extras: pip install -r examples/requirements.txt"
        ) from e


def qr_to_pil(data: str, size: int = PANEL):
    qrcode = _require("qrcode")
    from PIL import Image

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.NEAREST)


def probe_cameras(max_index: int = 8):
    cv2 = _require("cv2")
    print("Probing camera indices (a working camera shows >0 frames)...")
    found = []
    for idx in range(max_index):
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            cap.release()
            continue
        ok_count = 0
        for _ in range(10):
            ok, frame = cap.read()
            if ok and frame is not None:
                ok_count += 1
        cap.release()
        if ok_count:
            found.append(idx)
            print(f"  camera {idx}: OK ({ok_count}/10 frames)  ->  --camera {idx}")
        else:
            print(f"  camera {idx}: opened but delivered no frames")
    if not found:
        print("No usable camera. Ensure you're in the 'video' group and not using sudo.")
    return found


def exchange_qr(request_encoder, response_ur_type: str, *, camera: int = 0,
                width: int = 1280, height: int = 720, focus: int = None,
                fps: float = 6.0) -> bytes:
    """Show ``request_encoder``'s animated QR while watching the webcam for the
    device's ``response_ur_type`` UR. Returns the reassembled response CBOR.

    Side-by-side Tkinter window; close it (q / Esc / window button) to abort.
    """
    cv2 = _require("cv2")
    import tkinter as tk
    from PIL import Image, ImageTk
    pyzbar = _require("pyzbar.pyzbar")
    zbar_decode = pyzbar.decode

    decoder = URDecoder()
    prefix = f"UR:{response_ur_type.upper()}/"

    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        raise RuntimeError(f"could not open camera index {camera} (try --probe-cameras)")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    focus_state = {"value": focus, "auto": focus is None}

    def apply_focus():
        if focus_state["auto"]:
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        else:
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            if focus_state["value"] is None:
                focus_state["value"] = 30
            cap.set(cv2.CAP_PROP_FOCUS, float(focus_state["value"]))

    def adjust_focus(delta):
        focus_state["auto"] = False
        current = focus_state["value"] if focus_state["value"] is not None else 30
        focus_state["value"] = max(0, min(255, current + delta))
        apply_focus()

    def toggle_autofocus(*_):
        focus_state["auto"] = not focus_state["auto"]
        apply_focus()

    def focus_label():
        return "auto" if focus_state["auto"] else str(focus_state["value"])

    apply_focus()

    root = tk.Tk()
    root.title(f"Companion <-> Device  ({response_ur_type})")
    left = tk.Label(root)
    left.grid(row=0, column=0, padx=4, pady=4)
    right = tk.Label(root)
    right.grid(row=0, column=1, padx=4, pady=4)
    status = tk.Label(root, font=("TkDefaultFont", 12), anchor="w")
    status.grid(row=1, column=0, columnspan=2, sticky="we", padx=6, pady=4)

    result = {"cbor": None}
    state = {"done": False, "last": 0.0, "rendered": None,
             "part": request_encoder.next_part(), "qr": None, "cam": None}
    interval = 1.0 / max(fps, 0.5)

    def quit_app(*_):
        try:
            cap.release()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", quit_app)
    root.bind("<q>", quit_app)
    root.bind("<Escape>", quit_app)
    # Live focus tuning: +/- step the manual focus, 'a' toggles autofocus.
    root.bind("<plus>", lambda e: adjust_focus(5))
    root.bind("<equal>", lambda e: adjust_focus(5))
    root.bind("<KP_Add>", lambda e: adjust_focus(5))
    root.bind("<minus>", lambda e: adjust_focus(-5))
    root.bind("<KP_Subtract>", lambda e: adjust_focus(-5))
    root.bind("<a>", toggle_autofocus)

    def update():
        now = time.time()
        if not state["done"] and now - state["last"] >= interval:
            state["part"] = request_encoder.next_part()
            state["last"] = now

        if state["part"] != state["rendered"]:
            state["qr"] = ImageTk.PhotoImage(qr_to_pil(state["part"].upper()))
            left.configure(image=state["qr"])
            state["rendered"] = state["part"]

        ok, frame = cap.read()
        if ok:
            disp = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((PANEL, PANEL))
            state["cam"] = ImageTk.PhotoImage(disp)
            right.configure(image=state["cam"])
            if not state["done"]:
                gray = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
                for sym in zbar_decode(gray):
                    data = sym.data.decode("utf-8", errors="ignore")
                    if data.upper().startswith(prefix):
                        try:
                            decoder.receive_part(data)
                        except Exception:
                            pass
                if decoder.is_complete():
                    result["cbor"] = bytes(decoder.result_message().cbor)
                    state["done"] = True

        if state["done"]:
            status.configure(text="RESPONSE DECODED - closing ...")
            root.after(700, quit_app)
        else:
            pct = int(decoder.estimated_percent_complete() * 100)
            status.configure(
                text=f"response {pct}%   |   focus: {focus_label()}  "
                     f"(+/- adjust, 'a' autofocus, q quit)")
            root.after(30, update)

    root.after(0, update)
    root.mainloop()

    if result["cbor"] is None:
        raise RuntimeError("window closed before the response was fully scanned")
    return result["cbor"]
