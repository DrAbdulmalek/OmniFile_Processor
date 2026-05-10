#!/usr/bin/env python3
"""
modify_hf_app.py — Gradio Compatibility Patcher for hf_app.py
=============================================================
Automatically fixes known Gradio compatibility issues in hf_app.py
so it runs correctly on Google Colab and HuggingFace Spaces.

Fixes applied:
1. multiple=True → file_count="multiple"  (Gradio 5.x+)
2. Remove deprecated 'fn=' from gr.Examples (Gradio 5.x+)
3. Remove 'height=NNN' from Dataframe components (Gradio 5.x+)
4. Force share=True for Colab, auto-detect for Spaces
5. Clean up double commas and malformed arguments

Usage:
    python scripts/modify_hf_app.py [--dry-run] [--file hf_app.py]

والله من وراء القصد
"""
import re
import os
import sys
import argparse


def patch_file(file_path: str, dry_run: bool = False) -> dict:
    """Apply all Gradio compatibility patches to hf_app.py."""
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    patches_applied = {}
    
    # ── Patch 1: multiple=True → file_count="multiple" ──
    pattern_multiple = re.compile(r'(\bgr\.File\([^)]*?)multiple\s*=\s*True([^)]*?\))', re.DOTALL)
    matches_multiple = pattern_multiple.findall(content)
    if matches_multiple:
        content = pattern_multiple.sub(
            lambda m: m.group(1) + 'file_count="multiple"' + m.group(2),
            content
        )
        patches_applied["multiple=True → file_count='multiple'"] = len(matches_multiple)
    
    # ── Patch 2: Remove 'fn=' from gr.Examples ──
    pattern_fn = re.compile(
        r'(gr\.Examples\([^)]*?\n[^)]*?)fn\s*=\s*\w+,\s*\n([^)]*?\))',
        re.DOTALL
    )
    matches_fn = pattern_fn.findall(content)
    if matches_fn:
        content = pattern_fn.sub(
            lambda m: m.group(1) + m.group(2),
            content
        )
        patches_applied["fn= removed from gr.Examples"] = len(matches_fn)
    
    # ── Patch 3: Remove 'height=NNN' from Dataframe ──
    # Only target gr.Dataframe, not gr.Gallery (height is valid for Gallery)
    pattern_height = re.compile(
        r'(gr\.Dataframe\([^)]*?),\s*height\s*=\s*\d+([^)]*?\))',
        re.DOTALL
    )
    matches_height = pattern_height.findall(content)
    if matches_height:
        content = pattern_height.sub(
            lambda m: m.group(1) + m.group(2),
            content
        )
        patches_applied["height= removed from Dataframe"] = len(matches_height)
    
    # ── Patch 4: Auto-detect share for Colab ──
    # Replace share=False with auto-detection
    if "share=False" in content:
        auto_share_code = """    # Auto-detect environment: share=True in Colab, False on HF Spaces
    _in_colab = os.environ.get("COLAB_RELEASE_TAG") is not None or os.environ.get("JPY_PARENT_PID") is not None
    _in_space = os.environ.get("SPACE_ID") is not None or os.environ.get("SPACE_AUTHOR_NAME") is not None
    _share = _in_colab or not _in_space

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=_share,"""
        
        # Find and replace the demo.launch section
        pattern_launch = re.compile(
            r'(demo\.launch\(\s*\n\s*server_name\s*=\s*"[^"]*",\s*\n\s*server_port\s*=\s*\d+,\s*\n)\s*share\s*=\s*False',
            re.DOTALL
        )
        if pattern_launch.search(content):
            content = pattern_launch.sub(auto_share_code, content)
            patches_applied["share=False → auto-detect"] = 1
    
    # ── Patch 5: Cleanup double commas ──
    content = re.sub(r',\s*,', ',', content)
    content = re.sub(r'\(\s*,', '(', content)
    content = re.sub(r',\s*\)', ')', content)
    
    # ── Report ──
    if content != original:
        if dry_run:
            print("DRY RUN — no changes written.\n")
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"PATCHED: {file_path}\n")
        
        print("Patches applied:")
        for patch, count in patches_applied.items():
            print(f"  ✅ {patch} ({count} occurrence(s))")
        
        if not patches_applied:
            print("  ℹ️  No patches needed — file is already compatible.")
    else:
        print(f"ℹ️  No changes needed — {file_path} is already compatible.")
    
    return patches_applied


def main():
    parser = argparse.ArgumentParser(description="Patch hf_app.py for Gradio compatibility")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--file", default="hf_app.py", help="Path to hf_app.py")
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"ERROR: {args.file} not found")
        sys.exit(1)
    
    patch_file(args.file, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
