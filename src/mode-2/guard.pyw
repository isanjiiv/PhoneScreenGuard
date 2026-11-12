"""Local webcam phone detection for the signed-in Windows desktop."""
import ctypes
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
import time

from PySide6 import QtCore, QtGui, QtWidgets

BASE = Path(__file__).resolve().parent
logging.basicConfig(
    handlers=[RotatingFileHandler(BASE / "guard.log", maxBytes=250_000, backupCount=1)],
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
CAMERA_INDEX = 0
PROTECTION_MODE = 2
CONFIDENCE = 0.45
RESTORE_SECONDS = 2.0
FRAME_TIMEOUT_SECONDS = 0.75


def frame_is_unusable(gray):
    # Dark and uniform feeds include physical shutters and some placeholders.
    pixels = gray[::4, ::4]
    if (pixels < 32).mean() >= 0.98 or pixels.std() < 3.0:
        return True

    if PROTECTION_MODE != 3:
        return False

    # A near-lens cover can create a broad brightness gradient while
    # removing almost all fine detail. Measure local contrast at native scale.
    sampled = gray[::2, ::2].astype("int16")
    horizontal = abs(sampled[:, 2:] - sampled[:, :-2])
    vertical = abs(sampled[2:, :] - sampled[:-2, :])
    if not horizontal.size or not vertical.size:
        return False
    return all(
        (differences >= 7).mean() < 0.005 and differences.mean() < 2.5
        for differences in (horizontal, vertical)
    )


class ScreenProtection:
    def __init__(self, now):
        self.started_at = now
        self.camera_blocked = False
        self.recovery_started = None

    def update(self, now, camera_state, last_phone, paused):
        frame_at, usable = camera_state
        stalled = now - (frame_at if frame_at is not None else self.started_at) >= FRAME_TIMEOUT_SECONDS
        phone_visible = now - last_phone < RESTORE_SECONDS
        if PROTECTION_MODE != 1 and (usable is False or stalled):
            self.camera_blocked = True
            self.recovery_started = None
        elif phone_visible or not usable:
            self.recovery_started = None
        elif self.camera_blocked:
            if self.recovery_started is None:
                self.recovery_started = now
            elif now - self.recovery_started >= RESTORE_SECONDS:
                self.camera_blocked = False
                self.recovery_started = None
        return not paused and (phone_visible or self.camera_blocked)


class Detector(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.stop = threading.Event()
        self.camera_state = (None, None)
        self.latest_frame = None
        self.last_phone = float("-inf")
        self.status = "Opening camera"
        self.model_status = "Loading phone detector"

    def publish_unusable(self):
        self.camera_state = (time.monotonic(), False)
        self.latest_frame = None

    def run(self):
        try:
            import cv2

            threading.Thread(target=self.detect_phones, daemon=True).start()
            while not self.stop.is_set():
                self.status = "Opening camera"
                capture = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
                try:
                    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    while capture.isOpened() and not self.stop.is_set():
                        ok, frame = capture.read()
                        if not ok or frame is None or not frame.size:
                            self.publish_unusable()
                            break

                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        if PROTECTION_MODE != 1 and frame_is_unusable(gray):
                            self.publish_unusable()
                            self.status = "Camera view dark or obstructed"
                        else:
                            now = time.monotonic()
                            self.camera_state = (now, True)
                            self.latest_frame = (now, frame)
                            self.status = "Monitoring"

                        # Bound CPU use without waiting for the phone model.
                        self.stop.wait(0.02)
                    self.publish_unusable()
                finally:
                    capture.release()
                self.status = "Camera unavailable. Retrying."
                self.stop.wait(3)
        except Exception:
            self.publish_unusable()
            self.status = "Camera error. See guard.log."
            logging.exception("Camera capture stopped")

    def detect_phones(self):
        try:
            from ultralytics import YOLO

            model_file = BASE / "yolo11n.pt"
            if not model_file.is_file():
                raise FileNotFoundError(model_file)
            model = YOLO(str(model_file))
            phone_class = next(key for key, name in model.names.items() if name == "cell phone")
            self.model_status = ""
            last_processed = None
            while not self.stop.is_set():
                sample = self.latest_frame
                if sample is None or sample[0] == last_processed:
                    self.stop.wait(0.03)
                    continue

                last_processed, frame = sample
                result = model.predict(
                    frame, classes=[phone_class], imgsz=640,
                    conf=CONFIDENCE, device="cpu", verbose=False, save=False,
                )[0]
                if len(result.boxes):
                    self.last_phone = time.monotonic()
                self.stop.wait(0.12)
        except Exception:
            self.model_status = "Phone detector error. See guard.log."
            logging.exception("Phone detection stopped")


class InputGuard:
    """Suppress desktop input only while an overlay is visible."""

    def __init__(self):
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        callback = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p
        )
        self.user.SetWindowsHookExW.argtypes = (
            ctypes.c_int, callback, ctypes.c_void_p, ctypes.c_uint32
        )
        self.user.SetWindowsHookExW.restype = ctypes.c_void_p
        self.user.UnhookWindowsHookEx.argtypes = (ctypes.c_void_p,)
        self.user.UnhookWindowsHookEx.restype = ctypes.c_int
        self.user.CallNextHookEx.argtypes = (
            ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_void_p
        )
        self.user.CallNextHookEx.restype = ctypes.c_ssize_t
        kernel.GetModuleHandleW.argtypes = (ctypes.c_wchar_p,)
        kernel.GetModuleHandleW.restype = ctypes.c_void_p
        self.module = kernel.GetModuleHandleW(None)
        self.keyboard_callback = callback(self.keyboard_event)
        self.mouse_callback = callback(self.mouse_event)
        self.handles = []
        self.keys = set()
        self.pause_requested = False

    def keyboard_event(self, code, message, data):
        if code != 0:
            return self.user.CallNextHookEx(None, code, message, data)
        key = ctypes.cast(data, ctypes.POINTER(ctypes.c_uint32)).contents.value
        if message in (0x100, 0x104):
            first_press = key not in self.keys
            self.keys.add(key)
            if (first_press and key == 0x7B
                    and self.keys.intersection((0x11, 0xA2, 0xA3))
                    and self.keys.intersection((0x10, 0xA0, 0xA1))):
                self.pause_requested = True
        elif message in (0x101, 0x105):
            self.keys.discard(key)
        return 1

    def mouse_event(self, code, message, data):
        if code != 0:
            return self.user.CallNextHookEx(None, code, message, data)
        return 1

    def start(self):
        self.keys.clear()
        self.pause_requested = False
        for hook_type, callback in ((13, self.keyboard_callback), (14, self.mouse_callback)):
            handle = self.user.SetWindowsHookExW(hook_type, callback, self.module, 0)
            if not handle:
                error = ctypes.get_last_error()
                self.stop()
                logging.error("Input blocking unavailable (Win32 error %s)", error)
                return False
            self.handles.append(handle)
        return True

    def stop(self):
        for handle in self.handles:
            self.user.UnhookWindowsHookEx(handle)
        self.handles.clear()
        self.keys.clear()
        self.pause_requested = False


class Guard:
    def __init__(self, app):
        self.app = app
        self.paused = False
        self.hotkey_down = False
        self.input_guard = InputGuard()
        self.input_unavailable = False
        self.overlays = []
        self.detector = Detector()
        self.protection = ScreenProtection(time.monotonic())
        self.tray = QtWidgets.QSystemTrayIcon(
            app.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon), app
        )
        self.menu = QtWidgets.QMenu()
        self.pause_action = self.menu.addAction("Pause monitoring")
        self.pause_action.setCheckable(True)
        self.pause_action.toggled.connect(self.set_paused)
        self.menu.addAction("Exit Phone Screen Guard", app.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.show()
        app.screenAdded.connect(self.rebuild_overlays)
        app.screenRemoved.connect(self.rebuild_overlays)
        self.timer = QtCore.QTimer(app)
        self.timer.timeout.connect(self.update)
        self.timer.start(25)
        app.aboutToQuit.connect(self.input_guard.stop)
        app.aboutToQuit.connect(self.detector.stop.set)
        self.detector.start()

    def set_paused(self, paused):
        self.paused = paused
        self.pause_action.setChecked(paused)

    def rebuild_overlays(self, *_):
        for overlay in self.overlays:
            overlay.hide()
            overlay.deleteLater()
        self.overlays.clear()
        self.input_guard.stop()
        self.input_unavailable = False

    def update(self):
        key_down = ctypes.windll.user32.GetAsyncKeyState
        pressed = all(key_down(key) & 0x8000 for key in (0x11, 0x10, 0x7B))
        if self.input_guard.pause_requested or (pressed and not self.hotkey_down):
            self.input_guard.pause_requested = False
            self.set_paused(not self.paused)
        self.hotkey_down = pressed

        now = time.monotonic()
        cover = self.protection.update(
            now, self.detector.camera_state, self.detector.last_phone, self.paused
        )
        if cover and not self.overlays:
            for screen in self.app.screens():
                overlay = QtWidgets.QWidget()
                overlay.setWindowFlags(
                    QtCore.Qt.WindowType.FramelessWindowHint
                    | QtCore.Qt.WindowType.WindowStaysOnTopHint
                    | QtCore.Qt.WindowType.Tool
                    | QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
                )
                overlay.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
                overlay.setStyleSheet("background-color: black;")
                overlay.setGeometry(screen.geometry())
                screen.geometryChanged.connect(overlay.setGeometry)
                overlay.show()
                self.overlays.append(overlay)
            if self.overlays:
                self.input_unavailable = not self.input_guard.start()
        elif not cover and self.overlays:
            self.rebuild_overlays()

        status = "Paused" if self.paused else self.detector.status
        if status == "Monitoring" and self.detector.model_status:
            status = self.detector.model_status
        if self.input_unavailable:
            status = "Input blocking unavailable. See guard.log."
        self.tray.setToolTip(f"Phone Screen Guard | Mode 2 | {status}")


def main():
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    lock = QtCore.QLockFile(str(BASE / "guard.lock"))
    if not lock.tryLock(0):
        return
    guard = Guard(app)
    app.exec()
    guard.detector.join(timeout=1)
    lock.unlock()


if __name__ == "__main__":
    main()
