from features.raw_processing import load_raw_image
from features.perspective import detect_document, warp
from features.rotate import rotate
from features.color import apply_color_pipeline

import os
import sys
import cv2 as cv
import json

from PySide6.QtWidgets import (
    QApplication, QListWidgetItem, QLabel, QListWidget, QSlider ,QComboBox, QSpinBox, QLineEdit, QCheckBox
)
from PySide6.QtCore import QFile, Qt, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QImage, QPixmap, QShortcut, QKeySequence


# ---------- SETTINGS FILE ----------
def get_settings_path(image_path):
    return image_path + ".json"


def save_settings(image_path):
    data = {
        "rotation": rotation_steps,
        "perspective": perspective_enabled,
        "color_enabled": color_enabled,
        "color_settings": color_settings,

        "classification": {
            "photo_id": photo_spin.value(),
            "side": side_combo.currentText().lower(),
            "needs_manual": manual_check.isChecked()
        }
    }

    with open(get_settings_path(image_path), "w") as f:
        json.dump(data, f, indent=4)

    print("Saving JSON to:", get_settings_path(image_path))

# ________ AUTO SAVE WHEN CHANGED _________
def on_classification_changed():
    current = list_widget.currentItem()
    if current:
        save_settings(current.data(256))
        update_status()
        update_photo_list()
        populate_raw_list()


def load_settings(image_path):
    global rotation_steps, perspective_enabled, color_enabled

    path = get_settings_path(image_path)

    if not os.path.exists(path):
        return

    with open(path, "r") as f:
        data = json.load(f)

    rotation_steps = data.get("rotation", 0)
    perspective_enabled = data.get("perspective", False)
    color_enabled = data.get("color_enabled", False)

    color_settings.update(data.get("color_settings", {}))

    
# __________ STATUS MAP ____________
def build_photo_map(folder_path):
    photos = {}

    for file in os.listdir(folder_path):
        if not file.lower().endswith(".cr3"):
            continue

        full_path = os.path.join(folder_path, file)
        json_path = full_path + ".json"

        if not os.path.exists(json_path):
            continue

        with open(json_path, "r") as f:
            data = json.load(f)

        cls = data.get("classification", {})

        pid = cls.get("photo_id")
        side = cls.get("side", "").lower()
        needs_manual = cls.get("needs_manual", False)

        # ---------- SAFETY CHECK ----------
        if pid is None or side not in ("front", "back"):
            continue

        pid = int(pid)

        # ---------- INIT ----------
        if pid not in photos:
            photos[pid] = {
                "front": None,
                "back": None,
                "needs_manual": False
            }

        # ---------- ASSIGN SIDE ----------
        photos[pid][side] = full_path

        # ---------- MERGE MANUAL FLAG ----------
        # if ANY image in this photo needs manual → whole photo needs manual
        photos[pid]["needs_manual"] = (
            photos[pid]["needs_manual"] or needs_manual
        )

        print("Loaded JSON:", pid, side, "| manual:", needs_manual)

    return photos

def get_next_photo_id(photos):
    if not photos:
        return 1

    return max(photos.keys()) + 1


def get_photo_status(photo):
    if photo["front"] and photo["back"]:
        return "complete"
    elif photo["front"] or photo["back"]:
        return "partial"
    else:
        return "empty"


def update_status():
    if current_image_path is None:
        status_label.setText("No image selected")
        return

    current_dir = os.path.dirname(current_image_path)
    photos = build_photo_map(current_dir)

    current_pid = photo_spin.value()

    # include needs_manual in default
    photo = photos.get(current_pid, {
        "front": None,
        "back": None,
        "needs_manual": False
    })

    front_done = photo["front"] is not None
    back_done = photo["back"] is not None
    needs_manual = photo.get("needs_manual", False)

    # ---------- PRIORITY LOGIC ----------
    if needs_manual:
        status = "NEEDS MANUAL"
    elif front_done and back_done:
        status = "COMPLETE"
    elif front_done or back_done:
        status = "PARTIAL"
    else:
        status = "EMPTY"

    # ---------- UI ----------
    status_label.setText(
        f"Photo {current_pid:03d} → {status}\n"
        f"Front: {'✔' if front_done else '✘'} | "
        f"Back: {'✔' if back_done else '✘'}\n"
        f"Manual: {'⚠' if needs_manual else '✔'}\n"
        f"Next: {get_next_photo_id(photos):03d}"
    )

    # ---------- DEBUG ----------
    print("current_image_path:", current_image_path)
    print("current_dir:", current_dir)
    print("photos map:", photos)
    print("current_pid:", current_pid)


