from features.raw_processing import load_raw_image
from features.perspective import detect_document, warp

import os
import sys
import cv2 as cv

from PySide6.QtWidgets import QApplication, QListWidgetItem, QLabel, QListWidget
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
show_processed = False


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

assert image_label is not None, "image_label not found!"
assert list_widget is not None, "list_widget not found!"

image_label.setAlignment(Qt.AlignCenter)
image_label.setScaledContents(False)


# ---------- INSERT FILES ----------
base_path = os.path.abspath(".")

for file in get_photos(base_path):
    full_path = os.path.join(base_path, file)

    item = QListWidgetItem(file)
    item.setData(256, full_path)
    list_widget.addItem(item)


# ---------- SCALE + DISPLAY ----------
def update_image():
    if not current_pixmap:
        return

    scaled = current_pixmap.scaled(
        image_label.size(),
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation
    )

    image_label.setPixmap(scaled)


# ---------- ON SELECT ----------
def on_item_changed(current, previous):
    global current_pixmap

    if not current:
        return

    path = current.data(256)

    img = load_raw_image(path)

    if show_processed:
        print("Showing PROCESSED")
        
        # Auto Perspective Transformation
        pts = detect_document(img)
        img = warp(img, pts)
    else:
        print("Showing ORIGINAL")

    current_pixmap = numpy_to_qpixmap(img)
    update_image()


# ---------- ENTER KEY ----------
def on_enter_pressed():
    global show_processed

    show_processed = not show_processed
    print("ENTER pressed -> processed =", show_processed)

    current = list_widget.currentItem()
    if current:
        on_item_changed(current, None)


shortcut = QShortcut(QKeySequence("Return"), window)
shortcut.activated.connect(on_enter_pressed)


# ---------- CONNECT ----------
list_widget.currentItemChanged.connect(on_item_changed)


# ---------- AUTO SELECT FIRST ----------
def select_first_item():
    if list_widget.count() > 0:
        list_widget.setCurrentRow(0)

QTimer.singleShot(0, select_first_item)


# ---------- HANDLE RESIZE ----------
def resizeEvent(event):
    update_image()
    return super(type(window), window).resizeEvent(event)

window.resizeEvent = resizeEvent


# ---------- RUN ----------
window.show()
app.exec()
