#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
training/cloud/aws_sagemaker.py
==============================

تكامل مع AWS SageMaker للتدريب السحابي.

المميزات:
- تدريب على instances قوية (P3, P4, G5)
- Spot instances للتوفير
- Auto-scaling
- S3 integration

المؤلف: Dr. Abdulmalek Al-husseini
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import boto3


class SageMakerTrainer:
    """مدرب SageMaker."""

    def __init__(
        self,
        role_arn: str = None,
        region: str = 'us-east-1',
        bucket: str = None
    ):
        self.role_arn = role_arn or os.getenv('SAGEMAKER_ROLE')
        self.region = region
        self.bucket = bucket or os.getenv('SAGEMAKER_BUCKET')

        # عملاء AWS
        self.sagemaker = boto3.client('sagemaker', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)

        if not self.role_arn or not self.bucket:
            raise ValueError("SAGEMAKER_ROLE و SAGEMAKER_BUCKET مطلوبان")

    def upload_dataset(
        self,
        local_path: Path,
        s3_key: str = None
    ) -> str:
        """
        رفع بيانات لـ S3.

        Args:
            local_path: مسار البيانات المحلي
            s3_key: مفتاح S3 (اختياري)

        Returns:
            URI S3
        """
        if s3_key is None:
            s3_key = f"training-data/{int(time.time())}/{local_path.name}"

        s3_uri = f"s3://{self.bucket}/{s3_key}"

        if local_path.is_dir():
            # رفع مجلد
            for file_path in local_path.rglob('*'):
                if file_path.is_file():
                    relative = file_path.relative_to(local_path)
                    self.s3.upload_file(
                        str(file_path),
                        self.bucket,
                        f"{s3_key}/{relative}"
                    )
        else:
            # رفع ملف
            self.s3.upload_file(str(local_path), self.bucket, s3_key)

        print(f"✅ تم الرفع: {s3_uri}")
        return s3_uri

    def create_training_job(
        self,
        job_name: str,
        dataset_s3_uri: str,
        output_s3_uri: str = None,
        instance_type: str = 'ml.p3.2xlarge',
        use_spot: bool = True,
        max_wait: int = 86400,  # 24 ساعة
        hyperparameters: Dict = None
    ) -> str:
        """
        إنشاء مهمة تدريب SageMaker.

        Args:
            job_name: اسم المهمة
            dataset_s3_uri: URI بيانات التدريب
            output_s3_uri: URI إخراج النموذج
            instance_type: نوع الـ instance
            use_spot: استخدام Spot instances (أرخص)
            max_wait: أقصى وقت انتظار
            hyperparameters: hyperparameters إضافية

        Returns:
            اسم المهمة
        """
        # إنشاء اسم فريد
        timestamp = int(time.time())
        full_job_name = f"omnifile-{job_name}-{timestamp}"

        # إعدادات الإخراج
        if output_s3_uri is None:
            output_s3_uri = f"s3://{self.bucket}/models/{full_job_name}"

        # إنشاء script تدريب
        training_script = self._generate_training_script(hyperparameters)

        # رفع الـ script
        script_s3_uri = f"s3://{self.bucket}/scripts/{full_job_name}/train.py"
        self.s3.put_object(
            Bucket=self.bucket,
            Key=f"scripts/{full_job_name}/train.py",
            Body=training_script.encode()
        )

        # إعدادات التدريب
        training_params = {
            'TrainingJobName': full_job_name,
            'RoleArn': self.role_arn,
            'AlgorithmSpecification': {
                'TrainingInputMode': 'File',
                'TrainingImage': self._get_pytorch_image(),
                'ContainerEntrypoint': ['python', '/opt/ml/input/data/code/train.py']
            },
            'InputDataConfig': [
                {
                    'ChannelName': 'training',
                    'DataSource': {
                        'S3DataSource': {
                            'S3DataType': 'S3Prefix',
                            'S3Uri': dataset_s3_uri,
                            'S3DataDistributionType': 'FullyReplicated'
                        }
                    },
                    'ContentType': 'application/x-parquet',
                    'CompressionType': 'None'
                },
                {
                    'ChannelName': 'code',
                    'DataSource': {
                        'S3DataSource': {
                            'S3DataType': 'S3Prefix',
                            'S3Uri': f"s3://{self.bucket}/scripts/{full_job_name}",
                            'S3DataDistributionType': 'FullyReplicated'
                        }
                    }
                }
            ],
            'OutputDataConfig': {
                'S3OutputPath': output_s3_uri
            },
            'ResourceConfig': {
                'InstanceType': instance_type,
                'InstanceCount': 1,
                'VolumeSizeInGB': 100
            },
            'StoppingCondition': {
                'MaxRuntimeInSeconds': max_wait
            },
            'HyperParameters': {
                k: str(v) for k, v in (hyperparameters or {}).items()
            },
            'Tags': [
                {'Key': 'Project', 'Value': 'OmniFile'},
                {'Key': 'Type', 'Value': 'HTR-Training'}
            ]
        }

        # Spot training (أرخص بنسبة 70%)
        if use_spot:
            training_params['EnableManagedSpotTraining'] = True
            training_params['StoppingCondition']['MaxWaitTimeInSeconds'] = max_wait * 2

        # إنشاء المهمة
        response = self.sagemaker.create_training_job(**training_params)

        print(f"🚀 تم إنشاء مهمة التدريب: {full_job_name}")
        print(f"   Instance: {instance_type}")
        print(f"   Spot: {'نعم' if use_spot else 'لا'}")
        print(f"   Output: {output_s3_uri}")

        return full_job_name

    def wait_for_completion(self, job_name: str, poll_interval: int = 60):
        """
        انتظار انتهاء المهمة.

        Args:
            job_name: اسم المهمة
            poll_interval: فترة الفحص بالثواني

        Returns:
            حالة المهمة
        """
        while True:
            response = self.sagemaker.describe_training_job(
                TrainingJobName=job_name
            )

            status = response['TrainingJobStatus']
            secondary_status = response.get('SecondaryStatus', '')

            print(f"⏳ الحالة: {status} ({secondary_status})")

            if status in ['Completed', 'Failed', 'Stopped']:
                break

            time.sleep(poll_interval)

        # النتائج
        if status == 'Completed':
            model_uri = response['ModelArtifacts']['S3ModelArtifacts']
            print(f"✅ اكتمل! النموذج: {model_uri}")
            return {'status': 'success', 'model_uri': model_uri}

        elif status == 'Failed':
            reason = response.get('FailureReason', 'Unknown')
            print(f"❌ فشل: {reason}")
            return {'status': 'failed', 'reason': reason}

        else:
            return {'status': 'stopped'}

    def download_model(self, job_name: str, local_dir: Path):
        """تحميل النموذج المدرب."""
        response = self.sagemaker.describe_training_job(
            TrainingJobName=job_name
        )

        model_uri = response['ModelArtifacts']['S3ModelArtifacts']

        # تحميل من S3
        import urllib.parse
        parsed = urllib.parse.urlparse(model_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')

        local_dir = Path(local_dir)
        local_dir.mkdir(parents=True, exist_ok=True)

        self.s3.download_file(bucket, key, str(local_dir / 'model.tar.gz'))

        # فك الضغط
        import tarfile
        with tarfile.open(local_dir / 'model.tar.gz', 'r:gz') as tar:
            tar.extractall(local_dir)

        print(f"✅ تم التحميل: {local_dir}")
        return local_dir

    def create_endpoint(
        self,
        model_uri: str,
        endpoint_name: str = None,
        instance_type: str = 'ml.g4dn.xlarge'
    ):
        """
        إنشاء endpoint للاستنتاج.

        Args:
            model_uri: URI النموذج في S3
            endpoint_name: اسم الـ endpoint
            instance_type: نوع الـ instance

        Returns:
            اسم الـ endpoint
        """
        if endpoint_name is None:
            endpoint_name = f"omnifile-htr-{int(time.time())}"

        # إنشاء model
        model_name = f"{endpoint_name}-model"
        self.sagemaker.create_model(
            ModelName=model_name,
            PrimaryContainer={
                'Image': self._get_pytorch_inference_image(),
                'ModelDataUrl': model_uri,
                'Environment': {
                    'SAGEMAKER_PROGRAM': 'inference.py',
                    'SAGEMAKER_SUBMIT_DIRECTORY': '/opt/ml/model/code'
                }
            },
            ExecutionRoleArn=self.role_arn
        )

        # إنشاء endpoint config
        config_name = f"{endpoint_name}-config"
        self.sagemaker.create_endpoint_config(
            EndpointConfigName=config_name,
            ProductionVariants=[
                {
                    'VariantName': 'AllTraffic',
                    'ModelName': model_name,
                    'InstanceType': instance_type,
                    'InitialInstanceCount': 1,
                    'InitialVariantWeight': 1.0
                }
            ]
        )

        # إنشاء endpoint
        self.sagemaker.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=config_name
        )

        print(f"🌐 Endpoint: {endpoint_name}")
        return endpoint_name

    def _generate_training_script(self, hyperparameters: Dict) -> str:
        """توليد script تدريب."""
        return f'''
import os
import sys
import json

# إضافة المكتبات
sys.path.append('/opt/ml/code')

from training.scripts.train_trocr_lora import train

# قراءة hyperparameters
with open('/opt/ml/input/config/hyperparameters.json') as f:
    hyperparameters = json.load(f)

# مسارات
data_dir = '/opt/ml/input/data/training'
output_dir = '/opt/ml/model'

# تشغيل التدريب
config = {{
    'model': {{
        'base_model': hyperparameters.get('base_model', 'microsoft/trocr-large-handwritten'),
        'generation': {{'max_length': 128, 'num_beams': 4}}
    }},
    'lora': {{
        'enabled': True,
        'r': int(hyperparameters.get('lora_r', 16)),
        'alpha': int(hyperparameters.get('lora_alpha', 32)),
        'dropout': 0.05,
        'target_modules': ['q_proj', 'v_proj', 'k_proj', 'o_proj']
    }},
    'training': {{
        'num_epochs': int(hyperparameters.get('epochs', 10)),
        'per_device_batch_size': int(hyperparameters.get('batch_size', 4)),
        'gradient_accumulation_steps': 4,
        'learning_rate': float(hyperparameters.get('learning_rate', 1e-4)),
        'output_dir': output_dir
    }},
    'data': {{
        'train_path': f'{data_dir}/train',
        'val_path': f'{data_dir}/val',
        'format': 'lmdb'
    }},
    'export': {{
        'merge_and_unload': True,
        'push_to_hub': False
    }}
}}

# تدريب
train(config_path=None, **config)

# حفظ النموذج
print("✅ Training completed!")
print(f"Model saved to: {output_dir}")
'''

    def _get_pytorch_image(self) -> str:
        """الحصول على Docker image PyTorch."""
        account_id = '763104351884'  # AWS Deep Learning Containers
        region = self.region

        return f"{account_id}.dkr.ecr.{region}.amazonaws.com/pytorch-training:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker"

    def _get_pytorch_inference_image(self) -> str:
        """الحصول على Docker image للاستنتاج."""
        account_id = '763104351884'
        region = self.region

        return f"{account_id}.dkr.ecr.{region}.amazonaws.com/pytorch-inference:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker"


