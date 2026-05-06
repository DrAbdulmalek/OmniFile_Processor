# sync_backend.py - Sync backend for mobile review

"""
🔗 وحدة مزامنة الموبايل مع Colab/محلي
تدعم: جوجل درايف، مجلد محلي، أو خادم WebDAV
"""

import os, json, time, hashlib
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MobileSyncBackend:
    """إدارة مزامنة التصحيحات بين الموبايل وبيئة التطوير"""

    def __init__(self, sync_root: str = None, provider: str = "local"):
        """
        Args:
            sync_root: المسار الجذر للمزامنة (مجلد محلي أو نقطة ربط Google Drive)
            provider: نوع المزود: "local" | "gdrive" | "webdav"
        """
        self.provider = provider
        self.sync_root = Path(sync_root) if sync_root else Path.home() / "OmniFile_MobileSync"
        self.sync_root.mkdir(parents=True, exist_ok=True)

        # مجلدات فرعية قياسية
        (self.sync_root / "corrections").mkdir(exist_ok=True)
        (self.sync_root / "exports").mkdir(exist_ok=True)
        (self.sync_root / "logs").mkdir(exist_ok=True)

        self.correction_index = self._load_index()

    def _load_index(self) -> Dict:
        """تحميل فهرس التصحيحات لتسريع البحث"""
        index_path = self.sync_root / "corrections" / ".index.json"
        if index_path.exists():
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                logger.warning("فشل تحميل الفهرس - سيتم إعادة بنائه")
        return {"corrections": {}, "last_sync": None}

    def _save_index(self):
        """حفظ الفهرس بعد التحديث"""
        index_path = self.sync_root / "corrections" / ".index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(self.correction_index, f, ensure_ascii=False, indent=2)

    def receive_correction(self, block_id: str, data: Dict) -> bool:
        """
        استقبال تصحيح من الموبايل وحفظه

        Args:
            block_id: معرف الكتلة (مثال: blk_042)
            data: قاموس يحتوي على: original, corrected, timestamp, device_info

        Returns:
            bool: نجاح العملية
        """
        # تحقق من صحة البيانات
        required = ["original", "corrected", "timestamp"]
        if not all(k in data for k in required):
            logger.error(f"بيانات غير كاملة لـ {block_id}: {data.keys()}")
            return False

        # توليد معرف فريد للتصحيح
        correction_id = hashlib.sha256(
            f"{block_id}:{data['original']}:{data['corrected']}".encode()
        ).hexdigest()[:12]

        # حفظ كملف منفصل (للمزامنة الجزئية)
        correction_file = self.sync_root / "corrections" / f"{block_id}.{correction_id}.json"
        payload = {
            "block_id": block_id,
            "correction_id": correction_id,
            "received_at": datetime.now().isoformat(),
            **data
        }

        with open(correction_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        # تحديث الفهرس
        self.correction_index["corrections"][block_id] = {
            "latest_correction_id": correction_id,
            "last_updated": payload["received_at"],
            "confidence_boost": 0.05  # مكافأة ثقة للتعديلات البشرية
        }
        self._save_index()

        logger.info(f"✅ استلام تصحيح: {block_id} → {correction_id}")
        return True

    def get_pending_corrections(self, limit: int = 50) -> List[Dict]:
        """جلب التصحيحات الجديدة التي لم تُدمج بعد"""
        pending = []
        corrections_dir = self.sync_root / "corrections"

        for corr_file in corrections_dir.glob("*.json"):
            if corr_file.name.startswith("."):
                continue  # تخطي ملفات الفهرس

            try:
                with open(corr_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # تحقق مما إذا كان هذا التصحيح قد دُمج سابقاً
                block_id = data.get("block_id")
                if block_id and self._is_merged(block_id, data.get("correction_id")):
                    continue

                pending.append(data)

                if len(pending) >= limit:
                    break
            except Exception as e:
                logger.warning(f"خطأ في قراءة {corr_file}: {e}")

        return sorted(pending, key=lambda x: x.get("received_at", ""), reverse=True)

    def _is_merged(self, block_id: str, correction_id: str) -> bool:
        """التحقق مما إذا تم دمج تصحيح معين سابقاً"""
        merged_file = self.sync_root / "exports" / "merged_corrections.json"
        if not merged_file.exists():
            return False

        try:
            with open(merged_file, "r", encoding="utf-8") as f:
                merged = json.load(f)
            return correction_id in merged.get("correction_ids", [])
        except:
            return False

    def mark_as_merged(self, corrections: List[Dict]):
        """وضع علامة على التصحيحات كمُدمجة لمنع التكرار"""
        merged_file = self.sync_root / "exports" / "merged_corrections.json"
        merged = {"correction_ids": [], "last_update": datetime.now().isoformat()}

        if merged_file.exists():
            try:
                with open(merged_file, "r", encoding="utf-8") as f:
                    merged = json.load(f)
            except:
                pass

        merged["correction_ids"].extend(c.get("correction_id") for c in corrections)
        merged["last_update"] = datetime.now().isoformat()

        with open(merged_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        logger.info(f"🗂️ وُضعت علامة دمج على {len(corrections)} تصحيح")

    def export_for_training(self, output_format: str = "tsv") -> Path:
        """تصدير التصحيحات كمدخلات تدريب"""
        corrections = self.get_pending_corrections(limit=1000)
        if not corrections:
            logger.info("لا توجد تصحيحات جديدة للتصدير")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_file = self.sync_root / "exports" / f"corrections_{timestamp}.{output_format}"

        if output_format == "tsv":
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("block_id\toriginal\tcorrected\ttimestamp\tconfidence_boost\n")
                for c in corrections:
                    boost = self.correction_index.get("corrections", {}).get(
                        c.get("block_id"), {}
                    ).get("confidence_boost", 0.05)
                    f.write(f"{c['block_id']}\t{c['original']}\t{c['corrected']}\t{c['received_at']}\t{boost}\n")

        elif output_format == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(corrections, f, ensure_ascii=False, indent=2)

        # وضع علامة دمج بعد التصدير الناجح
        self.mark_as_merged(corrections)

        logger.info(f"📤 صُدّرت {len(corrections)} تصحيحات إلى: {output_file}")
        return output_file

    def sync_with_colab(self, colab_workspace: Path) -> int:
        """مزامنة التصحيحات مع مساحة عمل Colab"""
        merged_count = 0
        pending = self.get_pending_corrections()

        for corr in pending:
            block_id = corr["block_id"]
            # تحديث قاموس التصحيحات في مساحة العمل
            correction_dict_path = colab_workspace / "correction_dict.json"

            if correction_dict_path.exists():
                with open(correction_dict_path, "r", encoding="utf-8") as f:
                    correction_dict = json.load(f)
            else:
                correction_dict = {}

            # إضافة التصحيح مع أولوية للنص المصحح
            if corr["original"] not in correction_dict:
                correction_dict[corr["original"]] = corr["corrected"]
                merged_count += 1

            with open(correction_dict_path, "w", encoding="utf-8") as f:
                json.dump(correction_dict, f, ensure_ascii=False, indent=2)

        if merged_count > 0:
            self.mark_as_merged(pending)
            logger.info(f"🔄 دُمج {merged_count} تصحيح جديد في قاموس التصحيحات")

        return merged_count

# 🔹 دالة مساعدة للاستخدام السريع في Colab
def setup_mobile_sync(colab_workspace: str = "/content/omnifile_workspace"):
    """تهيئة المزامنة في بيئة Colab"""
    workspace = Path(colab_workspace)
    sync_backend = MobileSyncSync(
        sync_root=workspace / "mobile_sync",
        provider="local"  # يمكن تغييره لـ "gdrive" عند ربط Drive
    )

    # دمج التصحيحات الواردة تلقائياً عند الاستيراد
    merged = sync_backend.sync_with_colab(workspace)
    if merged > 0:
        print(f"✅ دُمج {merged} تصحيح جديد من الموبايل")

    return sync_backend
