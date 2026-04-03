from features.raw_processing import load_raw_image
from features.perspective import detect_document, warp
import cv2 as cv
import os

# ---------- LOAD ----------
img = load_raw_image("IMG_9095.CR3")

# ---------- DETECT ----------
pts = detect_document(img)

# ---------- WARP ----------
warped = warp(img, pts)

# ---------- SHOW ----------
cv.imwrite("preview.png", warped)

os.system("kitty +kitten icat --clear")
os.system("kitty +kitten icat preview.png")
