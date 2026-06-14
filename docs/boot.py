import time, sensor, pyb, os, sys

# ---- Strip BOM from all .py files (self-healing) ----
for name in os.listdir('.'):
    if name.endswith('.py'):
        try:
            f = open(name, 'rb')
            d = f.read()
            f.close()
            if len(d) >= 3 and d[:3] == b'\xef\xbb\xbf':
                open(name, 'wb').write(d[3:])
        except:
            pass

# ---- Imports ----
from src.config import CAM_CFG
from src.pipeline import process_frame


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
    for t in ("RECT", "CIRCLE", "TRI", "SHAPE"):
        if status.startswith(t):
            return t
    return "NONE"


# ---- Main ----
sensor.reset()
sensor.set_pixformat(CAM_CFG["pixformat"])
sensor.set_framesize(CAM_CFG["framesize"])
sensor.skip_frames(time=CAM_CFG["warmup_ms"])
sensor.set_auto_gain(CAM_CFG["auto_gain"])
sensor.set_auto_whitebal(CAM_CFG["auto_whitebal"])

clock = time.clock()
led_ok = pyb.LED(2)
led_run = pyb.LED(3)
led_err = pyb.LED(1)
led_ok.on()
led_err.off()

uart = pyb.UART(3, 115200, timeout_char=10)

print("BOOT: %s %dx%d UART3->H7"
      % (_pixformat_name(CAM_CFG["pixformat"]), sensor.width(), sensor.height()))

dumped = False
frame_id = 0
while True:
    clock.tick()
    frame_id += 1
    led_run.toggle()

    try:
        img = sensor.snapshot()
        result = process_frame(img)

        status = result.get("status", "???")
        d_val = result.get("d_mm", 0)
        x_val = result.get("x_mm", 0)

        if not dumped and status[:3] in ("REC", "CIR", "TRI"):
            dumped = True
            print("RESULT keys: %s" % sorted(result.keys()))
            for k in sorted(result.keys()):
                print("  %s = %s" % (k, repr(result[k])))

        shape = _shape_from_status(status)
        img.draw_string(2, 2, "FPS: %.1f" % clock.fps(), color=(255,255,255), scale=1)
        img.draw_string(2, 14, "FRAME: %d" % frame_id, color=(255,255,255), scale=1)
        img.draw_string(2, img.height()-12, _clip_text(status, 26), color=(255,255,255), scale=1)

        if d_val == 0 and x_val == 0 and status[:3] in ("REC", "CIR", "TRI"):
            for p in status.split():
                if p.startswith("D="):
                    try: d_val = float(p[2:])
                    except: pass
                if p.startswith("X="):
                    try: x_val = float(p[2:])
                    except: pass

        uart.write("D:%.1f,X:%.1f,S:%s\n" % (d_val, x_val, shape))

        if frame_id % 10 == 0:
            print("[F#%d] %s | D=%.1f X=%.1f FPS=%.1f"
                  % (frame_id, status, d_val, x_val, clock.fps()))

        led_err.off()
    except Exception as exc:
        led_err.on()
        pyb.delay(120)
        print("[ERR] %s" % exc)