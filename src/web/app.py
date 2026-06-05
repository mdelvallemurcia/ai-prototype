import streamlit as st

from src.core.container import create_container
from src.web import handlers

st.set_page_config(page_title="MealMate AI", page_icon="🍽️")
st.title("MealMate AI")
st.caption("Your AI-powered recipe assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []


@st.cache_resource
def _get_container():
    return create_container()


# --- Render history -----------------------------------------------------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        for file_meta in message.get("files", []):
            if file_meta.get("thumbnail"):
                st.image(file_meta["thumbnail"])
            else:
                # PDF or non-image: show icon + filename
                st.markdown(f"📄 {file_meta['name']}")

# --- Handle new input ---------------------------------------------------------
chat_value = st.chat_input(
    "What would you like to cook today?",
    accept_file="multiple",
    file_type=["png", "jpg", "jpeg", "gif", "webp", "pdf"],
)

if chat_value:
    text: str = chat_value.text or ""
    raw_files = chat_value.files or []

    # Validate file types (defense-in-depth; Streamlit file_type already filters)
    valid_files = handlers.validate_file_types(raw_files)

    # Extract metadata + thumbnails; never store raw bytes
    file_metas: list[dict] = [handlers.extract_file_metadata(f) for f in valid_files]

    # Skip empty submissions (no text, no files)
    if not text and not file_metas:
        st.stop()

    # Append user turn
    st.session_state.messages.append({"role": "user", "content": text, "files": file_metas})

    # Render the user turn inline (history loop already ran above without this turn)
    with st.chat_message("user"):
        st.markdown(text)
        for file_meta in file_metas:
            if file_meta.get("thumbnail"):
                st.image(file_meta["thumbnail"])
            else:
                st.markdown(f"📄 {file_meta['name']}")

    # Build LangChain messages from history snapshot (user turn included, assistant NOT yet)
    lc_messages = handlers.to_langchain_messages(st.session_state.messages)

    # Stream assistant reply
    container = _get_container()
    try:
        with st.chat_message("assistant"):
            reply: str = st.write_stream(handlers.stream_reply(container.chat_model, lc_messages))
    except Exception:
        reply = "Sorry, I could not reach the AI service. Check your API key and try again."
        with st.chat_message("assistant"):
            st.warning(reply)

    # Persist joined reply
    st.session_state.messages.append({"role": "assistant", "content": reply, "files": []})
    # No st.rerun() — write_stream renders inline during execution
