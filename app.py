import os

import mlflow
import mlflow.transformers
import streamlit as st
from langchain_huggingface import HuggingFacePipeline
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

MODEL_NAME = "model/Qwen2.5-1.5B-Instruct"
EMB_MODEL_NAME = "model/bge-large-en-v1.5"

# define the absolute path of the LLM model
MODEL_PATH = os.path.abspath(MODEL_NAME)
EMB_MODEL_PATH = os.path.abspath(EMB_MODEL_NAME)


# 1. Enable autologging before any model operations
mlflow.transformers.autolog()

st.title("Local Qwen Chatbot with MLflow")

# 2. Load model and pipeline once
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH)

if "llm" not in st.session_state:
    with st.spinner("Loading model and starting MLflow tracking..."):
        # Set experiment for cleaner organization
        mlflow.set_experiment("qwen-chatbot-tracking")

        # Start a run that persists for the lifetime of the session
        # or use individual runs per interaction
        with mlflow.start_run():
            MODEL_PATH = MODEL_NAME
            pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=512)
            st.session_state.llm = HuggingFacePipeline(pipeline=pipe)

# 3. Standard Streamlit Chat UI
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask something..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Each query can be logged as an artifact or parameter in MLflow if desired
        stream = st.session_state.llm.stream(prompt)
        response = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": response})
