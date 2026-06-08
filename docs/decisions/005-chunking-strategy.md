# ADR-005: RecursiveCharacterTextSplitter with Default Parameters

## Status

Superseded by Revision 1 (below) — the original decision caused a production failure.

## Context

Ingested documents (YouTube transcripts, PDFs, web pages) need to be split into chunks before embedding and storing in pgvector.

## Decision

Use LangChain's `RecursiveCharacterTextSplitter` with default `chunk_size` and `chunk_overlap` values.

## Reasoning

- **Framework standard**: `RecursiveCharacterTextSplitter` is LangChain's recommended default splitter. It recursively tries splitting by paragraphs, sentences, then characters — producing more semantically coherent chunks than naive fixed-size splitting.
- **Defaults are good enough**: For a spike/prototype, the default parameters provide a reasonable baseline without premature optimization.

## Consequences

- Chunk size and overlap are not tuned for recipe content specifically. Retrieval quality may improve with domain-specific tuning (e.g., shorter chunks for ingredient lists, longer for preparation steps).
- If retrieval quality becomes an issue, this is the first knob to turn — experiment with `chunk_size` and `chunk_overlap` values before changing the retrieval strategy itself.

---

## Revision 1: Token-Aware Splitting via tiktoken

### Status

Accepted

### Context

Running the worker ingest CLI against the real NVIDIA embeddings API failed in production with:

```
[400] Input length 704 exceeds maximum allowed token size 512
```

Root cause: `RecursiveCharacterTextSplitter()` with library defaults uses `chunk_size=4000`
**characters** (~700 tokens for this content), but the embedding model
`nvidia/nv-embedqa-e5-v5` (the default `MEALMATE_NVIDIA_EMBED_MODEL`) caps input at
**512 tokens**. Splitting by character count is blind to the model's actual token limit,
so a "default is good enough" chunk could — and did — exceed it.

### Decision

Switch to a **token-aware splitter** using `RecursiveCharacterTextSplitter.from_tiktoken_encoder`,
counting tokens with `tiktoken` instead of characters:

- `chunk_size=448` tokens
- `chunk_overlap=64` tokens

### Reasoning

- **Token limits require token-aware splitting**: character-based chunk sizes are a proxy
  that breaks down once content density varies — the only reliable guard against the
  embed model's 512-token cap is to measure in the same unit the model enforces (tokens).
- **Safety margin for tokenizer mismatch**: `tiktoken` (the encoder backing
  `from_tiktoken_encoder`) over-counts relative to the NVIDIA e5 tokenizer for this content
  (observed: 4000 chars ≈ 704 NVIDIA tokens ≈ ~1000 tiktoken tokens). A 448-tiktoken-token
  budget therefore maps to well under the 512-NVIDIA-token limit, leaving headroom for
  tokenizer differences across content types.
- **New dependency**: `tiktoken` is added explicitly to `pyproject.toml` (it already backs
  `from_tiktoken_encoder` transitively via `langchain-text-splitters`).

### Consequences

- Chunks are now guaranteed (by a unit test asserting every produced chunk's tiktoken
  token count is `<= 448`) to stay within a safe margin of the embed model's 512-token
  input limit. This regression is the actual guard — the integration e2e test uses
  `DeterministicFakeEmbedding`, which has no token limit and would not catch this class
  of bug.
- If the embedding model changes (`MEALMATE_NVIDIA_EMBED_MODEL`), revisit `_CHUNK_TOKENS`
  and `_CHUNK_OVERLAP_TOKENS` in `src/worker/pipeline.py` against the new model's token cap.
- Retrieval quality tuning (chunk size/overlap for recipe content specifically) remains an
  open follow-up, now bounded by the 448-token ceiling rather than a raw character count.
