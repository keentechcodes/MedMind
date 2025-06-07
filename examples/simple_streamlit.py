#!/usr/bin/env python3
"""
Simple Streamlit test to debug RAG system issues

NOTE: This is a debugging/example script. For production use, 
use the main Streamlit app at physiology_rag/ui/streamlit_app.py
"""

import os
import streamlit as st
import google.generativeai as genai
from physiology_rag.core.embeddings_service import EmbeddingsService

st.title("🧠 Simple RAG Test")

# Test embeddings service directly
@st.cache_resource
def get_embeddings_service():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        st.error("GEMINI_API_KEY environment variable not set")
        return None
    return EmbeddingsService(api_key=api_key)

# Test Gemini directly
@st.cache_resource
def get_gemini_model():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        st.error("GEMINI_API_KEY environment variable not set")
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash-exp')

if st.button("Test Embeddings Service"):
    try:
        with st.spinner("Testing embeddings..."):
            embeddings_service = get_embeddings_service()
            result = embeddings_service.search_documents("cerebral cortex", 2)
            st.success("Embeddings service works!")
            st.json(result)
    except Exception as e:
        st.error(f"Embeddings error: {e}")

if st.button("Test Gemini Model"):
    try:
        with st.spinner("Testing Gemini..."):
            model = get_gemini_model()
            response = model.generate_content("What is the cerebral cortex?")
            st.success("Gemini model works!")
            st.write(response.text)
    except Exception as e:
        st.error(f"Gemini error: {e}")

# Simple chat input
if prompt := st.chat_input("Test question"):
    st.write(f"You asked: {prompt}")
    
    try:
        # Test just embeddings
        with st.spinner("Testing retrieval..."):
            embeddings_service = get_embeddings_service()
            search_result = embeddings_service.search_documents(prompt, 3)
            st.write("✅ Retrieval works")
            
        # Test just generation
        with st.spinner("Testing generation..."):
            model = get_gemini_model()
            response = model.generate_content(f"Answer this question: {prompt}")
            st.write("✅ Generation works")
            st.write(response.text)
            
    except Exception as e:
        st.error(f"Error: {e}")