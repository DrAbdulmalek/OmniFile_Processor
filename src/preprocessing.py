"""
HandwrittenOCR - معالجة الصور المسبقة v5.1
==============================================
تحسين الصور قبل التعرف مع تسجيل مفصّل لكل خطوة:
- تسوية الميل (Deskewing) مع borderMode=BORDER_REPLICATE
- CLAHE + Denoising + Thresholding (OTSU + Adaptive)
- تجزئة ذكية: EasyOCR أولاً + IoU matching + الكنتورات كبديل
- مُحصّن: crops من img_bgr الأصلية (ليس من الصورة الثنائية)
- detect_columns(): كشف الأعمدة في الصفحة
- column_aware_sort(): ترتيب الصناديق عمودياً داخل كل عمود
- smart_segmentation() محسّن لدعم التقسيم المتقدم
"""

import cv2
import numpy as np
import logging
import time
from typing import Tuple, Optional, List
from config import Config

logger = logging.getLogger("HandwrittenOCR")

# استيراد أدوات اللوق المفصّل
try:
    from src.logger import log_step, log_error_full, log_result
except ImportError:
    def log_step(lg, name, data=None):
        lg.info(f"STEP [{name}]")
        if data:
            for k, v in data.items():
                lg.info(f"      {k}: {v}")
    def log_error_full(lg, ctx, err, extra=None):
        lg.error(f"ERROR [{ctx}] {type(err).__name__}: {err}", exc_info=True)
    def log_result(lg, name, result):
        lg.info(f"RESULT [{name}] {result}")


def deskew(gray: np.ndarray, config: Config = None) -> np.ndarray:
    """تسوية ميل الصورة مع تسجيل مفصّل للزاوية والنتيجة."""
    coords = np.column_stack(np.where(gray < 250))
    if len(coords) < 50:
        logger.debug("deskew: نقاط قليلة جداً (<50) — يتجاوز التسوية")
        return gray

    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle

    if abs(angle) < 0.3:
        logger.debug(f"deskew: زاوية صغيرة جداً ({angle:.3f}°) — لا حاجة للتسوية")
        return gray

    h, w = gray.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    result = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    logger.info(f"deskew: زاوية={angle:.2f}°, حجم الصورة={w}x{h}")
    return result


def preprocess_image(img_bgr: np.ndarray, config: Config = None, adaptive: bool = False) -> Tuple[np.ndarray, np.ndarray]:
    """
    معالجة الصورة المسبقة مع تسجيل مفصّل لكل خطوة.

    الخطوات:
    1. تحويل لرمادي
    2. تسوية الميل (Deskewing)
    3. CLAHE (تحسين التباين)
    4. Denoising (إزالة الضوضاء)
    5. Thresholding (ثنائية)

    Returns:
        tuple: (binary, gray)
    """
    if config is None:
        config = Config()

    logger.debug(f"preprocess_image: أبعاد={img_bgr.shape[:2]}, dtype={img_bgr.dtype}, adaptive={adaptive}")

    start = time.time()

    # 1. تحويل لرمادي
    if img_bgr.ndim == 3:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        logger.debug(f"  تحويل لرمادي: {img_bgr.shape} => {gray.shape}")
    else:
        gray = img_bgr.copy()

    # 2. تسوية الميل
    if config.enable_deskew:
        gray = deskew(gray, config)
        logger.debug("  تم تسوية الميل")
    else:
        logger.debug("  تخطي تسوية الميل (enable_deskew=False)")

    # 3. CLAHE
    clahe = cv2.createCLAHE(clipLimit=config.clahe_clip, tileGridSize=config.clahe_tile)
    gray = clahe.apply(gray)
    logger.debug(f"  CLAHE: clipLimit={config.clahe_clip}, tile={config.clahe_tile}")

    # 4. Denoising
    gray = cv2.fastNlMeansDenoising(gray, h=config.denoise_h)
    logger.debug(f"  Denoising: h={config.denoise_h}")

    # 5. Thresholding
    if adaptive:
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 11)
        logger.debug("  Thresholding: Adaptive (GAUSSIAN_C, block=31, C=11)")
    else:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        logger.debug("  Thresholding: OTSU (تلقائي)")

    elapsed = time.time() - start
    logger.info(f"preprocess_image اكتمل في {elapsed:.3f}s | أبعاد الصورة={gray.shape}")
    return binary, gray


def compute_iou(b1, b2) -> float:
    """حساب IoU بين صندوقين."""
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    xi1, yi1 = max(x1, x2), max(y1, y2)
    xi2, yi2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    union = w1 * h1 + w2 * h2 - inter
    return inter / union if union > 0 else 0


