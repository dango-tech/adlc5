#!/usr/bin/env python3
import sys
import os
import json
import glob
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)
from lib.adlc5_paths import load_state  # noqa: E402

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def main():
    feature = ""
    if "--feature" in sys.argv:
        idx = sys.argv.index("--feature")
        if idx + 1 < len(sys.argv):
            feature = sys.argv[idx + 1]
            
    if not feature:
        # Auto-detect from .adlc5 directories
        adlc5_dirs = glob.glob(".adlc5/*")
        adlc5_dirs = [os.path.basename(d) for d in adlc5_dirs if os.path.isdir(d) and os.path.basename(d) != "workspace"]
        if adlc5_dirs:
            feature = adlc5_dirs[0]
            
    if not feature:
        print("ERROR: No active feature folder found under .adlc5/ or passed via --feature", file=sys.stderr)
        sys.exit(1)
        
    feature_dir = os.path.join(".adlc5", feature)
    state_path = os.path.join(feature_dir, "state.json")
    state = load_json(state_path)
    resolved_state = load_state(Path(".").resolve(), feature) or state
    
    current_stage = resolved_state.get("current_stage", "specify")
    current_step = resolved_state.get("current_step") or resolved_state.get("current_phase", "—")
    last_compacted = state.get("memory", {}).get("last_compacted") or "none"
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    index_content = f"""# ADLC5 Working Memory — {feature}

**Updated:** {timestamp}  
**Current stage:** {current_stage}  
**Current step:** {current_step}
**Last compacted:** {last_compacted}

## Retrieval rule

Read this file first. Load only artifacts listed below for active work. Do not paste full code specs into orchestrator chat when a context pack exists.

## Artifact index

| Path | Phase | Summary (≤120 chars) |
|------|-------|------------------------|
"""
    
    # Locate all artifacts in .adlc5/{feature}
    artifacts = []
    
    # Design files
    design_files = sorted(glob.glob(os.path.join(feature_dir, "design", "*.md")))
    for df in design_files:
        filename = os.path.basename(df)
        phase = "—"
        summary = ""
        if "1a" in filename or "discovery" in filename:
            phase = "plan-4-design-discovery"
            summary = "Design Discovery - Problem framing & core architecture decisions"
        elif "1b" in filename or "contracts" in filename:
            phase = "plan-5-design-contracts"
            summary = "API & Integration Contracts - Interfaces, endpoints & signatures"
        elif "1c" in filename or "operations" in filename:
            phase = "plan-6-design-operations"
            summary = "Security, Performance & Ops - Scale, monitoring & rollout plan"
        artifacts.append((df, phase, summary))
        
    # User stories
    user_stories = glob.glob(os.path.join(feature_dir, "tasks", "stories.md"))
    user_stories += glob.glob(os.path.join(feature_dir, "user_stories.md"))
    for us in user_stories:
        artifacts.append((us, "tasks-1-stories", "Technical user stories & decomposition"))
        
    # Code specs
    code_specs = sorted(glob.glob(os.path.join(feature_dir, "tasks", "code-spec", "*.md")))
    code_specs += sorted(glob.glob(os.path.join(feature_dir, "code_specs", "*.md")))
    for cs in code_specs:
        story_id = os.path.basename(cs).replace("-spec.md", "").upper()
        artifacts.append((cs, "tasks-2-code-spec", f"Code spec plan for story {story_id}"))
        
    # Context packs
    context_packs = sorted(glob.glob(os.path.join(feature_dir, "memory", "context-packs", "*.md")))
    for cp in context_packs:
        story_id = os.path.basename(cp).replace("story-", "").replace(".md", "").upper()
        artifacts.append((cp, "tasks-2-code-spec", f"Context pack for story {story_id}"))
        
    # Add artifacts to table
    for path, phase, summary in artifacts:
        index_content += f"| {path} | {phase} | {summary} |\n"
        
    index_content += """
## Summaries

| Summary | Path |
|---------|------|
"""
    
    # Summaries index
    summaries = [
        ("Specify", "memory/summaries/specify.md"),
        ("Plan", "memory/summaries/plan.md"),
        ("Tasks", "memory/summaries/tasks.md"),
        ("Implement", "memory/summaries/implement.md"),
    ]
    
    for s_label, s_path in summaries:
        index_content += f"| {s_label} | {s_path} |\n"
        
    index_content += """
## Context packs (Implement / Verify)

| Story ID | Pack path |
|----------|-----------|
"""
    
    # Add context packs list
    packs_found = False
    for cp in context_packs:
        story_id = os.path.basename(cp).replace("story-", "").replace(".md", "").upper()
        index_content += f"| {story_id} | memory/context-packs/story-{story_id.lower()}.md |\n"
        packs_found = True
        
    if not packs_found:
        index_content += "| — | — |\n"
        
    # Create directories if missing
    memory_dir = os.path.join(feature_dir, "memory")
    os.makedirs(os.path.join(memory_dir, "summaries"), exist_ok=True)
    os.makedirs(os.path.join(memory_dir, "context-packs"), exist_ok=True)
    
    index_path = os.path.join(memory_dir, "INDEX.md")
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
        
    # Update state.json memory timestamps
    if state:
        state["memory"] = state.get("memory", {})
        state["memory"]["index_path"] = index_path
        state["memory"]["last_compacted"] = current_stage
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
            
    print(f"Working memory INDEX compacted and updated successfully at {index_path}!")

if __name__ == "__main__":
    main()
