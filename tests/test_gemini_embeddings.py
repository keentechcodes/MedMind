#!/usr/bin/env python3
"""
Test script for Gemini embeddings functionality
"""

import google.generativeai as genai

def test_gemini_embeddings():
    print("🔐 Testing Gemini API embeddings...")
    
    # Configure API key from environment or settings
    import os
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable not set")
        print("Please set it with: export GEMINI_API_KEY=your-api-key")
        return False
    
    genai.configure(api_key=api_key)
    
    try:
        # Test embedding generation
        print("🔄 Testing embedding generation...")
        
        result = genai.embed_content(
            model="models/text-embedding-004",
            content="The cerebral cortex is the outer layer of neural tissue.",
            task_type="retrieval_document"
        )
        
        embedding = result['embedding']
        print(f"✅ Successfully generated embedding with {len(embedding)} dimensions")
        print(f"   First 5 values: {embedding[:5]}")
        
        # Test query embedding
        print("🔄 Testing query embedding...")
        
        query_result = genai.embed_content(
            model="models/text-embedding-004",
            content="What is the cerebral cortex?",
            task_type="retrieval_query"
        )
        
        query_embedding = query_result['embedding']
        print(f"✅ Successfully generated query embedding with {len(query_embedding)} dimensions")
        
        print("\n✅ All Gemini embedding tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Gemini embedding test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_gemini_embeddings()