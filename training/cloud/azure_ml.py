#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
training/cloud/azure_ml.py
==========================

تكامل مع Azure Machine Learning.

المميزات:
- Azure ML Compute
- Azure Container Instances
- Azure Kubernetes Service
- Integration مع Azure Storage

المؤلف: Dr. Abdulmalek Al-husseini
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from azure.ai.ml import MLClient, command, Input, Output
from azure.ai.ml.entities import (
    AmlCompute, Environment, Data, Model, Endpoint, ManagedOnlineEndpoint,
    ManagedOnlineDeployment
)
from azure.identity import DefaultAzureCredential


class AzureMLTrainer:
    """مدرب Azure ML."""

    def __init__(
        self,
        subscription_id: str = None,
        resource_group: str = None,
        workspace_name: str = None
    ):
        self.subscription_id = subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID')
        self.resource_group = resource_group or os.getenv('AZURE_RESOURCE_GROUP')
        self.workspace_name = workspace_name or os.getenv('AZURE_WORKSPACE_NAME')

        # إنشاء العميل
        credential = DefaultAzureCredential()
        self.ml_client = MLClient(
            credential=credential,
            subscription_id=self.subscription_id,
            resource_group_name=self.resource_group,
            workspace_name=self.workspace_name
        )

        if not all([self.subscription_id, self.resource_group, self.workspace_name]):
            raise ValueError("Azure ML credentials مطلوبة")

    def create_compute(
        self,
        compute_name: str = "omnifile-gpu",
        size: str = "Standard_NC6s_v3",
        min_instances: int = 0,
        max_instances: int = 2,
        idle_time_before_scale_down: int = 1800
    ) -> AmlCompute:
        """
        إنشاء compute cluster.

        Args:
            compute_name: اسم الـ compute
            size: حجم الـ VM
            min_instances: الحد الأدنى
            max_instances: الحد الأقصى
            idle_time_before_scale_down: وقت الخمول قبل التصغير

        Returns:
            AmlCompute
        """
        try:
            # التحقق من الوجود
            compute = self.ml_client.compute.get(compute_name)
            print(f"✅ Compute موجود: {compute_name}")
            return compute
        except Exception:
            # إنشاء جديد
            compute = AmlCompute(
                name=compute_name,
                type="amlcompute",
                size=size,
                min_instances=min_instances,
                max_instances=max_instances,
                idle_time_before_scale_down=idle_time_before_scale_down,
                tier="Dedicated"
            )

            self.ml_client.compute.begin_create_or_update(compute).result()
            print(f"✅ تم إنشاء compute: {compute_name} ({size})")
            return compute

    def create_environment(
        self,
        name: str = "omnifile-env",
        base_image: str = "mcr.microsoft.com/azureml/openmpi4.1.0-cuda11.8-cudnn8-ubuntu22.04:latest",
        conda_file: Path = None
    ) -> Environment:
        """
        إنشاء بيئة تدريب.

        Args:
            name: اسم البيئة
            base_image: الصورة الأساسية
            conda_file: ملف conda (اختياري)

        Returns:
            Environment
        """
        if conda_file is None:
            # إنشاء conda file افتراضي
            conda_file = Path('/tmp/conda.yml')
            conda_file.write_text('''
name: omnifile
channels:
  - pytorch
  - nvidia
  - conda-forge
  - defaults
dependencies:
  - python=3.10
  - pytorch=2.0.1
  - torchvision=0.15.2
  - torchaudio=2.0.2
  - pytorch-cuda=11.8
  - cudatoolkit=11.8
  - pip
  - pip:
    - transformers==4.35.0
    - peft==0.6.0
    - accelerate==0.24.0
    - datasets==2.14.0
    - pillow==10.0.0
    - numpy==1.24.0
    - wandb==0.16.0
    - azureml-mlflow==1.53.0
''')

        env = Environment(
            name=name,
            description="OmniFile HTR Training Environment",
            image=base_image,
            conda_file=str(conda_file)
        )

        self.ml_client.environments.create_or_update(env)
        print(f"✅ تم إنشاء البيئة: {name}")
        return env

    def upload_dataset(
        self,
        local_path: Path,
        dataset_name: str = None,
        description: str = "OmniFile training data"
    ) -> Data:
        """
        رفع بيانات لـ Azure ML.

        Args:
            local_path: مسار البيانات
            dataset_name: اسم الـ dataset
            description: الوصف

        Returns:
            Data asset
        """
        if dataset_name is None:
            dataset_name = f"omnifile-data-{int(time.time())}"

        data = Data(
            name=dataset_name,
            description=description,
            path=str(local_path),
            type="uri_folder"
        )

        self.ml_client.data.create_or_update(data)
        print(f"✅ تم رفع البيانات: {dataset_name}")
        return data

    def create_training_job(
        self,
        display_name: str,
        compute_name: str,
        environment_name: str,
        dataset_name: str,
        output_model_name: str = None,
        hyperparameters: Dict = None
    ):
        """
        إنشاء مهمة تدريب.

        Args:
            display_name: اسم المهمة
            compute_name: اسم الـ compute
            environment_name: اسم البيئة
            dataset_name: اسم الـ dataset
            output_model_name: اسم النموذج المخرج
            hyperparameters: hyperparameters

        Returns:
            Job
        """
        if output_model_name is None:
            output_model_name = f"{display_name}-model"

        # إعدادات التدريب
        job = command(
            name=display_name,
            display_name=display_name,
            description="OmniFile HTR Training",
            experiment_name="omnifile-htr",
            compute=compute_name,
            environment=f"{environment_name}@latest",
            inputs={
                "training_data": Input(type="uri_folder", path=dataset_name),
                "epochs": hyperparameters.get('epochs', 10),
                "batch_size": hyperparameters.get('batch_size', 16),
                "learning_rate": hyperparameters.get('learning_rate', 1e-4),
                "lora_r": hyperparameters.get('lora_r', 16),
                "lora_alpha": hyperparameters.get('lora_alpha', 32),
            },
            outputs={
                "model_output": Output(type="uri_folder", path=f"azureml://datastores/workspaceblobstore/paths/{output_model_name}")
            },
            command="""
                python -m training.scripts.train_trocr_lora \
                    --data-dir ${{inputs.training_data}} \
                    --output-dir ${{outputs.model_output}} \
                    --epochs ${{inputs.epochs}} \
                    --batch-size ${{inputs.batch_size}} \
                    --learning-rate ${{inputs.learning_rate}} \
                    --lora-r ${{inputs.lora_r}} \
                    --lora-alpha ${{inputs.lora_alpha}}
            """
        )

        # إرسال المهمة
        returned_job = self.ml_client.jobs.create_or_update(job)
        print(f"🚀 تم إنشاء المهمة: {returned_job.name}")
        print(f"   Experiment: {returned_job.experiment_name}")
        print(f"   Compute: {compute_name}")

        return returned_job

    def wait_for_completion(self, job_name: str, poll_interval: int = 60):
        """
        انتظار انتهاء المهمة.

        Args:
            job_name: اسم المهمة
            poll_interval: فترة الفحص

        Returns:
            حالة المهمة
        """
        while True:
            job = self.ml_client.jobs.get(job_name)
            status = job.status

            print(f"⏳ الحالة: {status}")

            if status in ['Completed', 'Failed', 'Canceled']:
                break

            time.sleep(poll_interval)

        if status == 'Completed':
            print(f"✅ اكتملت المهمة!")
            return {'status': 'success', 'job': job}
        elif status == 'Failed':
            print(f"❌ فشلت المهمة!")
            return {'status': 'failed', 'job': job}
        else:
            return {'status': 'canceled', 'job': job}

    def register_model(
        self,
        model_name: str,
        model_path: str,
        description: str = "OmniFile HTR Model",
        tags: Dict = None
    ) -> Model:
        """
        تسجيل نموذج.

        Args:
            model_name: اسم النموذج
            model_path: مسار النموذج
            description: الوصف
            tags: tags

        Returns:
            Model
        """
        model = Model(
            name=model_name,
            path=model_path,
            description=description,
            tags=tags or {'project': 'omnifile', 'type': 'htr'}
        )

        self.ml_client.models.create_or_update(model)
        print(f"✅ تم تسجيل النموذج: {model_name}")
        return model

    def deploy_endpoint(
        self,
        endpoint_name: str,
        model_name: str,
        deployment_name: str = "default",
        instance_type: str = "Standard_DS3_v2"
    ) -> ManagedOnlineEndpoint:
        """
        نشر endpoint.

        Args:
            endpoint_name: اسم الـ endpoint
            model_name: اسم النموذج
            deployment_name: اسم الـ deployment
            instance_type: نوع الـ instance

        Returns:
            Endpoint
        """
        # إنشاء endpoint
        endpoint = ManagedOnlineEndpoint(
            name=endpoint_name,
            description="OmniFile HTR Endpoint",
            auth_mode="key"
        )

        self.ml_client.online_endpoints.begin_create_or_update(endpoint).result()

        # إنشاء deployment
        deployment = ManagedOnlineDeployment(
            name=deployment_name,
            endpoint_name=endpoint_name,
            model=model_name,
            instance_type=instance_type,
            instance_count=1
        )

        self.ml_client.online_deployments.begin_create_or_update(deployment).result()

        # توجيه traffic
        endpoint.traffic = {deployment_name: 100}
        self.ml_client.online_endpoints.begin_create_or_update(endpoint).result()

        print(f"🌐 Endpoint: {endpoint_name}")
        print(f"   Deployment: {deployment_name}")
        print(f"   Instance: {instance_type}")

        return endpoint


