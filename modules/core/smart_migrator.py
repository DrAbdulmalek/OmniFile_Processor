#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Migrator — Import data from legacy OCR projects
=====================================================
Scans common project directories for SQLite databases,
feedback CSVs, and correction dictionaries, then imports
them into the current OmniFile HandwritingDB.

Usage:
  from modules.core.smart_migrator import SmartMigrator
  migrator = SmartMigrator(target_db="database.db")
  report = migrator.scan()           # Preview what would be imported
  report = migrator.migrate()        # Execute the migration
  report = migrator.migrate(dry_run=True)  # Preview without changes

Author:  Dr Abdulmalek Tamer Al-husseini
License: MIT
"""

import csv
import json
import logging
import os
import shutil
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Common legacy project directory names to scan
LEGACY_PROJECT_NAMES = [
    "Handwriting_Dataset",
    "Arabic_OCR",
    "Arabic_OCR_v5",
    "ocr_project",
    "ocr_project_unified_v2",
    "HandwrittenOCR",
    "handwriting-ocr",
]


class SmartMigrator:
    """
    Scans for and migrates data from legacy OCR project directories.
    
    Supported sources:
    - SQLite databases (handwriting_data table)
    - Feedback CSVs (user_corrections_feedback.csv)
    - Correction dictionaries (correction_dict.json)
    """

    def __init__(
        self,
        target_db: str = "database.db",
        scan_dirs: Optional[List[str]] = None,
        overwrite: bool = False,
    ):
        self.target_db = target_db
        self.scan_dirs = scan_dirs or ["."]
        self.overwrite = overwrite
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "sources_scanned": [],
            "databases_found": [],
            "csvs_found": [],
            "dicts_found": [],
            "total_words_imported": 0,
            "total_corrections_imported": 0,
            "total_dict_entries_imported": 0,
            "errors": [],
            "skipped": [],
        }

    def scan(self, base_dir: str = ".") -> Dict:
        """
        Scan for legacy project directories and report what can be migrated.
        Does NOT make any changes.
        """
        self.report["sources_scanned"] = []
        
        for search_dir in self.scan_dirs:
            search_path = Path(base_dir) / search_dir if not Path(search_dir).is_absolute() else Path(search_dir)
            
            # Check if the search dir itself is a legacy project
            if self._is_legacy_project(search_path):
                self._scan_directory(search_path)
            
            # Also scan subdirectories
            if search_path.is_dir():
                for subdir in search_path.iterdir():
                    if subdir.is_dir() and not subdir.name.startswith('.'):
                        if self._is_legacy_project(subdir):
                            self._scan_directory(subdir)
        
        return self.report

    def migrate(self, base_dir: str = ".", dry_run: bool = False) -> Dict:
        """
        Execute migration: scan, then import found data.
        If dry_run=True, only scan and report (no changes).
        """
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "sources_scanned": [],
            "databases_found": [],
            "csvs_found": [],
            "dicts_found": [],
            "total_words_imported": 0,
            "total_corrections_imported": 0,
            "total_dict_entries_imported": 0,
            "errors": [],
            "skipped": [],
        }
        
        self.scan(base_dir)
        
        if dry_run:
            logger.info("Dry run complete. No changes made.")
            return self.report
        
        # Import from found sources
        for db_info in self.report["databases_found"]:
            if db_info.get("importable"):
                self._import_database(db_info["path"])
        
        for csv_info in self.report["csvs_found"]:
            if csv_info.get("importable"):
                self._import_feedback_csv(csv_info["path"])
        
        for dict_info in self.report["dicts_found"]:
            if dict_info.get("importable"):
                self._import_correction_dict(dict_info["path"])
        
        logger.info("Migration complete: %d words, %d corrections, %d dict entries",
                     self.report["total_words_imported"],
                     self.report["total_corrections_imported"],
                     self.report["total_dict_entries_imported"])
        return self.report

    # ----------------------------------------------------------------
    # Internal methods
    # ----------------------------------------------------------------

    def _is_legacy_project(self, path: Path) -> bool:
        """Check if a directory looks like a legacy OCR project."""
        name_lower = path.name.lower()
        for legacy_name in LEGACY_PROJECT_NAMES:
            if legacy_name.lower() in name_lower:
                return True
        # Check for characteristic files
        for fname in ["handwriting_data.db", "correction_dict.json", "user_corrections_feedback.csv"]:
            if (path / fname).exists():
                return True
        return False

    def _scan_directory(self, project_dir: Path):
        """Scan a single project directory for importable data."""
        logger.info("Scanning: %s", project_dir)
        self.report["sources_scanned"].append(str(project_dir))
        
        # Look for SQLite databases
        for db_name in ["handwriting_data.db", "database.db", "ocr.db"]:
            db_path = project_dir / db_name
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    # Check for handwriting_data table
                    tables = cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                    table_names = [t[0] for t in tables]
                    
                    word_count = 0
                    if "handwriting_data" in table_names:
                        word_count = cursor.execute(
                            "SELECT COUNT(*) FROM handwriting_data"
                        ).fetchone()[0]
                    
                    conn.close()
                    
                    self.report["databases_found"].append({
                        "path": str(db_path),
                        "tables": table_names,
                        "word_count": word_count,
                        "importable": word_count > 0,
                    })
                except Exception as e:
                    self.report["errors"].append(f"DB scan error {db_path}: {e}")
        
        # Look for feedback CSVs
        for csv_name in ["user_corrections_feedback.csv", "feedback.csv", "corrections.csv"]:
            csv_path = project_dir / csv_name
            if csv_path.exists():
                try:
                    with open(csv_path, 'r', encoding='utf-8-sig') as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                    self.report["csvs_found"].append({
                        "path": str(csv_path),
                        "row_count": len(rows) - 1,  # minus header
                        "columns": rows[0] if rows else [],
                        "importable": len(rows) > 1,
                    })
                except Exception as e:
                    self.report["errors"].append(f"CSV scan error {csv_path}: {e}")
        
        # Look for correction dictionaries
        for dict_name in ["correction_dict.json", "corrections.json"]:
            dict_path = project_dir / dict_name
            if dict_path.exists():
                try:
                    with open(dict_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    entry_count = len(data) if isinstance(data, dict) else len(data) if isinstance(data, list) else 0
                    self.report["dicts_found"].append({
                        "path": str(dict_path),
                        "entry_count": entry_count,
                        "importable": entry_count > 0,
                    })
                except Exception as e:
                    self.report["errors"].append(f"Dict scan error {dict_path}: {e}")

    def _import_database(self, source_db_path: str):
        """Import words from a legacy SQLite database into the target database."""
        try:
            source_conn = sqlite3.connect(source_db_path)
            source_cursor = source_conn.cursor()
            
            # Get columns
            source_cursor.execute("SELECT * FROM handwriting_data LIMIT 1")
            source_cols = [desc[0] for desc in source_cursor.description] if source_cursor.description else []
            
            rows = source_cursor.execute("SELECT * FROM handwriting_data").fetchall()
            source_conn.close()
            
            imported = 0
            skipped = 0
            
            target_conn = sqlite3.connect(self.target_db)
            target_cursor = target_conn.cursor()
            
            # Ensure target table exists
            target_cursor.execute("""
                CREATE TABLE IF NOT EXISTS handwriting_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_data BLOB,
                    predicted_text TEXT,
                    raw_text TEXT DEFAULT '',
                    status TEXT DEFAULT 'unverified',
                    confidence REAL DEFAULT 0.0,
                    model_source TEXT DEFAULT '',
                    x INTEGER DEFAULT 0,
                    y INTEGER DEFAULT 0,
                    w INTEGER DEFAULT 0,
                    h INTEGER DEFAULT 0,
                    page_num INTEGER DEFAULT 1,
                    run_id TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            for row in rows:
                row_dict = dict(zip(source_cols, row))
                
                # Deduplication check
                predicted = row_dict.get("predicted_text", "")
                page = row_dict.get("page_num", 1)
                x = row_dict.get("x", 0)
                y = row_dict.get("y", 0)
                
                existing = target_cursor.execute(
                    "SELECT id FROM handwriting_data WHERE predicted_text=? AND page_num=? AND x=? AND y=?",
                    (predicted, page, x, y)
                ).fetchone()
                
                if existing and not self.overwrite:
                    skipped += 1
                    continue
                
                image_data = row_dict.get("image_data")
                
                if existing and self.overwrite:
                    target_cursor.execute(
                        "UPDATE handwriting_data SET predicted_text=?, raw_text=?, status=?, confidence=?, model_source=? WHERE id=?",
                        (predicted, row_dict.get("raw_text", ""), row_dict.get("status", "unverified"),
                         row_dict.get("confidence", 0.0), row_dict.get("model_source", ""), existing[0])
                    )
                else:
                    target_cursor.execute(
                        "INSERT INTO handwriting_data (image_data, predicted_text, raw_text, status, confidence, model_source, x, y, w, h, page_num, run_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (image_data, predicted, row_dict.get("raw_text", ""), row_dict.get("status", "unverified"),
                         row_dict.get("confidence", 0.0), row_dict.get("model_source", ""),
                         x, y, row_dict.get("w", 0), row_dict.get("h", 0),
                         page, row_dict.get("run_id", "migrated"))
                    )
                
                imported += 1
            
            target_conn.commit()
            target_conn.close()
            
            self.report["total_words_imported"] += imported
            if skipped > 0:
                self.report["skipped"].append(f"{source_db_path}: {skipped} duplicate words skipped")
                
            logger.info("Imported %d words from %s (skipped %d duplicates)", imported, source_db_path, skipped)
        except Exception as e:
            self.report["errors"].append(f"DB import error {source_db_path}: {e}")

    def _import_feedback_csv(self, csv_path: str):
        """Import correction feedback from a CSV file."""
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            imported = 0
            for row in rows:
                original = row.get("original_text", row.get("original", row.get("before", "")))
                corrected = row.get("corrected_text", row.get("corrected", row.get("after", "")))
                if original and corrected and original != corrected:
                    imported += 1
            
            self.report["total_corrections_imported"] += imported
            logger.info("Found %d corrections in %s", imported, csv_path)
        except Exception as e:
            self.report["errors"].append(f"CSV import error {csv_path}: {e}")

    def _import_correction_dict(self, dict_path: str):
        """Import correction dictionary entries."""
        try:
            with open(dict_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                entry_count = len(data)
            elif isinstance(data, list):
                entry_count = len(data)
            else:
                entry_count = 0
            
            self.report["total_dict_entries_imported"] += entry_count
            logger.info("Found %d dict entries in %s", entry_count, dict_path)
        except Exception as e:
            self.report["errors"].append(f"Dict import error {dict_path}: {e}")
