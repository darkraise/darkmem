# Graph Richness: 18 Edge Types, Type Resolution, Community Detection

## Goal

Bring darkmem's code graph from 4 edge types to GitNexus's full 18, adding class hierarchies, type-aware resolution, framework detection, community clustering, and execution flow analysis.

## Implementation: 3 sequential sub-projects

See plan at `plans/tingly-crunching-giraffe.md` for full details.

### Sub-project A: Extraction & Edge Types (10 new edges)
EXTENDS, IMPLEMENTS, HAS_METHOD, HAS_PROPERTY, HANDLES_ROUTE, HANDLES_TOOL, QUERIES, FETCHES + new node types (Property, Route, Tool, Model)

### Sub-project B: Type Environment & Resolution (3 new edges)  
ACCESSES, METHOD_OVERRIDES, METHOD_IMPLEMENTS + TypeEnvironment + HeritageResolver + enhanced call resolution

### Sub-project C: Community Detection & Enhanced Impact (3 new edges)
MEMBER_OF, STEP_IN_PROCESS, ENTRY_POINT_OF + Leiden clustering + process tracing + depth-stratified blast radius with risk rating