# ============================================================================
# استخدام سهل
# ============================================================================

def train_on_azure(
    dataset_path: Path,
    subscription_id: str = None,
    resource_group: str = None,
    workspace_name: str = None,
    display_name: str = "omnifile-htr",
    compute_size: str = "Standard_NC6s_v3",
    **hyperparameters
) -> Dict:
    """
    تدريب سهل على Azure ML.

    Args:
        dataset_path: مسار البيانات
        subscription_id: معرف الاشتراك
        resource_group: مجموعة الموارد
        workspace_name: اسم مساحة العمل
        display_name: اسم المهمة
        compute_size: حجم الـ compute
        **hyperparameters: hyperparameters

    Returns:
        نتائج التدريب
    """
    trainer = AzureMLTrainer(
        subscription_id=subscription_id,
        resource_group=resource_group,
        workspace_name=workspace_name
    )

    # إنشاء compute
    print("⚙️ إنشاء compute...")
    trainer.create_compute(compute_name="omnifile-gpu", size=compute_size)

    # إنشاء بيئة
    print("🐍 إنشاء البيئة...")
    trainer.create_environment(name="omnifile-env")

    # رفع البيانات
    print("📤 رفع البيانات...")
    dataset = trainer.upload_dataset(dataset_path)

    # إنشاء مهمة
    print("🚀 إنشاء مهمة التدريب...")
    job = trainer.create_training_job(
        display_name=display_name,
        compute_name="omnifile-gpu",
        environment_name="omnifile-env",
        dataset_name=dataset.name,
        hyperparameters=hyperparameters
    )

    # انتظار
    print("⏳ انتظار الانتهاء...")
    result = trainer.wait_for_completion(job.name)

    if result['status'] == 'success':
        # تسجيل النموذج
        print("📝 تسجيل النموذج...")
        model = trainer.register_model(
            model_name=f"{display_name}-model",
            model_path=result['job'].outputs['model_output']
        )
        result['model'] = model.name

    return result


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python azure_ml.py <dataset_path> [display_name]")
        sys.exit(1)

    dataset = Path(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else "omnifile-htr"

    result = train_on_azure(dataset, display_name=name)
    print(f"\nResults: {result}")
