"""
معالج ملفات PDF
==================
يقوم باستخراج النصوص والصور والجداول من ملفات PDF
باستخدام PyMuPDF (fitz) مع pdfplumber كاحتياطي للتخطيطات المعقدة.

القدرات:
- استخراج النص من صفحات محددة أو كل الصفحات
- تحويل الصفحات إلى صور PIL
- دعم الملفات المحمية بكلمة مرور
- تتبع التقدم عبر دوال الاستدعاء (callbacks)
- دعم المسارات الملفية والبايتات (bytes)
"""

import logging
from typing import Optional, Union, Callable, Any
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    معالج ملفات PDF - يستخدم PyMuPDF للسرعة و pdfplumber للتخطيطات المعقدة.

    مثال الاستخدام:
        >>> processor = PDFProcessor(dpi=300)
        >>> results = processor.process_pdf("document.pdf", pages=[0, 1, 2])
        >>> count = processor.get_page_count("document.pdf")
        >>> img = processor.extract_page("document.pdf", page_num=0)
    """

    def __init__(
        self,
        dpi: int = 300,
        use_pdfplumber_fallback: bool = True,
        password: Optional[str] = None,
    ) -> None:
        """
        تهيئة معالج PDF.

        Args:
            dpi: دقة التحول إلى صور (الافتراضي 300)
            use_pdfplumber_fallback: استخدام pdfplumber كاحتياطي (الافتراضي True)
            password: كلمة مرور افتراضية للملفات المحمية
        """
        self.dpi = dpi
        self.use_pdfplumber_fallback = use_pdfplumber_fallback
        self.default_password = password

        # التحقق من توفر المكتبات
        self._has_fitz = self._check_library("fitz", "PyMuPDF")
        self._has_pdfplumber = self._check_library("pdfplumber", "pdfplumber")
        self._has_pil = self._check_library("PIL", "Pillow")

        if not self._has_fitz:
            logger.warning(
                "PyMuPDF (fitz) غير مثبت. لن يتمكن المعالج من العمل بشكل كامل. "
                "قم بالتثبيت: pip install PyMuPDF"
            )

    @staticmethod
    def _check_library(import_name: str, package_name: str) -> bool:
        """التحقق من توفر مكتبة معينة."""
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False

    # ------------------------------------------------------------------
    # الأساليب العامة (Public API)
    # ------------------------------------------------------------------

    def get_page_count(self, pdf_source: Union[str, bytes]) -> int:
        """
        الحصول على عدد صفحات ملف PDF.

        Args:
            pdf_source: مسار الملف أو البايتات الخام

        Returns:
            عدد الصفحات

        Raises:
            ValueError: إذا لم يكن الملف صالحاً أو لم تتوفر المكتبة
        """
        if not self._has_fitz:
            raise RuntimeError("PyMuPDF (fitz) غير مثبت - لا يمكن معالجة PDF")

        try:
            doc = self._open_document(pdf_source)
            count = len(doc)
            doc.close()
            logger.debug("عدد صفحات PDF: %d", count)
            return count
        except Exception as e:
            logger.error("فشل في قراءة عدد صفحات PDF: %s", e)
            raise ValueError(f"فشل في قراءة ملف PDF: {e}") from e

    def extract_page(
        self,
        pdf_source: Union[str, bytes],
        page_num: int,
    ) -> "PIL.Image.Image":
        """
        تحويل صفحة PDF إلى صورة PIL.

        Args:
            pdf_source: مسار الملف أو البايتات الخام
            page_num: رقم الصفحة (يبدأ من 0)

        Returns:
            صورة PIL للصفحة المطلوبة

        Raises:
            IndexError: إذا كان رقم الصفحة خارج النطاق
            RuntimeError: إذا لم تتوفر المكتبات المطلوبة
        """
        if not self._has_fitz or not self._has_pil:
            raise RuntimeError("PyMuPDF و Pillow مطلوبان لتحويل PDF إلى صورة")

        try:
            doc = self._open_document(pdf_source)
            if page_num < 0 or page_num >= len(doc):
                doc.close()
                raise IndexError(
                    f"رقم الصفحة {page_num} خارج النطاق (0-{len(doc)-1})"
                )

            page = doc[page_num]
            # تحويل الصفحة إلى مصفوفة بكسلات
            mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.h, pix.w, pix.n
            )

            from PIL import Image

            # التأكد من أن الصورة بصيغة RGB
            if pix.n == 4:
                image = Image.fromarray(img_array[:, :, :3], mode="RGB")
            elif pix.n == 1:
                image = Image.fromarray(img_array[:, :, 0], mode="L").convert("RGB")
            else:
                image = Image.fromarray(img_array, mode="RGB")

            doc.close()
            logger.debug("تم تحويل الصفحة %d إلى صورة بنجاح", page_num)
            return image

        except IndexError:
            raise
        except Exception as e:
            logger.error("فشل في تحويل الصفحة %d إلى صورة: %s", page_num, e)
            raise RuntimeError(f"فشل في تحويل الصفحة إلى صورة: {e}") from e

    def process_pdf(
        self,
        pdf_source: Union[str, bytes],
        pages: Optional[list[int]] = None,
        password: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        معالجة ملف PDF بالكامل واستخراج المحتوى.

        Args:
            pdf_source: مسار الملف أو البايتات الخام
            pages: قائمة أرقام الصفحات (يبدأ من 0). None = كل الصفحات
            password: كلمة مرور للملفات المحمية (تجاوز الافتراضي)
            progress_callback: دالة استدعاء لمراقبة التقدم (current, total, status)

        Returns:
            قائمة قواميس، كل قاموس يحتوي:
            - page_num: رقم الصفحة (يبدأ من 0)
            - text: النص المستخرج
            - images: قائمة الصور المستخرجة (PIL Images)
            - tables: قائمة الجداول المستخرجة (قوائم القوائم)
        """
        if not self._has_fitz:
            raise RuntimeError("PyMuPDF (fitz) غير مثبت - لا يمكن معالجة PDF")

        pwd = password or self.default_password

        try:
            doc = self._open_document(pdf_source, password=pwd)
            total_pages = len(doc)

            # تحديد الصفحات المطلوبة
            if pages is None:
                target_pages = list(range(total_pages))
            else:
                target_pages = [p for p in pages if 0 <= p < total_pages]

            logger.info(
                "بدء معالجة PDF: %d صفحة مطلوبة من أصل %d",
                len(target_pages), total_pages,
            )

            results: list[dict[str, Any]] = []

            for idx, page_num in enumerate(target_pages):
                try:
                    if progress_callback:
                        progress_callback(idx + 1, len(target_pages), f"معالجة صفحة {page_num + 1}")

                    page_result = self._process_single_page(
                        doc, page_num, use_pdfplumber=False
                    )

                    # استخدام pdfplumber كاحتياطي إذا لم يُستخرج نص
                    if (
                        self.use_pdfplumber_fallback
                        and self._has_pdfplumber
                        and not page_result["text"].strip()
                    ):
                        logger.debug(
                            "لا يوجد نص في صفحة %d باستخدام PyMuPDF، "
                            "جرب pdfplumber...",
                            page_num,
                        )
                        page_result_fallback = self._process_single_page_pdfplumber(
                            pdf_source, page_num, password=pwd
                        )
                        # دمج النتائج
                        if page_result_fallback["text"].strip():
                            page_result["text"] = page_result_fallback["text"]
                            page_result["tables"] = page_result_fallback["tables"]

                    results.append(page_result)
                    logger.debug(
                        "تمت معالجة الصفحة %d: %d حرف، %d صورة",
                        page_num,
                        len(page_result["text"]),
                        len(page_result["images"]),
                    )

                except Exception as e:
                    logger.error("خطأ في معالجة الصفحة %d: %s", page_num, e)
                    results.append({
                        "page_num": page_num,
                        "text": "",
                        "images": [],
                        "tables": [],
                        "error": str(e),
                    })

            doc.close()

            if progress_callback:
                progress_callback(len(target_pages), len(target_pages), "اكتملت المعالجة")

            logger.info("تمت معالجة %d صفحة بنجاح", len(results))
            return results

        except Exception as e:
            logger.error("فشل في معالجة ملف PDF: %s", e)
            raise RuntimeError(f"فشل في معالجة ملف PDF: {e}") from e

    # ------------------------------------------------------------------
    # الأساليب الداخلية (Private)
    # ------------------------------------------------------------------

    def _open_document(
        self,
        pdf_source: Union[str, bytes],
        password: Optional[str] = None,
    ) -> "fitz.Document":
        """
        فتح مستند PDF من مسار ملف أو بايتات.

        Args:
            pdf_source: مسار الملف أو البايتات الخام
            password: كلمة مرور للملفات المحمية

        Returns:
            مستند PyMuPDF مفتوح
        """
        import fitz

        try:
            if isinstance(pdf_source, (str, Path)):
                path_str = str(pdf_source)
                if not Path(path_str).exists():
                    raise FileNotFoundError(f"الملف غير موجود: {path_str}")
                doc = fitz.open(path_str)
            elif isinstance(pdf_source, bytes):
                doc = fitz.open(stream=pdf_source, filetype="pdf")
            else:
                raise TypeError(
                    f"نوع غير مدعوم لـ pdf_source: {type(pdf_source)}"
                )

            # فك تشفير الملف إذا كان محمياً
            if doc.is_encrypted:
                if password:
                    if not doc.authenticate(password):
                        doc.close()
                        raise PermissionError("كلمة المرور غير صحيحة")
                elif self.default_password:
                    if not doc.authenticate(self.default_password):
                        doc.close()
                        raise PermissionError("كلمة المرور الافتراضية غير صحيحة")
                else:
                    doc.close()
                    raise PermissionError(
                        "ملف PDF محمي بكلمة مرور ولم يتم توفير واحدة"
                    )

            return doc

        except Exception as e:
            raise RuntimeError(f"فشل في فتح مستند PDF: {e}") from e

    def _process_single_page(
        self,
        doc: "fitz.Document",
        page_num: int,
        use_pdfplumber: bool = False,
    ) -> dict[str, Any]:
        """
        معالجة صفحة واحدة باستخدام PyMuPDF.

        Args:
            doc: مستند PyMuPDF مفتوح
            page_num: رقم الصفحة
            use_pdfplumber: تجاهل - يُستخدم داخلياً

        Returns:
            قاموس بالنتائج
        """
        import fitz

        page = doc[page_num]

        # استخراج النص
        text = page.get_text("text").strip()

        # استخراج الصور
        images: list[Any] = []
        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                if base_image:
                    from PIL import Image
                    import io

                    img_bytes = base_image["image"]
                    img_pil = Image.open(io.BytesIO(img_bytes))
                    images.append(img_pil.convert("RGB"))
            except Exception as e:
                logger.warning(
                    "فشل في استخراج صورة %d من صفحة %d: %s",
                    img_idx, page_num, e,
                )

        # تحويل الصفحة إلى صورة كاملة
        page_image = None
        try:
            mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.h, pix.w, pix.n
            )
            if self._has_pil:
                from PIL import Image

                if pix.n == 4:
                    page_image = Image.fromarray(img_array[:, :, :3], mode="RGB")
                elif pix.n == 1:
                    page_image = Image.fromarray(img_array[:, :, 0], mode="L").convert("RGB")
                else:
                    page_image = Image.fromarray(img_array, mode="RGB")
        except Exception as e:
            logger.warning("فشل في تحويل صفحة %d إلى صورة: %s", page_num, e)

        return {
            "page_num": page_num,
            "text": text,
            "images": images,
            "tables": [],
            "page_image": page_image,
        }

    def _process_single_page_pdfplumber(
        self,
        pdf_source: Union[str, bytes],
        page_num: int,
        password: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        معالجة صفحة واحدة باستخدام pdfplumber كاحتياطي.

        مفيد للتخطيطات المعقدة والجداول.

        Args:
            pdf_source: مسار الملف أو البايتات الخام
            page_num: رقم الصفحة
            password: كلمة مرور (يدعم pdfplumber المحمية فقط في بعض الحالات)

        Returns:
            قاميس بالنتائج
        """
        import pdfplumber

        tables: list[Any] = []
        text = ""

        try:
            if isinstance(pdf_source, (str, Path)):
                pdf = pdfplumber.open(str(pdf_source), password=password)
            elif isinstance(pdf_source, bytes):
                pdf = pdfplumber.open(io.BytesIO(pdf_source))
            else:
                raise TypeError(f"نوع غير مدعوم: {type(pdf_source)}")

            if page_num < 0 or page_num >= len(pdf.pages):
                pdf.close()
                return {"page_num": page_num, "text": "", "images": [], "tables": []}

            page = pdf.pages[page_num]
            text = (page.extract_text() or "").strip()
            tables = [table for table in (page.extract_tables() or []) if table]
            pdf.close()

        except Exception as e:
            logger.warning("pdfplumber فشل في معالجة صفحة %d: %s", page_num, e)

        return {
            "page_num": page_num,
            "text": text,
            "images": [],
            "tables": tables,
            "page_image": None,
        }

    def get_metadata(
        self, pdf_source: Union[str, bytes]
    ) -> dict[str, Any]:
        """
        استخراج البيانات الوصفية (metadata) من ملف PDF.

        Args:
            pdf_source: مسار الملف أو البايتات الخام

        Returns:
            قاموس يحتوي البيانات الوصفية
        """
        if not self._has_fitz:
            raise RuntimeError("PyMuPDF (fitz) غير مثبت")

        try:
            doc = self._open_document(pdf_source)
            metadata = doc.metadata or {}
            doc.close()

            result = {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "modification_date": metadata.get("modDate", ""),
                "page_count": self.get_page_count(pdf_source),
                "is_encrypted": False,
            }

            # التحقق من التشفير
            try:
                doc = self._open_document(pdf_source)
                result["is_encrypted"] = doc.is_encrypted
                doc.close()
            except Exception:
                result["is_encrypted"] = True

            return result

        except Exception as e:
            logger.error("فشل في استخراج البيانات الوصفية: %s", e)
            raise RuntimeError(f"فشل في استخراج البيانات الوصفية: {e}") from e
