from features.raw_processing import load_raw_image
from features.perspective import detect_document, warp
from features.rotate import rotate
from features.color import apply_color_pipeline

import os
import sys
import cv2 as cv

from PySide6.QtWidgets import (
    QApplication, QListWidgetItem, QLabel, QListWidget,
    QSlider, QCheckBox
)
from PySide6.QtCore import QFile, Qt, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QImage, QPixmap, QShortcut, QKeySequence


# ---------- GET PHOTOS ----------
def get_photos(path):
    return [x for x in os.listdir(path) if x.lower().endswith(".cr3")]


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
    "color_fix": 0.8,
    "warmth": -8,
    "tint": 0,
    "contrast": False,
    "exposure": 0
}


# ---------- APP ----------
app = QApplication(sys.argv)
loader = QUiLoader()

file = QFile('phote.ui')
file.open(QFile.ReadOnly)

window = loader.load(file)
file.close()


# ---------- FIND WIDGETS ----------
list_widget = window.findChild(QListWidget, "listWidget")
image_label = window.findChild(QLabel, "label_2")

exposure_slider = window.findChild(QSlider, "exposureSlider")
warmth_slider = window.findChild(QSlider, "warmthSlider")
contrast_checkbox = window.findChild(QCheckBox, "contrastCheckbox")

assert image_label is not None
assert list_widget is not None

image_label.setAlignment(Qt.AlignCenter)
image_label.setScaledContents(False)


# ---------- INSERT FILES ----------
base_path = os.path.abspath(".")

for file in get_photos(base_path):
    full_path = os.path.join(base_path, file)

    item = QListWidgetItem(file)
    item.setData(256, full_path)
    list_widget.addItem(item)


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


# ---------- PROCESS PIPELINE ----------
def process_and_display():
    global current_pixmap

    if current_base_image is None:
        return

    img = current_base_image.copy()

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


# ---------- LOAD IMAGE ----------
def on_item_changed(current, previous):
    global current_base_image

    if not current:
        return

    path = current.data(256)

    print("Loading:", path)

    # LOAD ONLY ONCE
    current_base_image = load_raw_image(path)

    process_and_display()


# ---------- SHORTCUTS ----------
def on_enter_pressed():
    global perspective_enabled
    perspective_enabled = not perspective_enabled
    print("Perspective =", perspective_enabled)
    process_and_display()


def on_r_pressed():
    global rotation_steps
    rotation_steps += 1
    print("Rotation =", (rotation_steps % 4) * 90, "degrees")
    process_and_display()


def on_c_pressed():
    global color_enabled
    color_enabled = not color_enabled
    print("Color =", color_enabled)
    process_and_display()


# ---------- SLIDERS ----------
def on_exposure_changed(value):
    color_settings["exposure"] = value / 10.0
    update_timer.start(30)


def on_warmth_changed(value):
    color_settings["warmth"] = value
    update_timer.start(30)


def on_contrast_changed(state):
    color_settings["contrast"] = bool(state)
    process_and_display()


# ---------- DEBOUNCE TIMER ----------
update_timer = QTimer()
update_timer.setSingleShot(True)
update_timer.timeout.connect(process_and_display)


# ---------- CONNECT ----------
list_widget.currentItemChanged.connect(on_item_changed)

exposure_slider.valueChanged.connect(on_exposure_changed)
warmth_slider.valueChanged.connect(on_warmth_changed)
contrast_checkbox.stateChanged.connect(on_contrast_changed)


# ---------- SHORTCUT SETUP ----------
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
