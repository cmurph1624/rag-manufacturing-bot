# Data Chunking and Retrieval: Lessons from RAG Evaluation

## Overview

This document summarizes key learnings from diagnosing and fixing retrieval failures in a RAG (Retrieval-Augmented Generation) application for manufacturing documentation. The system ingests technical PDFs and Slack conversations to answer questions about assembly procedures, safety protocols, and equipment specifications.

## The Problem

Initial RAGAS evaluation revealed **7 out of 20 questions failing** with major issues:
- **Context Recall = 0.0**: Critical chunks weren't being retrieved at all (e.g., "Loctite 243", "3mm Hex Key")
- **Answer Relevancy = 0.0**: LLM responding "I don't know" even when information existed in source documents
- **Lexical Search Broken**: Returning 0 results for every query

Key failing questions:
- Q2: "Which Loctite type for rotor arm assembly?" → Missing "Loctite 243"
- Q13: "Maximum charging temperature?" → LLM couldn't interpret "don't charge above 40°C"
- Q17: "What tool for M3x10 screws?" → Missing "3mm Hex Key"

## What We Tried: Chunking Strategies

### 1. Standard Fixed-Size Chunking (Baseline)
- **Approach**: Fixed 1000 character chunks with 200 character overlap
- **Result**: Failed to retrieve critical information
- **Issue**: Arbitrary splitting broke semantic units

### 2. Semantic Similarity-Based Chunking (First Attempt)
- **Approach**: Split on sentence boundaries, merge based on embedding similarity
- **Initial Regex**: `r'(?<=[.?!])\s+'`
- **Critical Bug Discovered**: Regex was splitting on numbered lists (1., 2., 3.)
  ```
  Original text:
  "Required Tools:
  1. 3mm Hex Key
  2. Loctite 243
  3. Torque wrench"

  Result: Three separate tiny chunks, each useless without context
  ```
- **Fix**: Updated regex to `r'(?<!\d\.)(?<=[.?!])\s+'` (negative lookbehind for digit+period)
- **Result**: Improved but still had retrieval failures
- **Learning**: Sentence-level chunking alone isn't enough for technical documentation

### 3. Structure-Aware Chunking (Best Performer)
- **Approach**: Classify text segments (headers, lists, tables, procedures) and chunk by logical structure
- **Key Features**:
  - Keep numbered/bulleted lists together
  - Preserve table structures
  - Maintain header-content relationships
  - Enforce minimum chunk size (100 chars)
- **Results**:
  - Q13 SOLVED: LLM correctly interpreted temperature limits
  - Q20 improved significantly
  - But Q2, Q7, Q9, Q17 still had context_recall=0.0
- **Learning**: Good chunking is necessary but not sufficient

## The Real Culprit: Embedding Model Limitations

After fixing chunking, we discovered the **embedding model (`nomic-embed-text`) was the bottleneck**:

**Why embeddings failed:**
```
Query: "Which Loctite type should be used for the rotor arm assembly?"
Chunk: "Apply a single drop of Loctite 243 to the threads of each M3x10 screw."

The embedding model couldn't connect these semantically!
```

The chunks existed in the vector database with perfect structure, but the embeddings couldn't match:
- "Which Loctite type" → "Loctite 243"
- "What tool for M3x10 screws" → "3mm Hex Key"
- "Maximum charging temperature" → "don't charge above 40°C"

**Key Insight**: Semantic search assumes the embedding model can bridge vocabulary gaps and understand synonyms. When it can't, you need lexical search.

## Fixing Lexical Search with BM25

### Original Broken Implementation
```python
# This was NOT real BM25, just naive substring matching
results = collection.get(
    where_document={"$contains": query},
    limit=self.k
)
```
**Problems:**
- Only matched exact substrings (useless for "What tool..." → "3mm Hex Key")
- Called ChromaDB methods but system used Pinecone
- Returned 0 results for every query

### Proper BM25 Implementation
**Challenges with Pinecone:**
- No native BM25 support
- `list_paginated()` API broken (error: "ListResponse has no attribute '0'")
- Need to build in-memory BM25 index from Pinecone vectors

**Solution:**
1. Sample documents using `query()` with random vectors (20 queries × 100 docs = 2000 docs sampled)
2. Extract text from metadata
3. Build BM25 index using `rank-bm25` library
4. Tokenize queries and rank results by BM25 score

```python
from rank_bm25 import BM25Okapi

# Build index from Pinecone
tokenized_corpus = [doc.lower().split() for doc in all_texts]
self._bm25_index = BM25Okapi(tokenized_corpus)

# Query
tokenized_query = query.lower().split()
scores = self._bm25_index.get_scores(tokenized_query)
```

### BM25 Results: Major Improvement

**Q2 (Loctite):**
- Before: context_recall = 0.0
- After: context_recall = 1.0 ✓
- BM25 successfully matched "Loctite type" with "Loctite 243"

**Q13 (Temperature):**
- All metrics near perfect (0.75-0.98)
- Retrieval + generation both working

**Q17 (3mm Hex Key):**
- Still context_recall = 0.0
- BM25 can't bridge "tool for M3x10 screws" → "3mm Hex Key"
- Vocabulary gap too large for pure lexical matching

## Remaining Challenges

### 1. Generation Issues (Q2)
**Problem**: Even with context_recall=1.0, answer_relevancy=0.0
```
Context: "Apply a single drop of Loctite 243 to the threads"
LLM Response: "the specific type of Loctite...is not explicitly stated"
```
**Cause**: Overly conservative prompt requiring exact phrasing
**Solution**: Adjust prompt to recognize implicit answers

