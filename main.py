import time
import sensor
import pyb

from src.config import CAM_CFG
from src.pipeline import process_frame


def _extract_shape_type(status):
    """Extract shape type from status string like 'RECT D=320 X=15'"""
    if not status:
        return "NONE"
    if status.startswith("NO_A4"):
        return "NONE"
    if status.startswith("A4 "):
        return "NONE"
    for t in ("RECT", "CIRCLE", "TRI", "SHAPE"):
        if status.startswith(t):
            return t
    return "NONE"


def setup_sensor():
    sensor.reset()
    sensor.set_pixformat(CAM_CFG["pixformat"])
    sensor.set_framesize(CAM_CFG["framesize"])
    sensor.skip_frames(time=CAM_CFG["warmup_ms"])


def main():
    setup_sensor()
    clock = time.clock()
    led_err = pyb.LED(1)
    led_ok = pyb.LED(2)
    led_run = pyb.LED(3)
    led_ok.on()
    led_err.off()

    # UART3: P4(TX) -> H7 PC11(RX), 115200 8N1
    uart = pyb.UART(3, 115200, timeout_char=10)

    print("Sensor ready, UART3 -> H7")
    frame_id = 0

    while True:
        clock.tick()
        frame_id += 1
        led_run.toggle()

        try:
            img = sensor.snapshot()
            result = process_frame(img)

            d_val = result.get("d_mm", 0)
            x_val = result.get("x_mm", 0)
            shape = _extract_shape_type(result.get("status", ""))

            # UART3 -> H7: D, X, shape type
            uart.write("D:%.1f,X:%.1f,S:%s\n" % (d_val, x_val, shape))

            # PC debug
            print("[F#%d] D=%.1f X=%.1f S=%s FPS=%.1f"
                  % (frame_id, d_val, x_val, shape, clock.fps()))

            led_err.off()
        except Exception as exc:
            led_err.on()
            pyb.delay(120)
            print("[ERR] frame %d: %s" % (frame_id, exc))


if __name__ == "__main__":
    main()