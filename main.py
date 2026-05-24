import time
import sensor
import pyb
import sys
from pyb import SPI          ### NEW: OpenMV 的 SPI 模块（注意命名冲突）
from pyb import SPI, Pin

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

def setup_spi():
    spi = SPI(
        2,                    # SPI2 总线
        SPI.MASTER,           # 枚举值变了
        baudrate=8000000,
        polarity=0,
        phase=0,
        bits=8,
        firstbit=SPI.MSB
    )
    return spi


def send_frame_spi(spi, nss_pin, img):
    w, h = img.width(), img.height()
    pixels = bytearray(img)
    nss_pin.low()
    spi.send(bytearray([(w >> 8) & 0xFF, w & 0xFF,
                        (h >> 8) & 0xFF, h & 0xFF]))
    for i in range(0, len(pixels), 256):
        spi.send(pixels[i:i + 256])
    nss_pin.high()


def send_image_over_spi(spi, img):
    """
    协议：2B 宽度 + 2B 高度 + N 字节灰度像素
    发送前先拉 NSS，发完后释放 NSS
    """
    w = img.width()
    h = img.height()
    pixels = img.bytearray()  # 灰度图像：每个像素 1 字节
    buf = bytearray(4 + len(pixels))
    buf[0] = (w >> 8) & 0xFF
    buf[1] = w & 0xFF
    buf[2] = (h >> 8) & 0xFF
    buf[3] = h & 0xFF
    buf[4:] = pixels

    # 分块发送，避免单次 SPI 传输过大
    CHUNK = 256
    for i in range(0, len(buf), CHUNK):
        end = min(i + CHUNK, len(buf))
        spi.send(buf[i:end])

def _draw_debug_overlay(img, fps, status, frame_id):
    img.draw_string(2, 2, "FPS: %.1f" % fps, color=(255, 255, 255), scale=1)
    img.draw_string(2, 14, "FRAME: %d" % frame_id, color=(255, 255, 255), scale=1)
    img.draw_string(2, img.height() - 12, _clip_text(status, 26), color=(255, 255, 255), scale=1)


def main():
    info = setup_sensor()
    spi = setup_spi()           ### NEW
    clock = time.clock()
    led_ok = pyb.LED(2)
    led_run = pyb.LED(3)
    led_err = pyb.LED(1)
    led_ok.on()
    led_err.off()

    # 初始化 UART3：P4(TX), P5(RX), 115200 8N1，发给 H743
    uart = pyb.UART(3, 115200, timeout_char=10)   ### NEW

    print("MAIN: sensor init done")
    print(
        "MAIN: %s %dx%d warmup=%dms"
        % (info["pixformat"], info["width"], info["height"], info["warmup_ms"])
    )

    frame_id = 0
    while True:
        clock.tick()
        frame_id += 1
        led_run.toggle()

        try:
            img = sensor.snapshot()
            result = process_frame(img)
            _draw_debug_overlay(img, clock.fps(), result["status"], frame_id)

            # UART 发 D/X
            line = result["uart_line"]
            parts = {}
            for pair in line.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    parts[k] = v
            d_val = float(parts.get("D", 0))
            x_val = float(parts.get("X", 0))
            uart.write("D:%.1f,X:%.1f\n" % (d_val, x_val))

            # SPI 发图像
            send_frame_spi(spi, nss, img)

            led_err.off()
        except Exception as exc:
            led_err.on()
            pyb.delay(120)


if __name__ == "__main__":
    main()
