# ADR-001: NVIDIA Build API as LLM Provider

## Status

Accepted

## Context

The project needs an LLM provider for both chat completions and embeddings. Options considered: OpenAI API, Anthropic API, local models via Ollama, and NVIDIA Build API.

## Decision

Use NVIDIA Build API (`langchain-nvidia-ai-endpoints`) for both LLM inference and embeddings.

## Reasoning

- **Zero cost**: NVIDIA provides free API keys for developers — no billing setup, no pay-per-token charges. This is a learning/prototype project where spending on API calls is not justified.
- **No local hardware requirement**: Ollama was considered but discarded because the development machine lacks the GPU/RAM to run capable models locally. NVIDIA Build API offloads inference to NVIDIA's infrastructure.
- **LangChain integration**: `langchain-nvidia-ai-endpoints` provides drop-in LangChain compatibility for both `ChatNVIDIA` (chat) and `NVIDIAEmbeddings` (embeddings), keeping the RAG pipeline consistent.

## Consequences

- Dependent on NVIDIA's free tier availability and rate limits.
- Model selection is limited to what NVIDIA exposes through their Build API.
- If the project moves to production, the provider choice should be revisited for SLAs and model quality.
