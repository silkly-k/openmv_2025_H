import time
import sensor
import pyb
import sys
from pyb import SPI, Pin

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
        2,                    # SPI2
        SPI.MASTER,           # host mode
        baudrate=8000000,     # 8 MHz
        polarity=0,
        phase=0,
        bits=8,
        firstbit=SPI.MSB
    )
    return spi


def _dbg(msg, uart=None):
    """Unified debug output: PC via print(USB VCP), H7 via uart.write"""
    if DEBUG_TO_PC:
        print(msg)
    elif uart is not None:
        uart.write(msg + "\r\n")


def send_frame_spi_debug(spi, img, uart, frame_id):
    """SPI send image frame with detailed debug info.
    NSS is held LOW externally -- no toggling here."""
    import pyb

    t0 = pyb.micros()
    w, h = img.width(), img.height()
    pixels = bytearray(img)
    pixel_count = len(pixels)
    bpp = 1 if img.format() == sensor.GRAYSCALE else 2
    bpp_name = "GRAY" if bpp == 1 else "RGB565"

    # header: 2B width + 2B height
    header = bytearray([
        (w >> 8) & 0xFF, w & 0xFF,
        (h >> 8) & 0xFF, h & 0xFF,
    ])
    total_bytes = len(header) + pixel_count

    # ---- pre-send debug ----
    _dbg("[SPI] === FRAME %d START ===" % frame_id, uart)
    _dbg("[SPI] fmt=%s w=%d h=%d bpp=%d" % (bpp_name, w, h, bpp), uart)
    _dbg("[SPI] header=%dB pixels=%dB total=%dB"
         % (len(header), pixel_count, total_bytes), uart)

    # ---- send header (NSS held low externally) ----
    t1 = pyb.micros()
    spi.send(header)
    t2 = pyb.micros()

    # ---- chunked pixel send ----
    CHUNK = 256
    chunk_count = (pixel_count + CHUNK - 1) // CHUNK
    chunk_times = []
    for i in range(0, pixel_count, CHUNK):
        tc0 = pyb.micros()
        spi.send(pixels[i:i + CHUNK])
        tc1 = pyb.micros()
        chunk_times.append(tc1 - tc0)

    t3 = pyb.micros()

    # ---- post-send debug ----
    total_us = t3 - t0
    header_us = t2 - t1
    pixel_us = t3 - t2
    avg_chunk_us = sum(chunk_times) // len(chunk_times) if chunk_times else 0
    max_chunk_us = max(chunk_times) if chunk_times else 0
    min_chunk_us = min(chunk_times) if chunk_times else 0
    fps_est = 1_000_000.0 / total_us if total_us > 0 else 0

    # first/last 8 bytes as verification reference
    first8 = " ".join("%02X" % b for b in pixels[:8])
    last8 = " ".join("%02X" % b for b in pixels[-8:])

    _dbg("[SPI] header: %d us" % header_us, uart)
    _dbg("[SPI] chunks: %d x %dB | avg=%d min=%d max=%d us"
         % (chunk_count, CHUNK, avg_chunk_us, min_chunk_us, max_chunk_us), uart)
    _dbg("[SPI] pixel-total: %d us | frame-total: %d us"
         % (pixel_us, total_us), uart)
    _dbg("[SPI] BW ~%.1f KB/s | SPI-max ~%.1f fps"
         % (total_bytes * 1_000_000.0 / total_us / 1024.0, fps_est), uart)
    _dbg("[SPI] data[0..7]:  %s" % first8, uart)
    _dbg("[SPI] data[-8..-1]:%s" % last8, uart)
    _dbg("[SPI] === FRAME %d END ===" % frame_id, uart)

    return {
        "total_us": total_us,
        "header_us": header_us,
        "pixel_us": pixel_us,
        "chunk_count": chunk_count,
        "avg_chunk_us": avg_chunk_us,
        "total_bytes": total_bytes,
    }


def _draw_debug_overlay(img, fps, status, frame_id):
    img.draw_string(2, 2, "FPS: %.1f" % fps, color=(255, 255, 255), scale=1)
    img.draw_string(2, 14, "FRAME: %d" % frame_id, color=(255, 255, 255), scale=1)
    img.draw_string(2, img.height() - 12, _clip_text(status, 26),
                    color=(255, 255, 255), scale=1)


def main():
    info = setup_sensor()
    spi = setup_spi()
    clock = time.clock()
    led_ok = pyb.LED(2)
    led_run = pyb.LED(3)
    led_err = pyb.LED(1)
    led_ok.on()
    led_err.off()

    # UART3: P4(TX), P5(RX), 115200 8N1 -> H743
    uart = pyb.UART(3, 115200, timeout_char=10)

    # NSS chip-select pin (P3) -- held LOW continuously
    nss = Pin("P3", Pin.OUT_PP)
    nss.low()

    print("========================================")
    print("MAIN: sensor init done")
    print("MAIN: %s %dx%d warmup=%dms"
          % (info["pixformat"], info["width"], info["height"], info["warmup_ms"]))
    print("MAIN: SPI2 baud=8MHz NSS=P3 (held LOW)")
    print("MAIN: UART3 baud=115200 -> H743")
    print("MAIN: DEBUG_TO_PC=%s" % DEBUG_TO_PC)
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

            # ---- UART3: clean D/X protocol to H7 ----
            d_val = result.get("d_mm", 0)
            x_val = result.get("x_mm", 0)
            uart.write("D:%.1f,X:%.1f\n" % (d_val, x_val))

            # ---- PC debug: timing summary ----
            print("[TIMING] F#%d | CAP=%dus PROC=%dus FPS=%.1f | D=%.1f X=%.1f"
                  % (frame_id, t_cap, t_proc, clock.fps(), d_val, x_val))

            # ---- SPI send with detailed debug ----
            spi_info = send_frame_spi_debug(spi, img, uart, frame_id)

            led_err.off()
        except Exception as exc:
            led_err.on()
            pyb.delay(120)
            print("[ERR] frame %d: %s" % (frame_id, str(exc)))


if __name__ == "__main__":
    main()