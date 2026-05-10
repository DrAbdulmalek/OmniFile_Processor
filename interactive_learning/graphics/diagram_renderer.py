#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interactive_learning/graphics/diagram_renderer.py
==================================================

رسم المخططات الصندوقية والرسوم البيانية بشكل جميل ومنسق.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import uuid

import numpy as np
import svgwrite
from svgwrite import cm, mm


@dataclass
class FlowchartNode:
    """عقدة في مخطط التدفق."""
    id: str
    node_type: str  # start, process, decision, input, output, end
    text: str
    x: float = 0
    y: float = 0
    width: float = 150
    height: float = 80
    fill_color: str = "#e3f2fd"
    border_color: str = "#1565c0"
    text_color: str = "#333"
    connections: List[Dict] = None  # [{target_id, label, style}]
    
    def __post_init__(self):
        if self.connections is None:
            self.connections = []


@dataclass
class FlowchartEdge:
    """وصلة بين عقدتين."""
    source: str
    target: str
    label: str = ""
    style: str = "solid"  # solid, dashed, dotted
    color: str = "#666"


class FlowchartRenderer:
    """مصيّر مخططات التدفق."""
    
    # أشكال العقد
    SHAPES = {
        'start': 'ellipse',
        'end': 'ellipse',
        'process': 'rect',
        'decision': 'diamond',
        'input': 'parallelogram',
        'output': 'parallelogram',
        'subprocess': 'rect_with_stripe'
    }
    
    # الألوان الافتراضية
    COLORS = {
        'start': {'fill': '#c8e6c9', 'border': '#2e7d32', 'text': '#1b5e20'},
        'end': {'fill': '#ffcdd2', 'border': '#c62828', 'text': '#b71c1c'},
        'process': {'fill': '#e3f2fd', 'border': '#1565c0', 'text': '#0d47a1'},
        'decision': {'fill': '#fff3e0', 'border': '#ef6c00', 'text': '#e65100'},
        'input': {'fill': '#f3e5f5', 'border': '#7b1fa2', 'text': '#4a148c'},
        'output': {'fill': '#e0f2f1', 'border': '#00796b', 'text': '#004d40'}
    }
    
    def __init__(
        self,
        width: float = 800,
        height: float = 600,
        node_spacing: float = 50,
        layer_spacing: float = 100
    ):
        self.width = width
        self.height = height
        self.node_spacing = node_spacing
        self.layer_spacing = layer_spacing
        
        self.nodes: Dict[str, FlowchartNode] = {}
        self.edges: List[FlowchartEdge] = []
    
    def add_node(self, node: FlowchartNode):
        """إضافة عقدة."""
        self.nodes[node.id] = node
    
    def add_edge(self, edge: FlowchartEdge):
        """إضافة وصلة."""
        self.edges.append(edge)
        
        # إضافة للعقدة المصدر
        if edge.source in self.nodes:
            self.nodes[edge.source].connections.append({
                'target_id': edge.target,
                'label': edge.label,
                'style': edge.style
            })
    
    def auto_layout(self):
        """تخطيط تلقائي للعقد."""
        # خوارزمية تخطيط هرمي بسيطة
        # TODO: استخدام خوارزمية أكثر تطوراً
        
        # ترتيب الطبقات
        layers = self._calculate_layers()
        
        # وضع العقد
        for layer_idx, layer in enumerate(layers):
            y = 50 + layer_idx * (80 + self.layer_spacing)
            total_width = len(layer) * 150 + (len(layer) - 1) * self.node_spacing
            start_x = (self.width - total_width) / 2
            
            for node_idx, node_id in enumerate(layer):
                node = self.nodes[node_id]
                node.x = start_x + node_idx * (150 + self.node_spacing)
                node.y = y
    
    def _calculate_layers(self) -> List[List[str]]:
        """حساب الطبقات باستخدام BFS."""
        # العثور على البداية
        start_nodes = [
            nid for nid, n in self.nodes.items()
            if n.node_type == 'start'
        ]
        
        if not start_nodes:
            start_nodes = [list(self.nodes.keys())[0]]
        
        # BFS
        layers = []
        visited = set()
        queue = [(nid, 0) for nid in start_nodes]
        
        while queue:
            node_id, depth = queue.pop(0)
            
            if node_id in visited:
                continue
            
            visited.add(node_id)
            
            while len(layers) <= depth:
                layers.append([])
            
            layers[depth].append(node_id)
            
            # إضافة الأبناء
            for conn in self.nodes[node_id].connections:
                if conn['target_id'] not in visited:
                    queue.append((conn['target_id'], depth + 1))
        
        return layers
    
    def render(self, output_path: Optional[Path] = None) -> str:
        """
        تصيير المخطط كـ SVG.
        
        Returns:
            نص SVG
        """
        # التخطيط التلقائي إذا لم يتم تحديد مواقع
        if all(n.x == 0 and n.y == 0 for n in self.nodes.values()):
            self.auto_layout()
        
        # إنشاء SVG
        dwg = svgwrite.Drawing(
            str(output_path) if output_path else None,
            size=(self.width, self.height),
            profile='full'
        )
        
        # خلفية
        dwg.add(dwg.rect(
            insert=(0, 0),
            size=('100%', '100%'),
            fill='white'
        ))
        
        # رسم الوصلات أولاً (تحت العقد)
        for edge in self.edges:
            self._draw_edge(dwg, edge)
        
        # رسم العقد
        for node in self.nodes.values():
            self._draw_node(dwg, node)
        
        # الحفظ
        if output_path:
            dwg.save()
        
        return dwg.tostring()
    
    def _draw_node(self, dwg: svgwrite.Drawing, node: FlowchartNode):
        """رسم عقدة."""
        colors = self.COLORS.get(node.node_type, self.COLORS['process'])
        
        g = dwg.g(
            id=f"node_{node.id}",
            class_='flowchart-node',
            transform=f"translate({node.x}, {node.y})"
        )
        
        # الشكل
        shape = self.SHAPES.get(node.node_type, 'rect')
        
        if shape == 'ellipse':
            g.add(dwg.ellipse(
                center=(node.width / 2, node.height / 2),
                r=(node.width / 2 - 5, node.height / 2 - 5),
                fill=colors['fill'],
                stroke=colors['border'],
                stroke_width=2
            ))
        
        elif shape == 'rect':
            g.add(dwg.rect(
                insert=(5, 5),
                size=(node.width - 10, node.height - 10),
                rx=5, ry=5,
                fill=colors['fill'],
                stroke=colors['border'],
                stroke_width=2
            ))
        
        elif shape == 'diamond':
            # معين
            points = [
                (node.width / 2, 5),
                (node.width - 5, node.height / 2),
                (node.width / 2, node.height - 5),
                (5, node.height / 2)
            ]
            g.add(dwg.polygon(
                points=points,
                fill=colors['fill'],
                stroke=colors['border'],
                stroke_width=2
            ))
        
        elif shape == 'parallelogram':
            # متوازي أضلاع
            offset = 20
            points = [
                (offset, 5),
                (node.width - 5, 5),
                (node.width - offset, node.height - 5),
                (5, node.height - 5)
            ]
            g.add(dwg.polygon(
                points=points,
                fill=colors['fill'],
                stroke=colors['border'],
                stroke_width=2
            ))
        
        # النص
        # تقسيم النص لأسطر إذا طويل
        words = node.text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if len(test_line) * 8 < node.width - 20:  # تقريب عرض الحرف
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # رسم الأسطر
        line_height = 16
        total_text_height = len(lines) * line_height
        start_y = (node.height - total_text_height) / 2 + line_height
        
        for i, line in enumerate(lines):
            g.add(dwg.text(
                line,
                insert=(node.width / 2, start_y + i * line_height),
                text_anchor='middle',
                font_family='Segoe UI, Arial',
                font_size='14px',
                fill=colors['text']
            ))
        
        dwg.add(g)
    
    def _draw_edge(self, dwg: svgwrite.Drawing, edge: FlowchartEdge):
        """رسم وصلة."""
        source = self.nodes.get(edge.source)
        target = self.nodes.get(edge.target)
        
        if not source or not target:
            return
        
        # نقاط البداية والنهاية
        start = self._get_connection_point(source, target)
        end = self._get_connection_point(target, source)
        
        # منحنى بيزير
        mid_x = (start[0] + end[0]) / 2
        
        path = dwg.path(
            d=f"M {start[0]} {start[1]} "
              f"C {mid_x} {start[1]}, {mid_x} {end[1]}, {end[0]} {end[1]}",
            fill='none',
            stroke=edge.color,
            stroke_width=2,
            marker_end='url(#arrowhead)'
        )
        
        # تعريف السهم إذا لم يكن موجوداً
        if 'arrowhead' not in [d.get_id() for d in dwg.defs.elements]:
            marker = dwg.marker(
                insert=(9, 3),
                size=(10, 7),
                orient='auto',
                id='arrowhead'
            )
            marker.add(dwg.polygon(
                points=[(0, 0), (10, 3.5), (0, 7)],
                fill=edge.color
            ))
            dwg.defs.add(marker)
        
        dwg.add(path)
        
        # تسمية الوصلة
        if edge.label:
            mid_point = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            dwg.add(dwg.text(
                edge.label,
                insert=mid_point,
                text_anchor='middle',
                font_family='Segoe UI, Arial',
                font_size='12px',
                fill='#666',
                dy='-5'
            ))
    
    def _get_connection_point(
        self,
        from_node: FlowchartNode,
        to_node: FlowchartNode
    ) -> Tuple[float, float]:
        """حساب نقطة الاتصال بين عقدتين."""
        # مركز العقدة
        cx = from_node.x + from_node.width / 2
        cy = from_node.y + from_node.height / 2
        
        # اتجاه العقدة الهدف
        dx = (to_node.x + to_node.width / 2) - cx
        dy = (to_node.y + to_node.height / 2) - cy
        
        # تحديد الجانب
        if abs(dx) > abs(dy):
            # أفقي
            if dx > 0:
                return (from_node.x + from_node.width, cy)  # يمين
            else:
                return (from_node.x, cy)  # يسار
        else:
            # عمودي
            if dy > 0:
                return (cx, from_node.y + from_node.height)  # أسفل
            else:
                return (cx, from_node.y)  # أعلى
    
    def render_interactive_html(self, output_path: Path):
        """تصيير HTML تفاعلي مع SVG."""
        svg_content = self.render()
        
        html = f'''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>مخطط التدفق</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .flowchart-svg {{
            width: 100%;
            height: auto;
        }}
        
        .flowchart-node {{
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .flowchart-node:hover {{
            filter: brightness(1.1);
        }}
        
        .flowchart-node:hover rect,
        .flowchart-node:hover ellipse,
        .flowchart-node:hover polygon {{
            stroke-width: 3;
        }}
        
        .node-editor {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            display: none;
            z-index: 1000;
        }}
        
        .node-editor.visible {{
            display: block;
        }}
        
        .overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: none;
            z-index: 999;
        }}
        
        .overlay.visible {{
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>مخطط التدفق</h1>
        {svg_content}
    </div>
    
    <div class="overlay" id="overlay"></div>
    <div class="node-editor" id="nodeEditor">
        <h3>تعديل العقدة</h3>
        <input type="text" id="nodeText" style="width: 100%; padding: 8px; margin: 10px 0;">
        <button onclick="saveNode()">حفظ</button>
        <button onclick="closeEditor()">إلغاء</button>
    </div>
    
    <script>
        let currentNodeId = null;
        
        document.querySelectorAll('.flowchart-node').forEach(node => {{
            node.addEventListener('click', function() {{
                currentNodeId = this.id.replace('node_', '');
                const textElement = this.querySelector('text');
                document.getElementById('nodeText').value = textElement.textContent;
                document.getElementById('overlay').classList.add('visible');
                document.getElementById('nodeEditor').classList.add('visible');
            }});
        }});
        
        function saveNode() {{
            const newText = document.getElementById('nodeText').value;
            // إرسال للخادم
            fetch('/api/update-node', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{id: currentNodeId, text: newText}})
            }});
            closeEditor();
        }}
        
        function closeEditor() {{
            document.getElementById('overlay').classList.remove('visible');
            document.getElementById('nodeEditor').classList.remove('visible');
        }}
    </script>
</body>
</html>
        '''
        
        output_path.write_text(html, encoding='utf-8')
        return output_path