def get_image_classification(image_path):
    json_path = image_path + ".json"

    if not os.path.exists(json_path):
        return None

    with open(json_path, "r") as f:
        data = json.load(f)

    cls = data.get("classification")
    if not cls:
        return None

    return {
        "photo_id": cls.get("photo_id"),
        "side": cls.get("side"),
        "needs_manual": cls.get("needs_manual", False)
    }



def set_ui_without_signals():
    side_combo.blockSignals(True)
    photo_spin.blockSignals(True)
    manual_check.blockSignals(True)

def restore_ui_signals():
    side_combo.blockSignals(False)
    photo_spin.blockSignals(False)
    manual_check.blockSignals(False)


def update_photo_list():
    if current_image_path is None:
        return

    current_dir = os.path.dirname(current_image_path)
    photos = build_photo_map(current_dir)

    photo_list.clear()

    max_id = get_next_photo_id(photos)

    for pid in range(1, max_id + 1):
        photo = photos.get(pid, {
            "front": None,
            "back": None,
            "needs_manual": False
        })

        front = photo["front"] is not None
        back = photo["back"] is not None
        needs_manual = photo.get("needs_manual", False)

        # ---------- SAME PRIORITY LOGIC ----------
        if needs_manual:
            status = "NEEDS MANUAL"
        elif front and back:
            status = "COMPLETE"
        elif front or back:
            status = "PARTIAL"
        else:
            status = "EMPTY"

        # ---------- TEXT ----------
        text = (
            f"{pid:03d} | "
            f"F:{'✔' if front else '✘'} "
            f"B:{'✔' if back else '✘'} | "
            f"{status}"
        )

        item = QListWidgetItem(text)

        # ---------- COLORS ----------
        if needs_manual:
            item.setForeground(Qt.red)
        elif front and back:
            item.setForeground(Qt.green)
        elif front or back:
            item.setForeground(Qt.yellow)
        else:
            item.setForeground(Qt.gray)

        photo_list.addItem(item)
# ---------- GET PHOTOS ----------
def get_photos(path):
    files = [x for x in os.listdir(path) if x.lower().endswith(".cr3")]
    return sorted(files)

# ---------- NUMPY to QPIXMAP ----------
def numpy_to_qpixmap(img):
    img = cv.cvtColor(img, cv.COLOR_BGR2RGB)

    height, width, channel = img.shape
    bytes_per_line = 3 * width

    q_image = QImage(
        img.data,
        width,
        height,
        bytes_per_line,
        QImage.Format_RGB888
    )

    return QPixmap.fromImage(q_image)


# ---------- GLOBAL ----------
current_pixmap = None
current_base_image = None

rotation_steps = 0
perspective_enabled = False
color_enabled = False

color_settings = {
    "color_fix": 0.5,
    "warmth": 0,
    "tint": 0,
    "contrast": 0.5,
    "exposure": 0
}

current_image_path = None

# ---------- APP ----------
app = QApplication(sys.argv)
loader = QUiLoader()

file = QFile('phote.ui')
file.open(QFile.ReadOnly)

window = loader.load(file)
file.close()


# ---------- FIND WIDGETS ----------
list_widget = window.findChild(QListWidget, "listWidget")
image_label = window.findChild(QLabel, "preview")

exposure_slider = window.findChild(QSlider, "exposureSlider")
warmth_slider = window.findChild(QSlider, "warmthSlider")
contrast_slider = window.findChild(QSlider, "contrastSlider")
colorfix_slider = window.findChild(QSlider, "colorFixSlider")

