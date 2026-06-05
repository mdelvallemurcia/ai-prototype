import streamlit as st

from src.web import handlers

st.set_page_config(page_title="MealMate AI", page_icon="🍽️")
st.title("MealMate AI")
st.caption("Your AI-powered recipe assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

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

    # Build echo response
    echo = handlers.build_echo_response(text, file_metas)

    # Append user turn
    st.session_state.messages.append({"role": "user", "content": text, "files": file_metas})

    # Append assistant turn
    st.session_state.messages.append({"role": "assistant", "content": echo, "files": []})

    st.rerun()
