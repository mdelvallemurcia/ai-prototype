# ADR-005: RecursiveCharacterTextSplitter with Default Parameters

## Status

Accepted — may tune later

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
