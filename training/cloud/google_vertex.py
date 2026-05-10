#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
training/cloud/google_vertex.py
================================

تكامل مع Google Cloud Vertex AI.

المميزات:
- TPUs للتدريب السريع
- AutoML للنماذج التلقائية
- Integration مع GCS
- Vertex AI Pipelines

المؤلف: Dr. Abdulmalek Al-husseini
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from google.cloud import aiplatform, storage
from google.cloud.aiplatform.gapic.schema import trainingjob


class VertexTrainer:
    """مدرب Vertex AI."""

    def __init__(
        self,
        project_id: str = None,
        location: str = 'us-central1',
        staging_bucket: str = None
    ):
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.location = location
        self.staging_bucket = staging_bucket or os.getenv('VERTEX_BUCKET')

        # تهيئة
        aiplatform.init(
            project=self.project_id,
            location=self.location,
            staging_bucket=self.staging_bucket
        )

        self.storage_client = storage.Client(project=self.project_id)

        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT مطلوب")

    def upload_dataset(
        self,
        local_path: Path,
        gcs_path: str = None
    ) -> str:
        """
        رفع بيانات لـ Google Cloud Storage.

        Args:
            local_path: مسار البيانات المحلي
            gcs_path: مسار GCS (اختياري)

        Returns:
            URI GCS
        """
        bucket_name = self.staging_bucket.replace('gs://', '').split('/')[0]
        bucket = self.storage_client.bucket(bucket_name)

        if gcs_path is None:
            gcs_path = f"training-data/{int(time.time())}/{local_path.name}"

        if local_path.is_dir():
            # رفع مجلد
            for file_path in local_path.rglob('*'):
                if file_path.is_file():
                    relative = file_path.relative_to(local_path)
                    blob = bucket.blob(f"{gcs_path}/{relative}")
                    blob.upload_from_filename(str(file_path))
        else:
            # رفع ملف
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(str(local_path))

        gcs_uri = f"gs://{bucket_name}/{gcs_path}"
        print(f"✅ تم الرفع: {gcs_uri}")
        return gcs_uri

    def create_custom_job(
        self,
        display_name: str,
        script_path: Path,
        dataset_gcs_uri: str,
        output_gcs_uri: str = None,
        machine_type: str = 'n1-standard-8',
        accelerator_type: str = 'NVIDIA_TESLA_V100',
        accelerator_count: int = 1,
        replica_count: int = 1,
        hyperparameters: Dict = None
    ) -> aiplatform.CustomJob:
        """
        إنشاء مهمة تدريب مخصصة على Vertex AI.

        Args:
            display_name: اسم المهمة
            script_path: مسار script التدريب
            dataset_gcs_uri: URI بيانات التدريب
            output_gcs_uri: URI إخراج النموذج
            machine_type: نوع الآلة
            accelerator_type: نوع المسرع
            accelerator_count: عدد المسرعات
            replica_count: عدد النسخ
            hyperparameters: hyperparameters إضافية

        Returns:
            CustomJob
        """
        # إعدادات الإخراج
        if output_gcs_uri is None:
            bucket_name = self.staging_bucket.replace('gs://', '').split('/')[0]
            output_gcs_uri = f"gs://{bucket_name}/models/{display_name}-{int(time.time())}"

        # إعدادات الم容器
        container_spec = {
            'image_uri': 'us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.1-13:latest',
            'command': ['python', '-u', str(script_path)],
            'args': [
                '--data-dir', dataset_gcs_uri,
                '--output-dir', output_gcs_uri,
                '--epochs', str(hyperparameters.get('epochs', 10)),
                '--batch-size', str(hyperparameters.get('batch_size', 16)),
                '--learning-rate', str(hyperparameters.get('learning_rate', 1e-4)),
                '--lora-r', str(hyperparameters.get('lora_r', 16)),
                '--lora-alpha', str(hyperparameters.get('lora_alpha', 32)),
            ]
        }

        # إعدادات العمل
        worker_pool_specs = [{
            'machine_spec': {
                'machine_type': machine_type,
                'accelerator_type': accelerator_type,
                'accelerator_count': accelerator_count,
            },
            'replica_count': replica_count,
            'container_spec': container_spec,
        }]

        # إنشاء المهمة
        job = aiplatform.CustomJob(
            display_name=f"omnifile-{display_name}",
            worker_pool_specs=worker_pool_specs,
            base_output_dir=output_gcs_uri,
        )

        print(f"🚀 تم إنشاء مهمة: {job.display_name}")
        print(f"   Machine: {machine_type}")
        print(f"   Accelerator: {accelerator_type} x{accelerator_count}")
        print(f"   Output: {output_gcs_uri}")

        return job

    def run_training_pipeline(
        self,
        display_name: str,
        dataset_gcs_uri: str,
        model_display_name: str = None,
        **hyperparameters
    ) -> Dict:
        """
        تشغيل pipeline تدريب كامل.

        Args:
            display_name: اسم الـ pipeline
            dataset_gcs_uri: URI البيانات
            model_display_name: اسم النموذج
            **hyperparameters: hyperparameters

        Returns:
            نتائج التدريب
        """
        # إنشاء script مؤقت
        script_path = Path('/tmp/train_vertex.py')
        script_path.write_text(self._generate_training_script())

        # إنشاء المهمة
        job = self.create_custom_job(
            display_name=display_name,
            script_path=script_path,
            dataset_gcs_uri=dataset_gcs_uri,
            **hyperparameters
        )

        # تشغيل
        print("▶️ تشغيل التدريب...")
        job.run(sync=True)

        # النتائج
        results = {
            'job_name': job.display_name,
            'state': job.state.name,
            'output_dir': job.base_output_dir,
        }

        if job.state.name == 'JOB_STATE_SUCCEEDED':
            print(f"✅ اكتمل التدريب!")
            print(f"   Output: {job.base_output_dir}")

            # تسجيل النموذج
            if model_display_name:
                model = aiplatform.Model.upload(
                    display_name=model_display_name,
                    artifact_uri=job.base_output_dir,
                    serving_container_image_uri='us-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.1-13:latest'
                )
                results['model_id'] = model.name

        return results

    def deploy_model(
        self,
        model_name: str,
        machine_type: str = 'n1-standard-4',
        accelerator_type: str = None,
        accelerator_count: int = 0
    ) -> aiplatform.Endpoint:
        """
        نشر نموذج على endpoint.

        Args:
            model_name: اسم النموذج
            machine_type: نوع الآلة
            accelerator_type: نوع المسرع
            accelerator_count: عدد المسرعات

        Returns:
            Endpoint
        """
        # الحصول على النموذج
        model = aiplatform.Model(model_name)

        # إنشاء endpoint
        endpoint = aiplatform.Endpoint.create(
            display_name=f"{model_name}-endpoint"
        )

        # نشر
        model.deploy(
            endpoint=endpoint,
            machine_type=machine_type,
            accelerator_type=accelerator_type,
            accelerator_count=accelerator_count,
            min_replica_count=1,
            max_replica_count=3,
            traffic_percentage=100
        )

        print(f"🌐 Endpoint: {endpoint.resource_name}")
        return endpoint

    def _generate_training_script(self) -> str:
        """توليد script تدريب لـ Vertex AI."""
        return '''
import argparse
import os
import sys
import json
from pathlib import Path

# إضافة المسار
sys.path.append('/opt/ml/code')

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=str, required=True)
    parser.add_argument('--output-dir', type=str, required=True)
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--learning-rate', type=float, default=1e-4)
    parser.add_argument('--lora-r', type=int, default=16)
    parser.add_argument('--lora-alpha', type=int, default=32)
    return parser.parse_args()

def main():
    args = parse_args()

    print(f"📊 Data: {args.data_dir}")
    print(f"📤 Output: {args.output_dir}")
    print(f"⚙️ Epochs: {args.epochs}")

    # استيراد training module
    from training.scripts.train_trocr_lora import train

    # إعدادات
    config = {
        'model': {
            'base_model': 'microsoft/trocr-large-handwritten',
            'generation': {'max_length': 128, 'num_beams': 4}
        },
        'lora': {
            'enabled': True,
            'r': args.lora_r,
            'alpha': args.lora_alpha,
            'dropout': 0.05,
            'target_modules': ['q_proj', 'v_proj', 'k_proj', 'o_proj']
        },
        'training': {
            'num_epochs': args.epochs,
            'per_device_batch_size': args.batch_size,
            'gradient_accumulation_steps': 4,
            'learning_rate': args.learning_rate,
            'output_dir': args.output_dir
        },
        'data': {
            'train_path': f'{args.data_dir}/train',
            'val_path': f'{args.data_dir}/val',
            'format': 'lmdb'
        },
        'export': {
            'merge_and_unload': True,
            'push_to_hub': False
        }
    }

    # تدريب
    train(config_path=None, **config)

    # حفظ النتائج
    results = {
        'status': 'completed',
        'output_dir': args.output_dir
    }

    with open(f'{args.output_dir}/results.json', 'w') as f:
        json.dump(results, f)

    print("✅ Training completed!")

if __name__ == '__main__':
    main()
'''


