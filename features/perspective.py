import cv2
import numpy as np
 
 
# ---------- ORDER POINTS ----------
def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]     # top-left
    rect[2] = pts[np.argmax(s)]     # bottom-right
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left
    return rect
 
 
# ---------- SCORE A QUAD ----------
def score_quad(pts, img_w, img_h):
    """
    Score a candidate quad. Higher = more photo-like, less mat-like.
    Criteria:
      - Reasonable area (not too small, not the whole image)
      - Aspect ratio close to common photo formats
      - Roughly centred (mats tend to fill the frame edge-to-edge)
    """
    area = cv2.contourArea(pts.astype("float32"))
    img_area = img_w * img_h
 
    area_ratio = area / img_area
 
    # Penalise quads that are basically the whole frame (likely the mat)
    if area_ratio > 0.90:
        return -1.0
 
    # Must be at least 5% of the frame
    if area_ratio < 0.05:
        return -1.0
 
    # Compute width/height of the bounding box for aspect ratio check
    rect = order_points(pts)
    tl, tr, br, bl = rect
    w = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    h = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
    if h == 0:
        return -1.0
    aspect = max(w, h) / min(w, h)
 
    # Common photo aspect ratios: 3:2 (1.5), 4:3 (1.33), 5:4 (1.25), 1:1, 7:5 (1.4)
    common_aspects = [1.0, 1.25, 1.33, 1.4, 1.5, 1.6, 1.78]
    aspect_score = min(abs(aspect - a) for a in common_aspects)
 
    # Prefer mid-range area (sweet spot around 30-70% of image)
    area_score = abs(area_ratio - 0.50)
 
    # Combined: lower raw penalty → higher final score
    penalty = aspect_score * 0.5 + area_score * 0.5
    return 1.0 - penalty
 
 
# ---------- CANDIDATE: OTSU CONTOUR ----------
def candidate_otsu(gray, img_w, img_h):
    """
    Otsu threshold → find the largest contour that isn't the whole frame.
    Works well when the photo has a clearly different tone from the mat.
    """
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
 
    # Try both polarities — photo might be lighter or darker than mat
    candidates = []
    for t in [thresh, cv2.bitwise_not(thresh)]:
        contours, _ = cv2.findContours(t, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
 
        for c in contours[:3]:  # check top-3 largest
            area = cv2.contourArea(c)
            if area < img_w * img_h * 0.05:
                continue
 
            hull = cv2.convexHull(c)
            epsilon = 0.02 * cv2.arcLength(hull, True)
            approx = cv2.approxPolyDP(hull, epsilon, True)
 
            if len(approx) == 4:
                pts = approx.reshape(4, 2).astype("float32")
            else:
                rect = cv2.minAreaRect(hull)
                pts = cv2.boxPoints(rect).astype("float32")
 
            score = score_quad(pts, img_w, img_h)
            if score > 0:
                candidates.append((score, pts))
 
    if not candidates:
        raise ValueError("Otsu: no valid quad found")
 
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]
 
 
# ---------- CANDIDATE: EDGE CONTOUR ----------
def candidate_edge_contour(gray, img_w, img_h):
    """
    Canny edges → contours. Better when tonal difference is small but
    the photo border creates a clear edge (e.g. white border on mat).
    """
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 30, 100)
 
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=2)
 
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
 
    candidates = []
    for c in contours[:5]:
        area = cv2.contourArea(c)
        if area < img_w * img_h * 0.05:
            continue
 
        hull = cv2.convexHull(c)
        epsilon = 0.02 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon, True)
 
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype("float32")
        else:
            rect = cv2.minAreaRect(hull)
            pts = cv2.boxPoints(rect).astype("float32")
 
        score = score_quad(pts, img_w, img_h)
        if score > 0:
            candidates.append((score, pts))
 
    if not candidates:
        raise ValueError("Edge contour: no valid quad found")
 
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]
 
 
# ---------- CANDIDATE: LAB COLOR SEGMENTATION ----------
def candidate_lab_color(image, img_w, img_h):
    """
    Segment in LAB colour space. Most effective when the mat has a
    noticeably different colour from the photo (green mat, red mat, etc.).
    Uses k-means (k=2) to split the image into two regions.
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    pixels = lab.reshape(-1, 3).astype("float32")
 
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, _ = cv2.kmeans(pixels, 2, None, criteria, 3, cv2.KMEANS_RANDOM_CENTERS)
 
    mask = labels.reshape(img_h, img_w).astype("uint8")
 
    candidates = []
    for val in [0, 1]:
        m = np.where(mask == val, 255, 0).astype("uint8")
        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
 
        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < img_w * img_h * 0.05:
            continue
 
        hull = cv2.convexHull(c)
        epsilon = 0.02 * cv2.arcLength(hull, True)
        approx = cv2.approxPolyDP(hull, epsilon, True)
 
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype("float32")
        else:
            rect = cv2.minAreaRect(hull)
            pts = cv2.boxPoints(rect).astype("float32")
 
        score = score_quad(pts, img_w, img_h)
        if score > 0:
            candidates.append((score, pts))
 
    if not candidates:
        raise ValueError("LAB colour: no valid quad found")
 
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]
 
 
# ---------- DETECT DOCUMENT ----------
def detect_document(image):
    """
    Run all three detectors, score every candidate, return the best quad.
    Falls back gracefully if individual methods fail.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
 
    all_candidates = []  # list of (score, pts, method_name)
 
    for name, fn, args in [
        ("otsu",      candidate_otsu,          (gray, w, h)),
        ("edge",      candidate_edge_contour,   (gray, w, h)),
        ("lab_color", candidate_lab_color,      (image, w, h)),
    ]:
        try:
            pts = fn(*args)
            score = score_quad(pts, w, h)
            print(f"[detect] {name}: score={score:.3f}")
            all_candidates.append((score, pts, name))
        except Exception as e:
            print(f"[detect] {name} failed: {e}")
 
    if not all_candidates:
        raise ValueError("All detection methods failed")
 
    all_candidates.sort(key=lambda x: x[0], reverse=True)
    best_score, best_pts, best_name = all_candidates[0]
    print(f"[detect] Winner: {best_name} (score={best_score:.3f})")
    return best_pts
 
 
 
 
# ---------- WARP ----------
def warp(image, pts):
    rect = order_points(pts)
    tl, tr, br, bl = rect
 
    widthA  = np.linalg.norm(br - bl)
    widthB  = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))
 
    heightA  = np.linalg.norm(tr - br)
    heightB  = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))
 
    if maxWidth < 50 or maxHeight < 50:
        raise ValueError("Bad transform (collapsed quad)")
 
    dst = np.array([
        [0,            0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0,            maxHeight - 1],
    ], dtype="float32")
 
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped
 
 
# ---------- MAIN PIPELINE ----------
def scan_photo(image, enhance=True):
    """
    Full pipeline:
      1. Detect the photo boundary (ignoring mat/background)
      2. Perspective-correct it
 
    Returns the corrected (and optionally enhanced) photo crop.
    """
    pts    = detect_document(image)
    warped = warp(image, pts)
 
   
    return warped

