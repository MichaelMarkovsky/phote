import cv2
import numpy as np


def auto_color_calibration(img, strength=0.5):
    img = img.astype(np.float32)

    b, g, r = cv2.split(img)

    med_b = np.median(b)
    med_g = np.median(g)
    med_r = np.median(r)

    target = (med_b + med_g + med_r) / 3.0

    b_corr = b * (target / (med_b + 1e-6))
    g_corr = g * (target / (med_g + 1e-6))
    r_corr = r * (target / (med_r + 1e-6))

    b = b * (1 - strength) + b_corr * strength
    g = g * (1 - strength) + g_corr * strength
    r = r * (1 - strength) + r_corr * strength

    return np.clip(cv2.merge([b, g, r]), 0, 255).astype(np.uint8)


def adjust_temperature(img, temp=0):
    img = img.astype(np.float32)
    b, g, r = cv2.split(img)

    r += temp * 0.5
    b -= temp * 0.5

    return np.clip(cv2.merge([b, g, r]), 0, 255).astype(np.uint8)


def adjust_tint(img, tint=0):
    img = img.astype(np.float32)
    b, g, r = cv2.split(img)

    g -= tint

    return np.clip(cv2.merge([b, g, r]), 0, 255).astype(np.uint8)


def enhance_contrast(img, strength=1.0):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l_clahe = clahe.apply(l)

    # blend original + enhanced
    l = l * (1 - strength) + l_clahe * strength

    lab = cv2.merge((l.astype("uint8"), a, b))
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

def adjust_exposure(img, exposure=0):
    img = img.astype(np.float32)
    factor = 2 ** exposure
    img *= factor
    return np.clip(img, 0, 255).astype(np.uint8)


# ---------- MAIN PIPELINE ----------
def apply_color_pipeline(
    img,
    color_fix=0.4,
    warmth=0,
    tint=0,
    contrast=True,
    exposure=0
):
    img = auto_color_calibration(img, strength=color_fix)
    img = adjust_temperature(img, temp=warmth)
    img = adjust_tint(img, tint=tint)

    if contrast > 0:
        img = enhance_contrast(img, strength=contrast)

    img = adjust_exposure(img, exposure=exposure)

    return img

