# نشر عبر Docker

## نظرة عامة

تعليمات لنشر OmniFile Processor باستخدام Docker و Docker Compose.

## البدء السريع

```bash
# استنساخ المشروع
git clone https://github.com/DrAbdulmalek/OmniFile_Processor.git
cd OmniFile_Processor

# تشغيل عبر Docker Compose
docker-compose -f deployment/docker/docker-compose.yml up -d

# الواجهة متاحة على: http://localhost:7860
# API متاح على: http://localhost:8000
```

## بناء الصورة يدوياً

```bash
# بناء صورة API
docker build -f deployment/docker/Dockerfile.api -t omnifile-api .

# بناء صورة التدريب (تحتاج GPU)
docker build -f deployment/docker/Dockerfile.training -t omnifile-training .

# تشغيل
docker run -d -p 7860:7860 --gpus all omnifile-api
```

## النشر على Kubernetes

```bash
# تطبيق مساحة الاسم
kubectl apply -f deployment/k8s/namespace.yaml

# نشر API
kubectl apply -f deployment/k8s/api-deployment.yaml

# مهمة تدريب GPU
kubectl apply -f deployment/k8s/gpu-training-job.yaml
```
