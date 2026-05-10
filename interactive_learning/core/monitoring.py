#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/core/monitoring.py
=======================================

نظام مراقبة متكامل للأداء والجودة.

Provides:
- MetricsCollector: Time-series metrics collection with aggregation
- PerformanceMonitor: Operation timing and latency tracking
- QualityAssurance: Correction validation and quality scoring
- AlertManager: Threshold-based alerting
"""

import logging
import time
import threading
from collections import deque, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
import json

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """لقطة مقياس."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertRule:
    """قاعدة تنبيه."""
    name: str
    metric_name: str
    condition: str  # 'above', 'below', 'spike'
    threshold: float
    cooldown_seconds: float = 300.0
    last_triggered: float = 0.0


class MetricsCollector:
    """
    جامع مقاييس متقدم مع تجميع زمني.

    Collects numeric metrics with optional labels, supports
    time-windowed aggregation and time-series bucketing.

    Usage:
        collector = MetricsCollector()
        collector.record('ocr_latency', 0.45, {'engine': 'trocr'})
        summary = collector.get_summary('ocr_latency', time_window=300)
        series = collector.get_time_series('ocr_latency', bucket_size=60)
    """

    def __init__(self, retention_seconds: float = 3600, max_points: int = 10000):
        """
        Args:
            retention_seconds: How long to keep metrics
            max_points: Maximum points per metric
        """
        self.retention = retention_seconds
        self.max_points = max_points
        self.metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_points)
        )
        self._lock = threading.Lock()

    def record(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        تسجيل قيمة مقياس.

        Args:
            metric_name: Name of the metric
            value: Numeric value
            labels: Optional key-value labels for grouping
        """
        with self._lock:
            snapshot = MetricSnapshot(
                timestamp=time.time(),
                value=value,
                labels=labels or {}
            )
            self.metrics[metric_name].append(snapshot)

    def get_summary(
        self,
        metric_name: str,
        time_window: Optional[float] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        الحصول على ملخص إحصائي.

        Args:
            metric_name: Name of the metric
            time_window: Time window in seconds (None for all)
            labels: Filter by labels

        Returns:
            Dictionary with count, mean, std, min, max, percentiles
        """
        with self._lock:
            snapshots = self.metrics.get(metric_name, deque())

            if not snapshots:
                return {}

            now = time.time()
            window_start = now - time_window if time_window else 0

            values = [
                s.value for s in snapshots
                if s.timestamp >= window_start
                and (labels is None or self._labels_match(s.labels, labels))
            ]

            if not values:
                return {}

            sorted_vals = sorted(values)
            n = len(sorted_vals)

            return {
                'count': n,
                'mean': sum(sorted_vals) / n,
                'std': self._std(sorted_vals),
                'min': sorted_vals[0],
                'max': sorted_vals[-1],
                'p50': self._percentile(sorted_vals, 50),
                'p95': self._percentile(sorted_vals, 95),
                'p99': self._percentile(sorted_vals, 99),
                'last': sorted_vals[-1],
            }

    def get_time_series(
        self,
        metric_name: str,
        time_window: float = 3600,
        bucket_size: float = 60,
        labels: Optional[Dict[str, str]] = None
    ) -> List[Dict]:
        """
        الحصول على سلسلة زمنية مجمعة.

        Args:
            metric_name: Name of the metric
            time_window: Time window in seconds
            bucket_size: Bucket duration in seconds
            labels: Filter by labels

        Returns:
            List of {timestamp, value, count} dictionaries
        """
        with self._lock:
            snapshots = self.metrics.get(metric_name, deque())
            now = time.time()
            window_start = now - time_window

            buckets: Dict[int, List[float]] = defaultdict(list)
            for s in snapshots:
                if s.timestamp >= window_start:
                    if labels and not self._labels_match(s.labels, labels):
                        continue
                    bucket_key = int(s.timestamp / bucket_size) * bucket_size
                    buckets[bucket_key].append(s.value)

            return [
                {
                    'timestamp': ts,
                    'value': sum(vals) / len(vals),
                    'count': len(vals),
                    'min': min(vals),
                    'max': max(vals),
                }
                for ts, vals in sorted(buckets.items())
            ]

    def list_metrics(self) -> List[str]:
        """List all recorded metric names."""
        with self._lock:
            return list(self.metrics.keys())

    def get_all_summaries(self, time_window: float = 300) -> Dict[str, Dict]:
        """Get summaries for all metrics."""
        result = {}
        for name in self.list_metrics():
            summary = self.get_summary(name, time_window=time_window)
            if summary:
                result[name] = summary
        return result

    def clear(self, metric_name: Optional[str] = None):
        """Clear metrics."""
        with self._lock:
            if metric_name:
                self.metrics.pop(metric_name, None)
            else:
                self.metrics.clear()

    def export_json(self, time_window: float = 3600) -> str:
        """Export all metrics as JSON."""
        data = {}
        for name in self.list_metrics():
            series = self.get_time_series(name, time_window=time_window)
            if series:
                data[name] = series
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def _labels_match(snapshot_labels: Dict, filter_labels: Dict) -> bool:
        """Check if snapshot labels match filter."""
        for key, value in filter_labels.items():
            if snapshot_labels.get(key) != value:
                return False
        return True

    @staticmethod
    def _std(values: List[float]) -> float:
        """Compute standard deviation."""
        n = len(values)
        if n < 2:
            return 0.0
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        return variance ** 0.5

    @staticmethod
    def _percentile(sorted_values: List[float], p: int) -> float:
        """Compute percentile from sorted values."""
        n = len(sorted_values)
        if n == 0:
            return 0.0
        k = (n - 1) * p / 100
        f = int(k)
        c = f + 1
        if c >= n:
            return sorted_values[-1]
        d = k - f
        return sorted_values[f] + d * (sorted_values[c] - sorted_values[f])


class PerformanceMonitor:
    """
    مراقب أداء للتعلم التفاعلي.

    Tracks operation durations, model accuracy, and correction impact.

    Usage:
        monitor = PerformanceMonitor()
        monitor.start_operation("ocr_page_1")
        # ... do OCR ...
        monitor.end_operation("ocr_page_1", "ocr", {"page": "1"})
        dashboard = monitor.get_dashboard_data()
    """

    def __init__(self):
        self.collector = MetricsCollector(retention_seconds=86400)
        self.active_operations: Dict[str, float] = {}
        self._lock = threading.Lock()

    def start_operation(self, operation_id: str):
        """
        بدء عملية وتسجيل وقت البدء.

        Args:
            operation_id: Unique identifier for the operation
        """
        with self._lock:
            self.active_operations[operation_id] = time.time()

    def end_operation(
        self,
        operation_id: str,
        operation_type: str,
        labels: Optional[Dict[str, str]] = None,
        success: bool = True
    ) -> Optional[float]:
        """
        إنهاء عملية وتسجيل المدة.

        Args:
            operation_id: Operation identifier
            operation_type: Type category (ocr, training, render, etc.)
            labels: Additional labels
            success: Whether operation succeeded

        Returns:
            Duration in seconds, or None if operation not found
        """
        with self._lock:
            start_time = self.active_operations.pop(operation_id, None)

        if start_time is None:
            return None

        duration = time.time() - start_time

        metric_labels = labels or {}
        metric_labels['status'] = 'success' if success else 'error'

        self.collector.record(
            f"operation_duration_{operation_type}",
            duration,
            metric_labels
        )

        return duration

    def record_accuracy(
        self,
        model_version: str,
        accuracy: float,
        metric_type: str = "cer"
    ):
        """
        تسجيل دقة النموذج.

        Args:
            model_version: Model version identifier
            accuracy: Accuracy value (CER, WER, etc.)
            metric_type: Type of metric
        """
        self.collector.record(
            "model_accuracy",
            accuracy,
            {
                'model_version': model_version,
                'metric_type': metric_type
            }
        )

    def record_correction_impact(
        self,
        word_id: str,
        confidence_before: float,
        confidence_after: float
    ):
        """
        تسجيل تأثير التصحيح على الثقة.

        Args:
            word_id: Word identifier
            confidence_before: OCR confidence before correction
            confidence_after: Expected confidence after correction
        """
        improvement = confidence_after - confidence_before
        self.collector.record(
            "correction_confidence_improvement",
            improvement,
            {'word_id': word_id}
        )

    def record_user_activity(self, user_id: str, activity_type: str):
        """Record a user activity event."""
        self.collector.record(
            "user_activity",
            1.0,
            {'user_id': user_id, 'type': activity_type}
        )

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        بيانات لوحة التحكم.

        Returns:
            Dictionary with current system metrics
        """
        return {
            'ocr_latency': self.collector.get_summary(
                'operation_duration_ocr', time_window=300
            ),
            'training_latency': self.collector.get_summary(
                'operation_duration_training', time_window=3600
            ),
            'render_latency': self.collector.get_summary(
                'operation_duration_render', time_window=300
            ),
            'accuracy_trend': self.collector.get_time_series(
                'model_accuracy', time_window=86400, bucket_size=3600
            ),
            'correction_impact': self.collector.get_summary(
                'correction_confidence_improvement', time_window=3600
            ),
            'active_operations': len(self.active_operations),
            'timestamp': datetime.utcnow().isoformat(),
        }

    def get_report(self, time_window: float = 86400) -> Dict[str, Any]:
        """Generate a comprehensive performance report."""
        return {
            'generated_at': datetime.utcnow().isoformat(),
            'time_window_seconds': time_window,
            'metrics': self.collector.get_all_summaries(time_window=time_window),
            'dashboard': self.get_dashboard_data(),
        }


class QualityAssurance:
    """
    ضمان جودة التصحيحات.

    Validates corrections against built-in and custom rules,
    assigns quality scores, and tracks quality trends.

    Usage:
        qa = QualityAssurance()
        result = qa.validate_correction("فم", "في")
        if result['is_valid']:
            accept_correction()
    """

    def __init__(self):
        self.collector = MetricsCollector(retention_seconds=86400)
        self.quality_rules: List[tuple] = []

    def add_rule(self, rule: Callable[[str, str], bool], name: str):
        """
        إضافة قاعدة جودة مخصصة.

        Args:
            rule: Function that takes (original, corrected) and returns bool
            name: Rule name for reporting
        """
        self.quality_rules.append((name, rule))

    def validate_correction(
        self,
        original: str,
        corrected: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        التحقق من جودة تصحيح.

        Args:
            original: Original OCR text
            corrected: User-corrected text
            context: Optional context (language, confidence, etc.)

        Returns:
            Dictionary with validation results
        """
        results: Dict[str, Any] = {
            'is_valid': True,
            'checks': {},
            'warnings': [],
            'score': 1.0,
            'details': {},
        }

        # 1. Non-empty check
        if not corrected or not corrected.strip():
            results['checks']['non_empty'] = False
            results['is_valid'] = False
            results['score'] = 0.0
            results['warnings'].append('Empty correction')
        else:
            results['checks']['non_empty'] = True

        # 2. Meaningful change check
        if original == corrected:
            results['checks']['meaningful_change'] = False
            results['warnings'].append('No change from original')
        else:
            results['checks']['meaningful_change'] = True

        # 3. Reasonable length check
        if original and corrected:
            len_ratio = len(corrected) / max(len(original), 1)
            results['details']['length_ratio'] = round(len_ratio, 3)

            if len_ratio > 3.0:
                results['checks']['reasonable_length'] = False
                results['warnings'].append(f'Length ratio too high: {len_ratio:.2f}')
                results['score'] *= 0.7
            elif len_ratio < 0.3:
                results['checks']['reasonable_length'] = False
                results['warnings'].append(f'Length ratio too low: {len_ratio:.2f}')
                results['score'] *= 0.7
            else:
                results['checks']['reasonable_length'] = True

        # 4. Valid characters check
        if corrected:
            invalid_chars = [c for c in corrected if ord(c) > 0x10FFFF or ord(c) < 0x20]
            if invalid_chars:
                results['checks']['valid_characters'] = False
                results['is_valid'] = False
                results['score'] = 0.0
                results['warnings'].append(f'Invalid characters: {len(invalid_chars)}')
            else:
                results['checks']['valid_characters'] = True

        # 5. Arabic content check (if context suggests Arabic)
        if context and context.get('language') == 'ar':
            arabic_count = sum(1 for c in corrected if '\u0600' <= c <= '\u06FF')
            ratio = arabic_count / max(len(corrected), 1)
            results['details']['arabic_ratio'] = round(ratio, 3)

            if ratio > 0.1:
                results['checks']['arabic_content'] = True
            else:
                results['checks']['arabic_content'] = False
                results['warnings'].append('Low Arabic content ratio')

        # 6. Apply custom rules
        for rule_name, rule_func in self.quality_rules:
            try:
                rule_passed = rule_func(original, corrected)
                results['checks'][rule_name] = rule_passed
                if not rule_passed:
                    results['score'] *= 0.9
                    results['warnings'].append(f'Rule failed: {rule_name}')
            except Exception as e:
                results['checks'][rule_name] = None
                results['warnings'].append(f'Rule error ({rule_name}): {e}')

        # Final validity check
        passed_checks = [
            v for v in results['checks'].values()
            if v is not None and v is not False
        ]
        failed_checks = [
            k for k, v in results['checks'].items()
            if v is False
        ]

        results['is_valid'] = results['is_valid'] and len(failed_checks) == 0
        results['score'] = max(0.0, min(1.0, results['score']))

        return results

    def record_validation(self, word_id: str, validation_result: Dict):
        """تسجيل نتيجة تحقق."""
        self.collector.record(
            "correction_quality_score",
            validation_result.get('score', 0.0),
            {
                'word_id': word_id,
                'valid': str(validation_result.get('is_valid', False))
            }
        )

    def get_quality_report(self, time_window: float = 86400) -> Dict:
        """Generate quality assurance report."""
        score_summary = self.collector.get_summary(
            'correction_quality_score', time_window=time_window
        )

        total_series = self.collector.get_time_series(
            'correction_quality_score',
            time_window=time_window,
            bucket_size=3600
        )

        return {
            'average_score': score_summary.get('mean', 0.0),
            'total_validations': score_summary.get('count', 0),
            'score_distribution': {
                'min': score_summary.get('min', 0.0),
                'max': score_summary.get('max', 0.0),
                'p50': score_summary.get('p50', 0.0),
                'p95': score_summary.get('p95', 0.0),
            },
            'trend': total_series,
            'custom_rules': len(self.quality_rules),
        }


class AlertManager:
    """
    مدير التنبيهات.

    Monitors metrics against configured thresholds and triggers alerts.

    Usage:
        alert_mgr = AlertManager()
        alert_mgr.add_rule('high_cer', 'model_accuracy', 'above', 0.3)
        alert_mgr.check_rules(metrics_collector)
    """

    def __init__(self):
        self.rules: List[AlertRule] = []
        self.active_alerts: List[Dict] = []
        self.alert_history: deque = deque(maxlen=1000)

    def add_rule(
        self,
        name: str,
        metric_name: str,
        condition: str,
        threshold: float,
        cooldown_seconds: float = 300.0
    ):
        """
        Add an alert rule.

        Args:
            name: Alert name
            metric_name: Metric to monitor
            condition: 'above', 'below', or 'spike'
            threshold: Threshold value
            cooldown_seconds: Minimum seconds between alerts
        """
        self.rules.append(AlertRule(
            name=name,
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            cooldown_seconds=cooldown_seconds
        ))

    def check_rules(self, collector: MetricsCollector) -> List[Dict]:
        """
        Check all rules against current metrics.

        Args:
            collector: MetricsCollector instance

        Returns:
            List of triggered alerts
        """
        triggered = []
        now = time.time()

        for rule in self.rules:
            if now - rule.last_triggered < rule.cooldown_seconds:
                continue

            summary = collector.get_summary(rule.metric_name, time_window=300)
            if not summary:
                continue

            current_value = summary.get('mean', summary.get('last', 0))
            is_triggered = False

            if rule.condition == 'above' and current_value > rule.threshold:
                is_triggered = True
            elif rule.condition == 'below' and current_value < rule.threshold:
                is_triggered = True
            elif rule.condition == 'spike':
                p95 = summary.get('p95', 0)
                if p95 > 0 and current_value > p95 * rule.threshold:
                    is_triggered = True

            if is_triggered:
                alert = {
                    'name': rule.name,
                    'metric': rule.metric_name,
                    'value': current_value,
                    'threshold': rule.threshold,
                    'condition': rule.condition,
                    'timestamp': datetime.utcnow().isoformat(),
                }
                rule.last_triggered = now
                self.active_alerts.append(alert)
                self.alert_history.append(alert)
                triggered.append(alert)

                logger.warning(
                    f"Alert triggered: {rule.name} - "
                    f"{rule.metric_name}={current_value:.4f} "
                    f"({rule.condition} {rule.threshold})"
                )

        # Clean old active alerts (older than 1 hour)
        cutoff = now - 3600
        self.active_alerts = [
            a for a in self.active_alerts
            if time.mktime(
                datetime.fromisoformat(a['timestamp']).timetuple()
            ) > cutoff
        ]

        return triggered

    def get_active_alerts(self) -> List[Dict]:
        """Get currently active alerts."""
        return list(self.active_alerts)

    def get_alert_history(
        self,
        limit: int = 50
    ) -> List[Dict]:
        """Get recent alert history."""
        return list(self.alert_history)[-limit:]