class ChartRenderer:
    """مصيّر المخططات البيانية."""
    
    CHART_TYPES = ['bar', 'line', 'pie', 'doughnut', 'radar']
    
    def __init__(self, width: int = 600, height: int = 400):
        self.width = width
        self.height = height
    
    def render_bar_chart(
        self,
        data: List[Dict],
        title: str = "",
        x_label: str = "",
        y_label: str = ""
    ) -> str:
        """
        تصيير مخطط شريطي.
        
        Args:
            data: [{'label': str, 'value': float, 'color': str}]
        """
        # إنشاء SVG
        dwg = svgwrite.Drawing(size=(self.width, self.height))
        
        # هوامش
        margin = {'top': 60, 'right': 40, 'bottom': 80, 'left': 80}
        chart_width = self.width - margin['left'] - margin['right']
        chart_height = self.height - margin['top'] - margin['bottom']
        
        # العنوان
        if title:
            dwg.add(dwg.text(
                title,
                insert=(self.width / 2, 30),
                text_anchor='middle',
                font_family='Segoe UI, Arial',
                font_size='18px',
                font_weight='bold',
                fill='#333'
            ))
        
        # العثور على القيمة القصوى
        max_value = max(d['value'] for d in data) if data else 1
        max_value = max(max_value * 1.1, 1)  # هامش علوي
        
        # رسم المحاور
        # Y axis
        dwg.add(dwg.line(
            start=(margin['left'], margin['top']),
            end=(margin['left'], self.height - margin['bottom']),
            stroke='#333',
            stroke_width=2
        ))
        
        # X axis
        dwg.add(dwg.line(
            start=(margin['left'], self.height - margin['bottom']),
            end=(self.width - margin['right'], self.height - margin['bottom']),
            stroke='#333',
            stroke_width=2
        ))
        
        # تسميات Y
        num_ticks = 5
        for i in range(num_ticks + 1):
            value = max_value * i / num_ticks
            y = self.height - margin['bottom'] - (chart_height * i / num_ticks)
            
            dwg.add(dwg.text(
                f"{value:.0f}",
                insert=(margin['left'] - 10, y + 5),
                text_anchor='end',
                font_family='Segoe UI, Arial',
                font_size='12px',
                fill='#666'
            ))
            
            # خط شبكة
            if i > 0:
                dwg.add(dwg.line(
                    start=(margin['left'], y),
                    end=(self.width - margin['right'], y),
                    stroke='#eee',
                    stroke_width=1
                ))
        
        # رسم الأعمدة
        bar_width = chart_width / len(data) * 0.7
        bar_spacing = chart_width / len(data) * 0.3
        
        for i, item in enumerate(data):
            x = margin['left'] + i * (bar_width + bar_spacing) + bar_spacing / 2
            bar_height = (item['value'] / max_value) * chart_height
            y = self.height - margin['bottom'] - bar_height
            
            # العمود
            color = item.get('color', '#1976d2')
            dwg.add(dwg.rect(
                insert=(x, y),
                size=(bar_width, bar_height),
                fill=color,
                rx=3, ry=3
            ))
            
            # القيمة فوق العمود
            dwg.add(dwg.text(
                f"{item['value']:.0f}",
                insert=(x + bar_width / 2, y - 5),
                text_anchor='middle',
                font_family='Segoe UI, Arial',
                font_size='12px',
                fill='#333'
            ))
            
            # التسمية
            label = item.get('label', f"Item {i+1}")
            dwg.add(dwg.text(
                label,
                insert=(x + bar_width / 2, self.height - margin['bottom'] + 20),
                text_anchor='middle',
                font_family='Segoe UI, Arial',
                font_size='12px',
                fill='#666',
                transform=f"rotate(45, {x + bar_width / 2}, {self.height - margin['bottom'] + 20})"
            ))
        
        # تسميات المحاور
        if y_label:
            dwg.add(dwg.text(
                y_label,
                insert=(20, self.height / 2),
                text_anchor='middle',
                font_family='Segoe UI, Arial',
                font_size='14px',
                fill='#333',
                transform=f"rotate(-90, 20, {self.height / 2})"
            ))
        
        if x_label:
            dwg.add(dwg.text(
                x_label,
                insert=(self.width / 2, self.height - 20),
                text_anchor='middle',
                font_family='Segoe UI, Arial',
                font_size='14px',
                fill='#333'
            ))
        
        return dwg.tostring()
    
    def render_pie_chart(
        self,
        data: List[Dict],
        title: str = ""
    ) -> str:
        """تصيير مخطط دائري."""
        dwg = svgwrite.Drawing(size=(self.width, self.height))
        
        center = (self.width / 2, self.height / 2)
        radius = min(self.width, self.height) / 3
        
        # العنوان
        if title:
            dwg.add(dwg.text(
                title,
                insert=(center[0], 30),
                text_anchor='middle',
                font_family='Segoe UI, Arial',
                font_size='18px',
                font_weight='bold',
                fill='#333'
            ))
        
        # حساب الزوايا
        total = sum(d['value'] for d in data)
        start_angle = 0
        
        for i, item in enumerate(data):
            angle = (item['value'] / total) * 360
            end_angle = start_angle + angle
            
            # رسم القطاع
            color = item.get('color', self._get_color(i))
            path = self._arc_path(center, radius, start_angle, end_angle)
            
            dwg.add(dwg.path(
                d=path,
                fill=color,
                stroke='white',
                stroke_width=2
            ))
            
            # التسمية
            mid_angle = (start_angle + end_angle) / 2
            label_radius = radius * 0.7
            label_x = center[0] + label_radius * np.cos(np.radians(mid_angle))
            label_y = center[1] + label_radius * np.sin(np.radians(mid_angle))
            
            percentage = (item['value'] / total) * 100
            dwg.add(dwg.text(
                f"{percentage:.1f}%",
                insert=(label_x, label_y),
                text_anchor='middle',
                font_family='Segoe UI, Arial',
                font_size='14px',
                fill='white',
                font_weight='bold'
            ))
            
            # مفتاح
            legend_y = 80 + i * 25
            dwg.add(dwg.rect(
                insert=(self.width - 150, legend_y - 10),
                size=(15, 15),
                fill=color,
                rx=3, ry=3
            ))
            dwg.add(dwg.text(
                f"{item.get('label', '')} ({item['value']:.0f})",
                insert=(self.width - 130, legend_y + 2),
                font_family='Segoe UI, Arial',
                font_size='12px',
                fill='#333'
            ))
            
            start_angle = end_angle
        
        return dwg.tostring()
    
    def _arc_path(
        self,
        center: Tuple[float, float],
        radius: float,
        start_angle: float,
        end_angle: float
    ) -> str:
        """إنشاء مسار قوس."""
        start = (
            center[0] + radius * np.cos(np.radians(start_angle)),
            center[1] + radius * np.sin(np.radians(start_angle))
        )
        end = (
            center[0] + radius * np.cos(np.radians(end_angle)),
            center[1] + radius * np.sin(np.radians(end_angle))
        )
        
        large_arc = 1 if (end_angle - start_angle) > 180 else 0
        
        return (
            f"M {center[0]} {center[1]} "
            f"L {start[0]} {start[1]} "
            f"A {radius} {radius} 0 {large_arc} 1 {end[0]} {end[1]} "
            f"Z"
        )
    
    def _get_color(self, index: int) -> str:
        """لون من لوحة الألوان."""
        colors = [
            '#1976d2', '#388e3c', '#f57c00', '#7b1fa2',
            '#00796b', '#c62828', '#5d4037', '#455a64'
        ]
        return colors[index % len(colors)]
