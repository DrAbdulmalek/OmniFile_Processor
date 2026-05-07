"""
مستخرج النصوص من الفيديو — Video OCR Module
================================================
استخراج النصوص من إطارات الفيديو مع طوابع زمنية باستخدام OpenCV + OCR.

القدرات:
- استخراج إطارات بمعدّل قابل للتهيئة (الافتراضي: كل 30 إطار ≈ 1 ثانية عند 30fps)
- معالجة ملفات الفيديو (mp4, avi, mov, mkv, webm)
- بث مباشر من الكاميرا
- نتائج مؤقتة (timestamped text) مع الثقة
- دعم رد الاتصال (callback) لتتبع التقدم
- تكامل كسول (lazy) مع محرك OCR الموجود

مثال الاستخدام:
    >>> video_ocr = VideoOCR(frame_interval=30)
    >>> # معالجة ملف فيديو
    >>> results = video_ocr.process_video("lecture.mp4")
    >>> for r in results:
    ...     print(f"[{r['timestamp']}] {r['text']} (conf: {r['confidence']:.0%})")
    >>> # بث مباشر من الكاميرا
    >>> video_ocr.process_camera(camera_id=0, duration=10)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Union

logger = logging.getLogger(__name__)

# صيغ الفيديو المدعومة
SUPPORTED_VIDEO_EXTENSIONS: set[str] = {
    ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v", ".mpg", ".mpeg",
}


# ======================================================================
# هياكل البيانات
# ======================================================================

@dataclass
class FrameResult:
    """نتيجة OCR لإطار فيديو واحد.

    Attributes:
        frame_number: رقم الإطار في الفيديو.
        timestamp: الطابع الزمني بالثواني (من بداية الفيديو).
        timestamp_formatted: الطابع الزمني بتنسيق MM:SS.
        text: النص المستخرج.
        confidence: مستوى الثقة (0.0 - 1.0).
        source_engine: محرك OCR المستخدم.
        fps: معدّل الإطارات في الثانية.
    """
    frame_number: int
    timestamp: float
    timestamp_formatted: str
    text: str
    confidence: float
    source_engine: str = ""
    fps: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """تحويل إلى قاموس."""
        return {
            "frame_number": self.frame_number,
            "timestamp": self.timestamp,
            "timestamp_formatted": self.timestamp_formatted,
            "text": self.text,
            "confidence": self.confidence,
            "source_engine": self.source_engine,
            "fps": self.fps,
            "metadata": self.metadata,
        }


@dataclass
class VideoTimeline:
    """الجدول الزمني للفيديو مع نتائج OCR.

    يحتوي ملخصاً كاملاً لكل الإطارات المُعالجة.
    """
    video_path: str = ""
    total_frames: int = 0
    processed_frames: int = 0
    fps: float = 0.0
    duration_seconds: float = 0.0
    frame_interval: int = 30
    results: list[FrameResult] = field(default_factory=list)

    @property
    def frames_with_text(self) -> int:
        """عدد الإطارات التي تحتوي نصاً."""
        return sum(1 for r in self.results if r.text.strip())

    @property
    def avg_confidence(self) -> float:
        """متوسط الثقة للإطارات التي تحتوي نصاً."""
        confidences = [r.confidence for r in self.results if r.text.strip() and r.confidence > 0]
        return sum(confidences) / len(confidences) if confidences else 0.0

    def to_dict(self) -> dict[str, Any]:
        """تحويل إلى قاموس."""
        return {
            "video_path": self.video_path,
            "total_frames": self.total_frames,
            "processed_frames": self.processed_frames,
            "fps": self.fps,
            "duration_seconds": round(self.duration_seconds, 2),
            "frame_interval": self.frame_interval,
            "frames_with_text": self.frames_with_text,
            "avg_confidence": round(self.avg_confidence, 4),
            "results": [r.to_dict() for r in self.results],
        }

    def get_text_only(self) -> str:
        """الحصول على النص الكامل فقط (بدون بيانات وصفية)."""
        return "\n".join(
            f"[{r.timestamp_formatted}] {r.text}"
            for r in self.results
            if r.text.strip()
        )


# ======================================================================
# فئة مستخرج النصوص من الفيديو
# ======================================================================

class VideoOCR:
    """مستخرج النصوص من الفيديو باستخدام OpenCV و OCR.

    يجمع بين استخراج الإطارات و التعرف على النصوص لتوفير
    نتائج مؤقتة (timestamped) من محتوى الفيديو.

    Attributes:
        frame_interval: عدد الإطارات بين كل عملية استخراج.
        ocr_engine: محرك OCR (يُحمَّل كسولاً عند أول استخدام).
    """

    def __init__(
        self,
        frame_interval: int = 30,
        ocr_engine: Optional[Any] = None,
        confidence_threshold: float = 0.3,
        min_text_length: int = 2,
        max_results: Optional[int] = None,
    ) -> None:
        """تهيئة مستخرج النصوص من الفيديو.

        Args:
            frame_interval: عدد الإطارات بين كل عملية استخراج
                           (الافتراضي 30 ≈ 1 ثانية عند 30fps).
            ocr_engine: مثيل OCREngine (اختياري، يُنشأ تلقائياً إذا لم يُحدد).
            confidence_threshold: أقل حد للثقة لقبول النتيجة.
            min_text_length: أقل طول نص مقبول (للتخلص من الضوضاء).
            max_results: أقصى عدد نتائج (None = بلا حد).
        """
        self.frame_interval = max(1, frame_interval)
        self._ocr_engine = ocr_engine
        self.confidence_threshold = confidence_threshold
        self.min_text_length = min_text_length
        self.max_results = max_results

        # التحقق من توفر المكتبات
        self._has_cv2 = self._check_library("cv2", "opencv-python")
        self._has_pil = self._check_library("PIL", "Pillow")

        if not self._has_cv2:
            logger.warning(
                "OpenCV غير مثبت. لن تعمل معالجة الفيديو. "
                "pip install opencv-python-headless"
            )

    @staticmethod
    def _check_library(import_name: str, package_name: str) -> bool:
        """التحقق من توفر مكتبة."""
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # تحميل محرك OCR (كسول)
    # ------------------------------------------------------------------

    def _get_ocr_engine(self) -> Any:
        """الحصول على محرك OCR (يُحمَّل عند أول استخدام).

        Returns:
            مثيل OCREngine أو None إذا لم يكن متاحاً.
        """
        if self._ocr_engine is not None:
            return self._ocr_engine

        try:
            from modules.vision.ocr_engine import OCREngine
            self._ocr_engine = OCREngine(
                enable_trocr=False,
                enable_easyocr=True,
                enable_tesseract=True,
                enable_paddleocr=False,
                enable_surya=False,
                confidence_threshold=self.confidence_threshold,
                preprocess=True,
            )
            logger.info("تم تحميل محرك OCR للفيديو بنجاح")
            return self._ocr_engine
        except Exception as e:
            logger.error("فشل في تحميل محرك OCR: %s", e)
            return None

    # ------------------------------------------------------------------
    # استخراج الإطارات
    # ------------------------------------------------------------------

    def extract_frames(
        self,
        video_path: str | Path,
        output_dir: Optional[str | Path] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[tuple[int, Any]]:
        """استخراج إطارات من ملف فيديو.

        Args:
            video_path: مسار ملف الفيديو.
            output_dir: مجلد حفظ الإطارات (اختياري، لا يحفظ إذا None).
            progress_callback: دالة (current_frame, total_frames) لتتبع التقدم.

        Returns:
            قائمة أزواج (frame_number, PIL.Image).

        Raises:
            FileNotFoundError: إذا لم يكن ملف الفيديو موجوداً.
            RuntimeError: إذا لم يكن OpenCV متاحاً.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"ملف الفيديو غير موجود: {video_path}")

        if not self._has_cv2:
            raise RuntimeError("OpenCV غير متاح — لا يمكن استخراج الإطارات")

        import cv2
        from PIL import Image

        # التحقق من الصيغة
        ext = video_path.suffix.lower()
        if ext not in SUPPORTED_VIDEO_EXTENSIONS:
            logger.warning("صيغة فيديو غير شائعة: %s — سيُحاول فتحها", ext)

        # إنشاء مجلد الإطارات إذا طُلب
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"فشل في فتح ملف الفيديو: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        frames: list[tuple[int, Image.Image]] = []
        frame_number = 0

        logger.info(
            "جارٍ استخراج إطارات من: %s (إجمالي: %d, FPS: %.1f, فاصل: %d)",
            video_path.name, total_frames, fps, self.frame_interval,
        )

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_number % self.frame_interval == 0:
                # تحويل BGR إلى RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)

                frames.append((frame_number, pil_image))

                # حفظ الإطار إذا طُلب
                if output_dir:
                    frame_path = output_dir / f"frame_{frame_number:06d}.png"
                    pil_image.save(frame_path)

                # استدعاء رد الاتصال
                if progress_callback:
                    try:
                        progress_callback(frame_number, total_frames)
                    except Exception as e:
                        logger.debug("خطأ في رد الاتصال: %s", e)

            frame_number += 1

        cap.release()
        logger.info("تم استخراج %d إطار من %s", len(frames), video_path.name)

        return frames

    # ------------------------------------------------------------------
    # معالجة الفيديو
    # ------------------------------------------------------------------

    def process_video(
        self,
        video_path: str | Path,
        languages: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
    ) -> VideoTimeline:
        """معالجة ملف فيديو واستخراج النصوص من إطاراته.

        Args:
            video_path: مسار ملف الفيديو.
            languages: لغات OCR المطلوبة (مثل ["ar", "en"]).
            progress_callback: دالة (frame_idx, total_frames, pct) لتتبع التقدم.

        Returns:
            كائن VideoTimeline يحتوي كل النتائج.

        Raises:
            FileNotFoundError: إذا لم يكن ملف الفيديو موجوداً.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"ملف الفيديو غير موجود: {video_path}")

        start_time = time.time()

        # استخراج الإطارات
        frames = self.extract_frames(video_path)

        if not frames:
            logger.warning("لم يُستخرج أي إطار من الفيديو")
            return VideoTimeline(
                video_path=str(video_path),
                frame_interval=self.frame_interval,
            )

        # الحصول على محرك OCR
        ocr_engine = self._get_ocr_engine()
        if ocr_engine is None:
            logger.warning("محرك OCR غير متاح — إرجاع إطارات بدون نص")
            return VideoTimeline(
                video_path=str(video_path),
                total_frames=len(frames) * self.frame_interval,
                processed_frames=len(frames),
                frame_interval=self.frame_interval,
            )

        # معالجة كل إطار
        results: list[FrameResult] = []
        total = len(frames)

        # الحصول على FPS
        fps = 30.0
        if self._has_cv2:
            import cv2
            cap = cv2.VideoCapture(str(video_path))
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                cap.release()

        for idx, (frame_num, image) in enumerate(frames):
            try:
                ocr_result = ocr_engine.recognize(image, languages=languages)

                text = ocr_result.get("text", "").strip()
                confidence = float(ocr_result.get("confidence", 0.0))
                source = ocr_result.get("source", "unknown")

                # فلترة النتائج
                if len(text) < self.min_text_length:
                    text = ""
                if confidence < self.confidence_threshold:
                    text = ""

                timestamp = frame_num / fps if fps > 0 else 0.0
                minutes = int(timestamp) // 60
                seconds = int(timestamp) % 60

                result = FrameResult(
                    frame_number=frame_num,
                    timestamp=round(timestamp, 2),
                    timestamp_formatted=f"{minutes:02d}:{seconds:02d}",
                    text=text,
                    confidence=confidence,
                    source_engine=source,
                    fps=fps,
                    metadata={
                        "processing_time": ocr_result.get("processing_time", 0.0),
                    },
                )
                results.append(result)

            except Exception as e:
                logger.warning("فشل OCR للإطار %d: %s", frame_num, e)
                results.append(FrameResult(
                    frame_number=frame_num,
                    timestamp=round(frame_num / fps, 2) if fps > 0 else 0.0,
                    timestamp_formatted="00:00",
                    text="",
                    confidence=0.0,
                    fps=fps,
                    metadata={"error": str(e)},
                ))

            # استدعاء رد الاتصال
            if progress_callback:
                try:
                    pct = (idx + 1) / total * 100
                    progress_callback(idx + 1, total, pct)
                except Exception as e:
                    logger.debug("خطأ في رد الاتصال: %s", e)

            # حد أقصى للنتائج
            if self.max_results and len(results) >= self.max_results:
                break

        elapsed = time.time() - start_time
        frames_with_text = sum(1 for r in results if r.text.strip())

        logger.info(
            "تمت معالجة الفيديو '%s': %d إطار, %d بنص, %.1f ثانية",
            video_path.name, len(results), frames_with_text, elapsed,
        )

        timeline = VideoTimeline(
            video_path=str(video_path),
            total_frames=total * self.frame_interval,
            processed_frames=len(frames),
            fps=fps,
            duration_seconds=total * self.frame_interval / fps if fps > 0 else 0.0,
            frame_interval=self.frame_interval,
            results=results,
        )

        return timeline

    # ------------------------------------------------------------------
    # معالجة الكاميرا (بث مباشر)
    # ------------------------------------------------------------------

    def process_camera(
        self,
        camera_id: int = 0,
        duration: float = 10.0,
        languages: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
    ) -> list[FrameResult]:
        """معالجة بث مباشر من الكاميرا واستخراج النصوص.

        Args:
            camera_id: معرّف الكاميرا (الافتراضي 0 = الكاميرا الأساسية).
            duration: مدة الالتقاط بالثواني.
            languages: لغات OCR.
            progress_callback: دالة (frame_idx, total_expected, pct) لتتبع التقدم.

        Returns:
            قائمة نتائج الإطارات.
        """
        if not self._has_cv2:
            raise RuntimeError("OpenCV غير متاح — لا يمكن الوصول للكاميرا")

        import cv2
        from PIL import Image

        ocr_engine = self._get_ocr_engine()
        if ocr_engine is None:
            raise RuntimeError("محرك OCR غير متاح")

        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            raise RuntimeError(f"فشل في فتح الكاميرا {camera_id}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        max_frames = int(duration * fps)

        results: list[FrameResult] = []
        frame_number = 0
        start_time = time.time()

        logger.info(
            "جارٍ الالتقاط من الكاميرا %d (مدة: %.1fs, FPS: %.1f)",
            camera_id, duration, fps,
        )

        try:
            while frame_number < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_number % self.frame_interval == 0:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)

                    try:
                        ocr_result = ocr_engine.recognize(pil_image, languages=languages)

                        text = ocr_result.get("text", "").strip()
                        confidence = float(ocr_result.get("confidence", 0.0))

                        if len(text) < self.min_text_length:
                            text = ""
                        if confidence < self.confidence_threshold:
                            text = ""

                        elapsed = time.time() - start_time
                        minutes = int(elapsed) // 60
                        seconds = int(elapsed) % 60

                        results.append(FrameResult(
                            frame_number=frame_number,
                            timestamp=round(elapsed, 2),
                            timestamp_formatted=f"{minutes:02d}:{seconds:02d}",
                            text=text,
                            confidence=confidence,
                            source_engine=ocr_result.get("source", "unknown"),
                            fps=fps,
                        ))
                    except Exception as e:
                        logger.warning("فشل OCR للإطار %d من الكاميرا: %s", frame_number, e)

                    # استدعاء رد الاتصال
                    if progress_callback:
                        try:
                            pct = frame_number / max_frames * 100
                            progress_callback(frame_number, max_frames, pct)
                        except Exception:
                            pass

                frame_number += 1
        finally:
            cap.release()

        logger.info(
            "تم الالتقاط من الكاميرا: %d إطار في %.1fs",
            len(results), time.time() - start_time,
        )

        return results

    # ------------------------------------------------------------------
    # الجدول الزمني
    # ------------------------------------------------------------------

    def get_timeline(
        self,
        video_path: str | Path,
        languages: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
    ) -> dict[str, Any]:
        """الحصول على الجدول الزمني للنصوص في الفيديو.

        يُرجع ملخصاً منسقاً مع النصوص المؤقتة.

        Args:
            video_path: مسار ملف الفيديو.
            languages: لغات OCR.
            progress_callback: دالة لتتبع التقدم.

        Returns:
            قاموس يحتوي:
            - summary: ملخص إحصائي
            - timeline: قائمة الإطارات مع النصوص
            - full_text: النص الكامل فقط
        """
        timeline = self.process_video(video_path, languages, progress_callback)

        return {
            "summary": {
                "video_path": str(video_path),
                "duration_seconds": timeline.duration_seconds,
                "total_frames_processed": timeline.processed_frames,
                "frames_with_text": timeline.frames_with_text,
                "avg_confidence": timeline.avg_confidence,
                "frame_interval": timeline.frame_interval,
            },
            "timeline": [
                {
                    "timestamp": r.timestamp_formatted,
                    "timestamp_seconds": r.timestamp,
                    "text": r.text,
                    "confidence": r.confidence,
                    "engine": r.source_engine,
                }
                for r in timeline.results
                if r.text.strip()
            ],
            "full_text": timeline.get_text_only(),
        }
