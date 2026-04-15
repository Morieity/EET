# Context Management Step-1: Paper Evidence to Algorithm Modules

## Scope

This document records step-1 deliverables:
1. Related paper evidence checks.
2. Core algorithm extraction.
3. Standalone algorithm modules added in application layer for later wiring.

This step does not modify runtime orchestration in chat flow yet.

## Code Reasonability Checks Before Modifications

Checked code paths before adding modules:
- `Backend/Application/UseCases/ChatUseCase.py`: current retrieval, context merge, prompt build sequence.
- `Backend/Web/app_factory.py`: dependency injection point for future Context Manager wiring.
- `Backend/Infrastructure/vectorstore/ChromaVectorStoreRepository.py`: score-bearing retrieval output contract.
- `Backend/Infrastructure/graphstore/NetworkXGraphRepository.py`: graph path data contract for pruning.

Reasoning:
- The project follows a clean split: Application (orchestration/contracts) vs Infrastructure (adapters).
- Therefore algorithm modules are placed in `Backend/Application/ContextManagement` as pure logic building blocks.
- This keeps step-1 low risk and avoids premature runtime coupling.

## Evidence Sufficiency Checks

External verification was done against arXiv search/abs pages for the key papers below.

| Evidence Key | Paper | Verified Source | Core Algorithm Signal |
|---|---|---|---|
| `long_context_vs_rag_2024` | Long Context vs. RAG for LLMs: An Evaluation and Revisits | https://arxiv.org/abs/2501.01880 | Budget and context-organization trade-offs |
| `long_context_llms_meet_rag_2024` | Long-Context LLMs Meet RAG | https://arxiv.org/abs/2410.05983 | Retrieval reordering and hard-negative handling |
| `retrieval_head_2024` | Retrieval Head Mechanistically Explains Long-Context Factuality | https://arxiv.org/abs/2404.15574 | Query-at-tail positioning |
| `longllmlingua_2023_2024` | LongLLMLingua | https://arxiv.org/abs/2310.06839 | Query-aware compression |
| `llmlingua2_2024` | LLMLingua-2 | https://arxiv.org/abs/2403.12968 | Task-agnostic prompt compression |
| `graphrag_local_to_global_2024` | From Local to Global: A Graph RAG Approach to Query-Focused Summarization | https://arxiv.org/abs/2404.16130 | Graph local-global context fusion |
| `pathrag_2025` | PathRAG | https://arxiv.org/abs/2502.14902 | Relational path pruning |
| `memagent_2025` | MemAgent | https://arxiv.org/abs/2507.02259 | Hierarchical conversation memory |

## Extracted Algorithm Modules (Application Layer)

### Package layout

`Backend/Application/ContextManagement/`

- `AlgorithmEvidence.py`
  - Paper registry and algorithm-to-evidence mapping.
- `ContextTypes.py`
  - Shared typed dicts for scored docs, graph paths, rounds, and messages.
- `AlgorithmRegistry.py`
  - Registry for module discovery in later integration steps.

`Backend/Application/ContextManagement/Algorithms/`

- `RetrievalReorderingAlgorithm.py`
  - Alternating head-tail ranking for high-relevance chunks.
- `MMRDeduplicationAlgorithm.py`
  - MMR-style selection with exact dedup and token-overlap novelty penalty.
- `TokenBudgetingAlgorithm.py`
  - Budget plan allocation and compression trigger decisions.
- `HistoryTieringAlgorithm.py`
  - Hot/warm/cold conversation tier split with deterministic summaries.
- `PathPruningAlgorithm.py`
  - Confidence-filtered and diversity-aware graph path pruning.
- `QueryPlacementAlgorithm.py`
  - Query-tail guarantee and append helper.
- `QueryAwareCompressionAlgorithm.py`
  - Deterministic placeholder for query-aware extractive compression.

## Why This Is Step-1 Safe

- No runtime endpoint behavior changed.
- No repository or DB schema changed.
- No new third-party dependency introduced.
- Algorithm APIs are stable and testable in isolation.

## Next Step Hook Points (for step-2+)

- Wire `ContextAlgorithmRegistry` into a future `ContextManager` in application layer.
- Replace direct context assembly in `ChatUseCase.execute` with orchestrated pipeline:
  - dedup/MMR -> reordering -> budget decision -> compression -> prompt assembly.
