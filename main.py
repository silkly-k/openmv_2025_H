import time
import sensor
import pyb
import sys

from src.config import CAM_CFG
from src.pipeline import process_frame


# ============================================================
# Debug output target: True=PC(print/USB)  False=H7(UART3)
# ============================================================
DEBUG_TO_PC = True


def _pixformat_name(pixformat):
    if pixformat == sensor.GRAYSCALE:
        return "GRAYSCALE"
    if pixformat == sensor.RGB565:
        return "RGB565"
    return str(pixformat)


def _clip_text(text, max_chars):
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3] + "..."


def _shape_from_status(status):
    """Extract shape type from status string like 'RECT D=320 X=15'"""
    for t in ("RECT", "CIRCLE", "TRI", "SHAPE"):
        if status.startswith(t):
            return t
    return "NONE"


def setup_sensor():
    sensor.reset()
    sensor.set_pixformat(CAM_CFG["pixformat"])
    sensor.set_framesize(CAM_CFG["framesize"])
    sensor.skip_frames(time=CAM_CFG["warmup_ms"])
    sensor.set_auto_gain(CAM_CFG["auto_gain"])
    sensor.set_auto_whitebal(CAM_CFG["auto_whitebal"])
    return {
        "pixformat": _pixformat_name(CAM_CFG["pixformat"]),
        "width": sensor.width(),
        "height": sensor.height(),
        "warmup_ms": CAM_CFG["warmup_ms"],
    }


def _draw_debug_overlay(img, fps, status, frame_id):
    img.draw_string(2, 2, "FPS: %.1f" % fps, color=(255, 255, 255), scale=1)
    img.draw_string(2, 14, "FRAME: %d" % frame_id, color=(255, 255, 255), scale=1)
    img.draw_string(2, img.height() - 12, _clip_text(status, 26),
                    color=(255, 255, 255), scale=1)


def main():
    info = setup_sensor()
    clock = time.clock()
    led_ok = pyb.LED(2)
    led_run = pyb.LED(3)
    led_err = pyb.LED(1)
    led_ok.on()
    led_err.off()

    # UART3: P4(TX), P5(RX), 115200 8N1 -> H743
    uart = pyb.UART(3, 115200, timeout_char=10)

    print("========================================")
    print("MAIN: sensor init done")
    print("MAIN: %s %dx%d warmup=%dms"
          % (info["pixformat"], info["width"], info["height"], info["warmup_ms"]))
    print("MAIN: UART3 baud=115200 -> H743")
    print("========================================")

    frame_id = 0
    while True:
        clock.tick()
        frame_id += 1
        led_run.toggle()

        try:
            t_cap_start = pyb.micros()
            img = sensor.snapshot()
            t_cap = pyb.micros() - t_cap_start

            t_proc_start = pyb.micros()
            result = process_frame(img)
            t_proc = pyb.micros() - t_proc_start

            _draw_debug_overlay(img, clock.fps(), result["status"], frame_id)

            # ---- UART3: send D/X/S to H7 ----
            d_val = result.get("d_mm", 0)
            x_val = result.get("x_mm", 0)
            shape = _shape_from_status(result.get("status", ""))
            uart.write("D:%.1f,X:%.1f,S:%s\n" % (d_val, x_val, shape))

            # ---- PC debug ----
            print("[F#%d] CAP=%dus PROC=%dus FPS=%.1f | D=%.1f X=%.1f S=%s"
                  % (frame_id, t_cap, t_proc, clock.fps(), d_val, x_val, shape))

            led_err.off()
        except Exception as exc:
            led_err.on()
            pyb.delay(120)
            print("[ERR] frame %d: %s" % (frame_id, str(exc)))


if __name__ == "__main__":
    main()