image_label.setAlignment(Qt.AlignCenter)
image_label.setScaledContents(False)

side_combo = window.findChild(QComboBox, "sideCombo")
photo_spin = window.findChild(QSpinBox, "photoSpin")
manual_check = window.findChild(QCheckBox, "manualCheck")

status_label = window.findChild(QLabel, "statusLabel")
photo_list = window.findChild(QListWidget, "photoList")

# ---------- INITIAL UI ----------
exposure_slider.setValue(0)
warmth_slider.setValue(0)
contrast_slider.setValue(50)
colorfix_slider.setValue(50)


# ---------- INSERT FILES ----------
def populate_raw_list():
    list_widget.clear()

    files = get_photos(base_path)
    total = len(files)

    for index, file in enumerate(files):
        full_path = os.path.join(base_path, file)

        cls = get_image_classification(full_path)

        # ---------- BASE LABEL ----------
        label = f"[{index+1}/{total}] {file}"

        # ---------- CLASSIFICATION ----------
        if cls:
            pid = cls["photo_id"]
            side = cls["side"]
            manual = cls.get("needs_manual", False)

            label += f" → [{pid:03d} {side.upper()}]"

            if manual:
                label += " ⚠"
        else:
            label += " → [UNASSIGNED]"

        item = QListWidgetItem(label)
        item.setData(256, full_path)

        # ---------- COLOR ----------
        if not cls:
            item.setForeground(Qt.gray)
        elif cls.get("needs_manual"):
            item.setForeground(Qt.red)
        else:
            item.setForeground(Qt.green)

        list_widget.addItem(item)

base_path = os.path.abspath(".")
populate_raw_list()

# ---------- DISPLAY ----------
def update_image():
    if not current_pixmap:
        return

    scaled = current_pixmap.scaled(
        image_label.size(),
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )

    image_label.setPixmap(scaled)


# ---------- PROCESS ----------
def process_and_display():
    global current_pixmap

    if current_base_image is None:
        return

    img = current_base_image.copy()

    # Downscale preview
    h, w = img.shape[:2]
    scale = 1000 / max(h, w)
    if scale < 1:
        img = cv.resize(img, (int(w * scale), int(h * scale)))

    # Perspective
    if perspective_enabled:
        try:
            pts = detect_document(img)
            img = warp(img, pts)
        except Exception as e:
            print("Perspective failed:", e)

    # Rotation
    for _ in range(rotation_steps % 4):
        img = rotate(img)

    # Color
    if color_enabled:
        img = apply_color_pipeline(
            img,
            color_fix=color_settings["color_fix"],
            warmth=color_settings["warmth"],
            tint=color_settings["tint"],
            contrast=color_settings["contrast"],
            exposure=color_settings["exposure"]
        )

    current_pixmap = numpy_to_qpixmap(img)
    update_image()


# ---------- PROCESS + SAVE ----------
def process_and_display_and_save():
    process_and_display()

    current = list_widget.currentItem()
    if current:
        save_settings(current.data(256))


