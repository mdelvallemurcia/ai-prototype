# ADR-003: Streamlit as Web UI

## Status

Accepted

## Context

The project needs a chat interface for users to interact with the RAG pipeline. Options considered: Streamlit, Gradio, Chainlit, and a custom FastAPI + frontend (React, HTMX, etc.).

## Decision

Use Streamlit for the web UI.

## Reasoning

- **Minimal UI requirements**: The interface is a single page with a chat conversation — no navigation, no dashboards, no complex layouts. Streamlit covers this with built-in `st.chat_message` and `st.chat_input` components.
- **Speed to prototype**: A working chat UI can be built in a single Python file with no frontend toolchain (no npm, no bundler, no JS/TS).
- **Python-only stack**: The entire project stays in Python — no context-switching to a frontend language.

## Consequences

- If the UI needs grow beyond a single chat page (e.g., recipe browsing, user accounts, admin panel), Streamlit will become a limitation and a different framework should be evaluated.
- Streamlit's rerun-on-interaction model adds complexity for stateful conversations, but `st.session_state` handles it for this use case.
