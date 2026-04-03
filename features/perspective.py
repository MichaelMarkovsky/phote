import cv2
import numpy as np


# ---------- ORDER POINTS ----------
def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left
    rect[2] = pts[np.argmax(s)]  # bottom-right

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left

    return rect


# ---------- DETECT DOCUMENT ----------
def detect_document(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    contours, _ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    # remove noise
    contours = [c for c in contours if cv2.contourArea(c) > 1000]

    if not contours:
        raise ValueError("No contours found")

    largest = max(contours, key=cv2.contourArea)

    # fix broken shapes
    largest = cv2.convexHull(largest)

    epsilon = 0.02 * cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, epsilon, True)

    # fallback if not 4 points
    if len(approx) != 4:
        rect = cv2.minAreaRect(largest)
        approx = cv2.boxPoints(rect)
        approx = np.int32(approx)
    else:
        approx = approx.reshape(4, 2)

    return approx.astype("float32")


# ---------- WARP ----------
def warp(image, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))

    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))

    if maxWidth < 50 or maxHeight < 50:
        raise ValueError("Bad transform (collapsed)")

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    return warped