# ============================================================================
# استخدام سهل
# ============================================================================

def train_on_sagemaker(
    dataset_path: Path,
    job_name: str = "omnifile-htr",
    instance_type: str = "ml.p3.2xlarge",
    use_spot: bool = True,
    **hyperparameters
) -> Dict:
    """
    تدريب سهل على SageMaker.

    Args:
        dataset_path: مسار البيانات المحلي
        job_name: اسم المهمة
        instance_type: نوع الـ instance
        use_spot: استخدام Spot instances
        **hyperparameters: hyperparameters إضافية

    Returns:
        نتائج التدريب
    """
    trainer = SageMakerTrainer()

    # رفع البيانات
    print("📤 رفع البيانات...")
    dataset_s3 = trainer.upload_dataset(dataset_path)

    # إنشاء مهمة
    print("🚀 إنشاء مهمة التدريب...")
    job = trainer.create_training_job(
        job_name=job_name,
        dataset_s3_uri=dataset_s3,
        instance_type=instance_type,
        use_spot=use_spot,
        hyperparameters=hyperparameters
    )

    # انتظار
    print("⏳ انتظار الانتهاء...")
    result = trainer.wait_for_completion(job)

    if result['status'] == 'success':
        # تحميل النموذج
        print("📥 تحميل النموذج...")
        local_path = Path(f"./models/{job}")
        trainer.download_model(job, local_path)
        result['local_path'] = str(local_path)

    return result


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python aws_sagemaker.py <dataset_path> [job_name]")
        sys.exit(1)

    dataset = Path(sys.argv[1])
    job = sys.argv[2] if len(sys.argv) > 2 else "omnifile-htr"

    result = train_on_sagemaker(dataset, job)
    print(f"\nResults: {result}")