def detect_columns(boxes, img_width, gap_threshold=0.15, min_column_words=3):
    """كشف الأعمدة في الصفحة مع تسجيل مفصّل."""
    if not boxes or len(boxes) < min_column_words * 2:
        logger.debug(f"detect_columns: صناديق قليلة ({len(boxes) if boxes else 0}) — عمود واحد")
        return [sorted(boxes, key=lambda b: (b[1], b[0]))]

    gap_px = img_width * gap_threshold
    box_centers = [(x + w / 2, x, y, w, h) for x, y, w, h in boxes]
    sorted_by_x = sorted(box_centers, key=lambda c: c[0])

    column_breaks = []
    for i in range(1, len(sorted_by_x)):
        prev_cx = sorted_by_x[i - 1][0]
        curr_cx = sorted_by_x[i][0]
        gap = abs(curr_cx - prev_cx)
        if gap > gap_px:
            column_breaks.append(i)
            logger.debug(f"  فاصل عمود عند الفهرس {i}: gap={gap:.0f}px > threshold={gap_px:.0f}px")

    if not column_breaks:
        logger.debug("detect_columns: لا فواصل عمود — عمود واحد")
        return [sorted(boxes, key=lambda b: (b[1], b[0]))]

    columns = []
    prev_break = 0
    for brk in column_breaks + [len(sorted_by_x)]:
        col_boxes = [(x, y, w, h) for _, x, y, w, h in sorted_by_x[prev_break:brk]]
        if col_boxes:
            col_boxes_sorted = sorted(col_boxes, key=lambda b: (b[1], b[0]))
            if len(col_boxes_sorted) >= min_column_words:
                columns.append(col_boxes_sorted)
            else:
                if columns:
                    columns[-1].extend(col_boxes_sorted)
                    columns[-1].sort(key=lambda b: (b[1], b[0]))
                else:
                    columns.append(col_boxes_sorted)
        prev_break = brk

    logger.info(f"detect_columns: {len(columns)} عمود (من {len(boxes)} صندوق)")
    for i, col in enumerate(columns):
        logger.debug(f"  عمود {i}: {len(col)} كلمة, x_range=[{col[0][0]}, {col[-1][0] + col[-1][2]}]")

    return columns if columns else [sorted(boxes, key=lambda b: (b[1], b[0]))]


def column_aware_sort(boxes, img_width, lang="en"):
    """ترتيب الصناديق مع مراعاة الأعمدة والاتجاه."""
    if not boxes:
        return []

    columns = detect_columns(boxes, img_width)
    if len(columns) == 1:
        return columns[0]

    # ترتيب الأعمدة حسب اللغة
    if lang == "ar":
        columns.sort(key=lambda col: -col[0][0])  # RTL
        logger.debug("column_aware_sort: ترتيب RTL (عربي)")
    else:
        columns.sort(key=lambda col: col[0][0])  # LTR
        logger.debug("column_aware_sort: ترتيب LTR")

    result = []
    for col in columns:
        result.extend(col)
    return result


def smart_segmentation(img_bgr, binary, easyocr_detections=None, config=None):
    """
    تجزئة ذكية للنص مع تسجيل مفصّل.
    يفضل EasyOCR detections أولاً، ثم يلجأ للكنتورات.
    """
    if config is None:
        config = Config()

    log_step(logger, "smart_segmentation", {
        "img_size": f"{img_bgr.shape[:2]}",
        "detections_provided": str(easyocr_detections is not None),
        "num_detections": str(len(easyocr_detections) if easyocr_detections else 0),
        "min_word_w": config.min_word_w,
        "min_word_h": config.min_word_h,
    })

    # === الطريقة 1: EasyOCR detections ===
    if easyocr_detections:
        boxes = []
        skipped = 0
        for det in easyocr_detections:
            pts = np.array(det[0], dtype=np.int32)
            x, y, w, h = cv2.boundingRect(pts)
            if w > config.min_word_w and h > config.min_word_h:
                boxes.append((x, y, w, h))
            else:
                skipped += 1

        logger.info(f"  EasyOCR boxes: {len(boxes)} صالح, {skipped} متجاوز (صغير)")

        if boxes:
            sorted_boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
            logger.debug(f"  smart_segmentation => {len(sorted_boxes)} صندوق من EasyOCR")
            return sorted_boxes

        logger.info("  لم ينتج عن EasyOCR صناديق صالحة — الانتقال للكنتورات")

    # === الطريقة 2: الكنتورات ===
    logger.debug("  استخدام طريقة الكنتورات")
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, config.dilation_kernel)
    dilated = cv2.dilate(binary, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = [
        (x, y, w, h) for c in contours
        for x, y, w, h in [cv2.boundingRect(c)]
        if w > config.min_word_w and h > config.min_word_h
    ]

    sorted_boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    logger.info(f"  الكنتورات: {len(contours)} كانتور => {len(boxes)} صندوق صالح")
    return sorted_boxes


def match_boxes_with_detections(boxes, detections, iou_threshold=0.3):
    """مطابقة الصناديق مع detections EasyOCR باستخدام IoU مع تسجيل مفصّل."""
    if not detections:
        logger.debug(f"match_boxes: لا detections — {len(boxes)} صندوق بدون مطابقة")
        return [(b, None) for b in boxes]

    det_boxes = []
    for det in detections:
        pts = np.array(det[0], dtype=np.int32)
        det_boxes.append((cv2.boundingRect(pts), det))

    result, used = [], set()
    matched_count = 0
    unmatched = 0

    for i, box in enumerate(boxes):
        best_det, best_iou = None, 0
        for j, (db, det) in enumerate(det_boxes):
            if j in used:
                continue
            iou = compute_iou(box, db)
            if iou > best_iou and iou > iou_threshold:
                best_iou, best_det = iou, det
                used.add(j)
        if best_det:
            matched_count += 1
        else:
            unmatched += 1
        result.append((box, best_det))

    logger.info(f"match_boxes: {matched_count} مطابق, {unmatched} غير مطابق (IoU>{iou_threshold})")
    return result


def crop_safe(img, x, y, w, h):
    """قص آمن مع تسجيل الحالات الشاذة."""
    H, W = img.shape[:2]
    crop = img[max(0, y): min(H, y + h), max(0, x): min(W, x + w)]

    if crop.size == 0:
        logger.warning(f"crop_safe: صورة فارغة! img={img.shape[:2]}, box=({x},{y},{w},{h})")
    elif crop.shape[0] < 3 or crop.shape[1] < 3:
        logger.debug(f"crop_safe: صندوق صغير جداً: {crop.shape[:2]}")

    return crop