### 2. Vocabulary Gap (Q17)
**Problem**: BM25 can't match queries with no overlapping keywords
```
Query: "What tool is required to install M3x10 screws?"
Chunk: "Required Tools: 3mm Hex Key"
No shared keywords → No match
```
**Solution**: Hybrid search (BM25 + semantic embeddings + reranking)

## Key Learnings for Technical RAG Systems

### 1. Match Chunking Strategy to Content Type
- **Technical procedures**: Structure-aware chunking (keep numbered steps together)
- **Conversations**: Semantic chunking (thread-level context)
- **Mixed content**: Test both and measure with proper evals

### 2. Embeddings Aren't Magic
- Popular embedding models (even good ones like `nomic-embed-text`) have limitations
- They struggle with:
  - Vocabulary mismatches (query uses "tool", doc says "hex key")
  - Indirect references (query asks "maximum", doc says "don't exceed")
  - Technical jargon that wasn't in training data

### 3. BM25 Saves the Day (Sometimes)
**When BM25 > Embeddings:**
- Exact terminology matching ("Loctite 243")
- Proper nouns and model numbers
- Queries with overlapping keywords

**When BM25 < Embeddings:**
- Synonym matching ("tool" → "hex key")
- Conceptual queries ("safety requirements")
- Paraphrased questions

### 4. Hybrid Search is the Answer
Neither approach alone is sufficient:
- **BM25**: Catches exact lexical matches embeddings miss
- **Semantic**: Bridges vocabulary gaps BM25 can't handle
- **Reranking**: Refines combined results

### 5. Measure Everything with RAGAS
Key metrics revealed different failure modes:
- `context_recall=0.0` → Retrieval failure (missing chunks)
- `answer_relevancy=0.0` → Generation failure (LLM won't answer)
- `faithfulness<0.7` → Hallucination (LLM inventing facts)
- `context_precision<0.5` → Noise (irrelevant chunks ranked high)

## Technical Implementation Notes

### BM25 on Pinecone (Non-Native Vector DB)
**Challenge**: Pinecone doesn't support BM25 natively

**Workaround**: Build in-memory BM25 index
- Use `query()` with random vectors to sample documents
- Cap at reasonable size (2000 docs) for memory efficiency
- Rebuild periodically or on-demand

**Trade-offs**:
- ✓ Works with any vector DB
- ✓ Full BM25 ranking algorithm
- ✗ Not real-time (index rebuild required for new docs)
- ✗ Memory overhead (stores corpus in RAM)

### Chunking Regex Gotchas
```python
# BAD: Splits on numbered lists
r'(?<=[.?!])\s+'

# GOOD: Preserves numbered lists
r'(?<!\d\.)(?<=[.?!])\s+'
```

Always test regex on actual document content, not toy examples!

## Current State & Next Steps

### What's Working ✓
- Structure-aware chunking preserves document semantics
- BM25 lexical search retrieves exact terminology matches
- RAGAS evaluation identifies specific failure modes

### What's Not Working ✗
- Q17 (3mm Hex Key): Vocabulary gap too large
- Q2 generation: LLM too conservative despite good retrieval
- Some chunks may not be sampled in BM25 index (2000 doc cap)

### Recommended Next Steps
1. **Implement hybrid search**: Combine BM25 + semantic + reranker
2. **Tune generation prompt**: Allow LLM to infer from context
3. **Expand BM25 sampling**: Remove 2000 doc cap or increase query count
4. **Consider better embeddings**: Test `text-embedding-3-large` or `voyage-02`

## Continuation Prompt for Next Session

```
I'm continuing work on my RAG application for manufacturing documentation. In the previous session, we:

1. Fixed data chunking (structure-aware strategy working well)
2. Implemented BM25 lexical search on Pinecone (now retrieving chunks that embeddings missed)
3. Identified remaining issues:
   - Q2 (Loctite): context_recall=1.0 but answer_relevancy=0.0 (generation issue)
   - Q17 (3mm Hex Key): context_recall=0.0 (vocabulary gap, needs hybrid search)

Latest evaluation results are in: evaluation_results/ragas_results_run_ids_3_20260216_165121.csv

I want to focus on [INSERT YOUR PRIORITY]:
- Option A: Implement hybrid search (BM25 + semantic + reranking)
- Option B: Fix the generation prompt to improve answer_relevancy
- Option C: Debug why Q17's chunk isn't being retrieved by BM25

As before, I want your help interpreting results and strategizing - please don't write code unless I explicitly ask.
```

---

## Article Writing Tips

**For Substack readers, emphasize:**
1. The "aha moment" when we discovered embedding limitations
2. The regex bug that split numbered lists (relatable debugging story)
3. Why hybrid search matters (concrete examples with Q2 vs Q17)
4. RAGAS evaluation as your "headlights" (measure → diagnose → fix)

**Possible article structure:**
- Hook: "My RAG app couldn't find 'Loctite 243' even though it was in the docs"
- Problem: Standard chunking failed on technical documentation
- Journey: Three chunking strategies tested (with failure modes)
- Plot twist: Chunking wasn't the real problem
- Solution: BM25 to the rescue (but not a silver bullet)
- Takeaway: Why you need hybrid search for production RAG

**Code snippets to include:**
- The regex bug (before/after comparison)
- BM25 implementation highlights
- Sample RAGAS results showing metrics

Good luck with the article!
