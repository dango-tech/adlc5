#!/usr/bin/env python3
import sys
import os
import re
import json
from datetime import datetime, timezone

def analyze_clarity(file_path):
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 1. Completeness (30%)
    # Look for key headings/keywords
    completeness_score = 0
    has_functional = re.search(r'(#+.*functional|functional requirements)', content, re.IGNORECASE) is not None
    has_ac = re.search(r'(#+.*acceptance criteria|acceptance criteria)', content, re.IGNORECASE) is not None
    has_nfr = re.search(r'(#+.*non-functional|#+.*nfr|non-functional requirements|scale nfrs)', content, re.IGNORECASE) is not None
    
    sections_found = []
    if has_functional:
        completeness_score += 10
        sections_found.append("Functional Requirements")
    if has_ac:
        completeness_score += 10
        sections_found.append("Acceptance Criteria")
    if has_nfr:
        completeness_score += 10
        sections_found.append("Non-functional Requirements (NFRs)")
        
    # 2. Confirmed vs Assumed (25%)
    # Scan for [ASSUMPTION] or (ASSUMPTION) or similar tags
    assumption_tags = re.findall(r'\[ASSUMPTION\]|\(ASSUMPTION\)|ASSUMPTION:', content, re.IGNORECASE)
    assumption_count = len(assumption_tags)
    
    # 25 points if 0 assumptions; subtract 5 points per assumption down to 0
    assumed_score = max(0, 25 - (assumption_count * 5))
    
    # 3. Specificity (30%)
    # Scan for vague terms that lack quantitative precision
    vague_words = ['fast', 'scalable', 'flexible', 'user-friendly', 'efficient', 'optimized', 'robust', 'performant']
    vague_violations = []
    for word in vague_words:
        # Find occurrences and see if they are near a digit
        for match in re.finditer(r'\b' + word + r'\b', content, re.IGNORECASE):
            start = max(0, match.start() - 30)
            end = min(len(content), match.end() + 30)
            context = content[start:end]
            if not re.search(r'\d', context):
                vague_violations.append(f"Vague term '{word}' found without quantitative bounds")
                
    # 30 points max; subtract 3 points per unquantified vague term down to 0
    specificity_score = max(0, 30 - (len(vague_violations) * 3))
    
    # 4. Testability (15%)
    # Check for test-supporting signals: status codes, precise parameters, schemas, example JSON/blocks
    testability_score = 0
    has_status_codes = re.search(r'\b[1-5]\d\d\b', content) is not None
    has_examples = re.search(r'```(json|yaml|xml|yml)', content, re.IGNORECASE) is not None or "example" in content.lower()
    has_validation = re.search(r'validation|regex|constraint|regex|type', content, re.IGNORECASE) is not None
    
    if has_status_codes:
        testability_score += 5
    if has_examples:
        testability_score += 5
    if has_validation:
        testability_score += 5
        
    overall_score = completeness_score + assumed_score + specificity_score + testability_score
    
    return {
        "score": int(overall_score),
        "open_items": assumption_count + int(len(vague_violations) / 2),
        "assumptions": assumption_count,
        "completeness_breakdown": {
            "score": completeness_score,
            "max": 30,
            "sections_found": sections_found
        },
        "assumptions_breakdown": {
            "score": assumed_score,
            "max": 25,
            "count": assumption_count
        },
        "specificity_breakdown": {
            "score": specificity_score,
            "max": 30,
            "violations_count": len(vague_violations),
            "top_violations": vague_violations[:5]
        },
        "testability_breakdown": {
            "score": testability_score,
            "max": 15,
            "signals": {
                "status_codes": has_status_codes,
                "examples": has_examples,
                "validation_rules": has_validation
            }
        },
        "scored_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: ./scripts/clarity-score.py <file_path> [--step-id ID]", file=sys.stderr)
        sys.exit(1)
        
    file_path = sys.argv[1]
    step_id = "general"
    if "--step-id" in sys.argv:
        idx = sys.argv.index("--step-id")
        if idx + 1 < len(sys.argv):
            step_id = sys.argv[idx + 1]
            
    result = analyze_clarity(file_path)
    
    # Output JSON matching the adlc5 clarity sub-schema
    output = {
        "step_id": step_id,
        "score": result["score"],
        "open_items": result["open_items"],
        "assumptions": result["assumptions"],
        "scored_at": result["scored_at"],
        "detailed_report": result
    }
    
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
