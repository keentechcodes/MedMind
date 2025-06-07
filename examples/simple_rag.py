#!/usr/bin/env python3
"""
Simplified RAG System for debugging

NOTE: This is a debugging/example script. For production use, 
use the main RAG system at physiology_rag.core.rag_system.RAGSystem
"""

import os
import google.generativeai as genai
from physiology_rag.core.embeddings_service import EmbeddingsService
from physiology_rag.config.settings import get_settings

class SimpleRAG:
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.embeddings_service = EmbeddingsService(api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def answer_question(self, query: str) -> dict:
        print(f"🔍 Searching for: {query}")
        
        # Step 1: Retrieve (limit to 3 results to keep it simple)
        try:
            search_results = self.embeddings_service.search_documents(query, 3)
            print(f"✅ Retrieved {len(search_results['results'])} results")
        except Exception as e:
            return {"error": f"Retrieval failed: {e}"}
        
        # Step 2: Format context (keep it short)
        context = ""
        for i, result in enumerate(search_results['results'][:2]):  # Only use top 2
            context += f"Source {i+1}: {result['document'][:500]}...\n\n"
        
        print(f"✅ Context formatted ({len(context)} chars)")
        
        # Step 3: Generate (simplified prompt)
        try:
            prompt = f"""Based on this context about physiology:

{context}

Question: {query}

Answer briefly:"""
            
            print("🧠 Calling Gemini...")
            response = self.model.generate_content(prompt)
            print("✅ Gemini responded")
            
            return {
                "query": query,
                "answer": response.text,
                "sources": search_results['results']
            }
            
        except Exception as e:
            return {"error": f"Generation failed: {e}"}

if __name__ == "__main__":
    try:
        settings = get_settings()
        api_key = settings.gemini_api_key
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        print("Please check your .env file has GEMINI_API_KEY set")
        exit(1)
    
    rag = SimpleRAG(api_key)
    
    result = rag.answer_question("What is the cerebral cortex?")
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Answer: {result['answer']}")