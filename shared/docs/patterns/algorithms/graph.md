---
type: Algorithm Decision
title: Graph algorithms decision table
description: Select BFS/DFS/Dijkstra/Bellman-Ford/MST/flow from graph problem class.
tags: [clrs, algorithms]
status: stable
scope: algorithmic
requirements_tags: [graph, routing, dependencies]
complexity_notes: Depends on weighted/unweighted and negative edges
skill_invoke: "@algorithm-advisor"
sources:
  - id: kb-clrs
    resource: ../knowledge-base/05-algorithms-clrs.md
    title: ADLC5 KB Part V — CLRS
generated: { by: "process:adlc5-okf-seed", at: "2026-08-09T06:50:00Z" }
---

## Decision table

| Problem | Algorithm | When |
|---------|-----------|------|
| Unweighted shortest path | BFS | Fewest edges |
| Cycle / topo / SCC | DFS | Dependencies, compile order |
| MST | Kruskal or Prim | Sparse vs dense |
| SSSP, non-negative | Dijkstra | **No negative edges** |
| SSSP, negative weights | Bellman-Ford | Detect negative cycle |
| All-pairs | Floyd-Warshall | Dense, small V |
| Max flow / matching | Ford-Fulkerson family | Network capacity |

## Representation

Adjacency list for sparse graphs; matrix for dense or all-pairs.

## Links

- [KB Part V §V.6](../knowledge-base/05-algorithms-clrs.md)
