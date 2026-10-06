# Algorithm Advisory — [use case]

**Date:** [YYYY-MM-DD]  
**ADLC5 stage:** Engineer  
**Status:** advisory | N/A

---

## Scale NFRs

- n ≈ [typical / peak]
- Latency: [target]
- Memory: [budget]

---

## Recommendation

| Algorithm / DS | Time | Space | Notes |
|----------------|------|-------|-------|
| Binary search on sorted index | O(log n) | O(1) | Requires sorted maintenance on write |

---

## Alternatives rejected

| Option | Why not |
|--------|---------|
| Linear scan | n > 10⁵ at peak |

---

## Expected n justification

[Source: PRD / metrics / labeled assumption]

---

## Implementation notes

- **Layer placement:** use case policy; sorted index in adapter
- **Platform:** stdlib `bisect` / DB index

---

## Complexity review flag

- [ ] Hot path → schedule S3c during Implement review