# ============================================================================
# استخدام سهل
# ============================================================================

def train_on_vertex(
    dataset_path: Path,
    project_id: str = None,
    location: str = 'us-central1',
    display_name: str = "omnifile-htr",
    machine_type: str = 'n1-standard-8',
    accelerator_type: str = 'NVIDIA_TESLA_V100',
    accelerator_count: int = 1,
    **hyperparameters
) -> Dict:
    """
    تدريب سهل على Google Cloud Vertex AI.

    Args:
        dataset_path: مسار البيانات المحلي
        project_id: معرف المشروع
        location: المنطقة
        display_name: اسم المهمة
        machine_type: نوع الآلة
        accelerator_type: نوع المسرع
        accelerator_count: عدد المسرعات
        **hyperparameters: hyperparameters

    Returns:
        نتائج التدريب
    """
    trainer = VertexTrainer(project_id=project_id, location=location)

    # رفع البيانات
    print("📤 رفع البيانات...")
    dataset_gcs = trainer.upload_dataset(dataset_path)

    # تشغيل
    print("🚀 تشغيل التدريب...")
    results = trainer.run_training_pipeline(
        display_name=display_name,
        dataset_gcs_uri=dataset_gcs,
        **hyperparameters
    )

    return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python google_vertex.py <dataset_path> [display_name]")
        sys.exit(1)

    dataset = Path(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else "omnifile-htr"

    result = train_on_vertex(dataset, display_name=name)
    print(f"\nResults: {result}")