# ---------- LOAD IMAGE ----------
def on_item_changed(current, previous):
    global current_base_image, current_image_path

    if not current:
        return

    path = current.data(256)
    current_image_path = path

    print("Loading:", path)

    current_base_image = load_raw_image(path)

    # load saved settings (this updates color_settings + classification internally)
    load_settings(path)

    # ---------- BLOCK SIGNALS ----------
    side_combo.blockSignals(True)
    photo_spin.blockSignals(True)
    manual_check.blockSignals(True)

    exposure_slider.blockSignals(True)
    warmth_slider.blockSignals(True)
    contrast_slider.blockSignals(True)
    colorfix_slider.blockSignals(True)

    # ---------- SYNC UI (COLOR) ----------
    exposure_slider.setValue(int(color_settings["exposure"] * 10))
    warmth_slider.setValue(int(color_settings["warmth"]))
    contrast_slider.setValue(int(color_settings["contrast"] * 100))
    colorfix_slider.setValue(int(color_settings["color_fix"] * 100))

    # ---------- SYNC UI (CLASSIFICATION) ----------
    json_path = path + ".json"

    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            data = json.load(f)

        cls = data.get("classification", {})

        photo_spin.setValue(int(cls.get("photo_id", 1)))

        # IMPORTANT: UI uses "Front"/"Back", JSON uses lowercase
        side = cls.get("side", "front").capitalize()
        side_combo.setCurrentText(side)

        manual_check.setChecked(cls.get("needs_manual", False))
    else:
        # default state
        photo_spin.setValue(1)
        side_combo.setCurrentText("Front")
        manual_check.setChecked(False)

    # ---------- RESTORE SIGNALS ----------
    side_combo.blockSignals(False)
    photo_spin.blockSignals(False)
    manual_check.blockSignals(False)

    exposure_slider.blockSignals(False)
    warmth_slider.blockSignals(False)
    contrast_slider.blockSignals(False)
    colorfix_slider.blockSignals(False)

    # ---------- DISPLAY ----------
    process_and_display()

    # ---------- STATUS ----------
    update_status()   
    update_photo_list()


# ---------- SHORTCUTS ----------
def on_enter_pressed():
    global perspective_enabled
    perspective_enabled = not perspective_enabled
    print("Perspective =", perspective_enabled)
    process_and_display_and_save()


def on_r_pressed():
    global rotation_steps
    rotation_steps += 1
    print("Rotation =", (rotation_steps % 4) * 90)
    process_and_display_and_save()


def on_c_pressed():
    global color_enabled
    color_enabled = not color_enabled
    print("Color =", color_enabled)
    process_and_display_and_save()


# ---------- SLIDERS ----------
def on_exposure_changed(value):
    if not color_enabled:
        return
    color_settings["exposure"] = value / 10.0
    update_timer.start(30)


def on_warmth_changed(value):
    if not color_enabled:
        return
    color_settings["warmth"] = value
    update_timer.start(30)


def on_contrast_changed(value):
    if not color_enabled:
        return
    color_settings["contrast"] = value / 100.0
    update_timer.start(30)


def on_colorfix_changed(value):
    if not color_enabled:
        return
    color_settings["color_fix"] = value / 100.0
    update_timer.start(30)


# ---------- TIMER ----------
update_timer = QTimer()
update_timer.setSingleShot(True)
update_timer.timeout.connect(process_and_display_and_save)


# ---------- CONNECT ----------
list_widget.currentItemChanged.connect(on_item_changed)

exposure_slider.valueChanged.connect(on_exposure_changed)
warmth_slider.valueChanged.connect(on_warmth_changed)
contrast_slider.valueChanged.connect(on_contrast_changed)
colorfix_slider.valueChanged.connect(on_colorfix_changed)

side_combo.currentTextChanged.connect(on_classification_changed)
photo_spin.valueChanged.connect(on_classification_changed)
manual_check.stateChanged.connect(on_classification_changed)

# ---------- SHORTCUTS ----------
shortcut = QShortcut(QKeySequence("Return"), window)
shortcut.setContext(Qt.ApplicationShortcut)
shortcut.activated.connect(on_enter_pressed)

shortcut_r = QShortcut(QKeySequence("R"), window)
shortcut_r.setContext(Qt.ApplicationShortcut)
shortcut_r.activated.connect(on_r_pressed)

shortcut_c = QShortcut(QKeySequence("C"), window)
shortcut_c.setContext(Qt.ApplicationShortcut)
shortcut_c.activated.connect(on_c_pressed)


# ---------- AUTO SELECT ----------
def select_first_item():
    if list_widget.count() > 0:
        list_widget.setCurrentRow(0)

QTimer.singleShot(0, select_first_item)


# ---------- RESIZE ----------
def resizeEvent(event):
    update_image()
    return super(type(window), window).resizeEvent(event)

window.resizeEvent = resizeEvent


# ---------- RUN ----------
window.show()
app.exec()
