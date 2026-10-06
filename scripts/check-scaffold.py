#!/usr/bin/env python3
import sys
import os
import json

def detect_stack(repo_path):
    signals = {
        "google-adk": {
            "files": ["adk.yaml", "agent.py"],
            "dep_keywords": ["google-adk", "google-genai", "google.adk"],
            "language": "python",
            "framework": "google-adk",
            "scaffold_tool": "agents-cli"
        },
        "spring-boot": {
            "files": ["pom.xml", "build.gradle"],
            "dep_keywords": ["spring-boot-starter"],
            "language": "java",
            "framework": "spring-boot",
            "scaffold_tool": "spring init"
        },
        "fastapi": {
            "files": [],
            "dep_keywords": ["fastapi"],
            "language": "python",
            "framework": "fastapi",
            "scaffold_tool": "cookiecutter"
        },
        "django": {
            "files": ["manage.py"],
            "dep_keywords": ["django"],
            "language": "python",
            "framework": "django",
            "scaffold_tool": "django-admin"
        },
        "nextjs": {
            "files": [],
            "dep_keywords": ["\"next\""],
            "language": "typescript",
            "framework": "nextjs",
            "scaffold_tool": "create-next-app"
        },
        "react": {
            "files": [],
            "dep_keywords": ["\"react\""],
            "language": "typescript",
            "framework": "react",
            "scaffold_tool": "create-vite"
        },
        "angular": {
            "files": [],
            "dep_keywords": ["@angular/core"],
            "language": "typescript",
            "framework": "angular",
            "scaffold_tool": "ng new"
        }
    }
    
    detected = {
        "language": "unknown",
        "framework": "unknown",
        "scaffold_tool": "unknown"
    }
    
    # Check for direct file matches
    for stack_id, info in signals.items():
        for filename in info["files"]:
            if os.path.exists(os.path.join(repo_path, filename)):
                detected["language"] = info["language"]
                detected["framework"] = info["framework"]
                detected["scaffold_tool"] = info["scaffold_tool"]
                return detected
                
    # Parse dependency files
    requirements_path = os.path.join(repo_path, "requirements.txt")
    pyproject_path = os.path.join(repo_path, "pyproject.toml")
    package_json_path = os.path.join(repo_path, "package.json")
    pom_path = os.path.join(repo_path, "pom.xml")
    
    dep_content = ""
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8', errors='ignore') as f:
            dep_content += f.read()
    if os.path.exists(pyproject_path):
        with open(pyproject_path, 'r', encoding='utf-8', errors='ignore') as f:
            dep_content += f.read()
    if os.path.exists(package_json_path):
        with open(package_json_path, 'r', encoding='utf-8', errors='ignore') as f:
            dep_content += f.read()
    if os.path.exists(pom_path):
        with open(pom_path, 'r', encoding='utf-8', errors='ignore') as f:
            dep_content += f.read()
            
    if dep_content:
        for stack_id, info in signals.items():
            for keyword in info["dep_keywords"]:
                if keyword in dep_content:
                    detected["language"] = info["language"]
                    detected["framework"] = info["framework"]
                    detected["scaffold_tool"] = info["scaffold_tool"]
                    return detected
                    
    return detected

def check_repo_profile(repo_path):
    # Ignore administrative folders
    ignore_dirs = {".git", ".adlc5", ".cursor", "scripts", "docs", "third-party", "examples", "node_modules", "__pycache__"}
    ignore_files = {".gitignore", "README.md", "LICENSE", "AGENTS.md", "config.yaml", "config.example.yaml", "CLAUDE.md", "GEMINI.md"}
    
    code_files_found = []
    for root, dirs, files in os.walk(repo_path):
        # Prune ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            if file not in ignore_files and not file.startswith(".") and not file.endswith(".log"):
                code_files_found.append(os.path.join(root, file))
                
    if len(code_files_found) == 0:
        return "greenfield"
    else:
        return "brownfield"

def main():
    repo_path = "."
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
        
    stack = detect_stack(repo_path)
    profile = check_repo_profile(repo_path)
    
    output = {
        "repo_profile": profile,
        "detected_stack": stack,
        "scaffold_preferences": {
            "auto_detect": True,
            "layout_compliance": "enforced" if profile == "greenfield" else "standard"
        }
    }
    
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
