# async_hf_pipeline.py - Async HuggingFace pipeline

"""
⚡ خط أنابيب تصدير غير متزامن لـ HuggingFace
متوافق مع Jupyter/Colab، يدعم تقدم مرئي، ويعزل أخطاء الملفات عن بعضها
"""

import asyncio, json, logging
from pathlib import Path
from typing import Optional, Dict, List, Callable
from datetime import datetime
import aiofiles
from datasets import Dataset, DatasetDict
from huggingface_hub import HfApi

logger = logging.getLogger(__name__)

class AsyncHFExportPipeline:
    def __init__(self, image_dir: Optional[str] = None, store_images: bool = True):
        self.image_dir = Path(image_dir) if image_dir else None
        self.store_images = store_images
        self.api = HfApi()

    def set_progress_callback(self, callback: Callable[[float, str], None]):
        """ربط دالة تتبع التقدم (مثال: tqdm أو عنصر Colab)"""
        self._progress_cb = callback

    async def _process_file(self, file_path: Path) -> List[dict]:
        """معالجة ملف JSON واحد بشكل غير متزامن"""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                ann = json.loads(content)

            records = []
            doc_id = ann.get("doc_id", file_path.stem)
            for page in ann.get("pages", []):
                for block in page.get("blocks", []):
                    records.append({
                        "doc_id": doc_id,
                        "page_id": page.get("page_id", ""),
                        "block_id": block.get("id", ""),
                        "original_text": block.get("text", ""),
                        "corrected_text": block.get("text", ""),
                        "confidence": float(block.get("confidence", 0.0)),
                        "block_type": block.get("type", "unknown"),
                        "language": block.get("language", "ar"),
                        "source": block.get("source", "unknown"),
                        "image_path": str(self.image_dir / f"{page.get('source_image', '')}") if self.store_images else ""
                    })
            return records
        except Exception as e:
            logger.warning(f"⚠️ فشل في معالجة {file_path.name}: {e}")
            return []

    async def process_annotations_async(self, dir_path: str, batch_size: int = 50) -> Dataset:
        dir_path = Path(dir_path)
        files = list(dir_path.glob("*.json"))
        all_records = []
        processed = 0

        # معالجة متوازية مع تحكم بالذاكرة
        for i in range(0, len(files), batch_size):
            batch = files[i:i+batch_size]
            tasks = [self._process_file(f) for f in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in results:
                if isinstance(res, list):
                    all_records.extend(res)

            processed += len(batch)
            if hasattr(self, "_progress_cb"):
                self._progress_cb(processed / len(files), f"معالجة {processed}/{len(files)}")

            # منع انسداد الذاكرة في Colab
            await asyncio.sleep(0.01)

        if not all_records:
            raise ValueError("لم يتم استخراج أي كتل صالحة")

        return Dataset.from_list(all_records)

    async def push_to_hub_async(self, dataset: Dataset, repo_name: str, private: bool = True) -> str:
        logger.info(f"📤 بدء الرفع إلى {repo_name}...")
        # الرفع نفسه غير متزامن جزئياً، نستخدم run_in_executor لعدم حظر الحلقة
        loop = asyncio.get_event_loop()
        url = await loop.run_in_executor(None, dataset.push_to_hub, repo_name, private)
        logger.info(f"🚗 تم الرفع: {url}")
        return url

    # 🎛️ مساعد لـ Colab
    @staticmethod
    def run_colab_async(coro):
        """تشغيل Coroutine في Jupyter/Colab بأمان"""
        try:
            loop = asyncio.get_running_loop()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)
