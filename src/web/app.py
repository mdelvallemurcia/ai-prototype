import streamlit as st

st.set_page_config(page_title="MealMate AI", page_icon="🍽️")
st.title("MealMate AI")
st.caption("Your AI-powered recipe assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What would you like to cook today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # TODO: integrate RAG chain
        response = f"I received your question: '{prompt}'. RAG integration coming soon!"
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
