#!/usr/bin/env python3
"""
Test script to verify Google Cloud authentication is working
"""

import os
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

def test_authentication():
    print("🔐 Testing Google Cloud authentication...")
    
    # Check environment variables
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    print(f"Project ID: {project_id}")
    print(f"Credentials path: {credentials_path}")
    
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT not set")
        return False
    
    if not credentials_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        return False
    
    if not os.path.exists(credentials_path):
        print(f"❌ Credentials file not found: {credentials_path}")
        return False
    
    try:
        # Test Vertex AI initialization
        print("\n🔄 Initializing Vertex AI...")
        aiplatform.init(project=project_id, location="us-central1")
        print("✅ Vertex AI initialized successfully")
        
        # Test embedding model
        print("\n🔄 Testing embedding model...")
        model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
        print("✅ Embedding model loaded successfully")
        
        # Test actual embedding generation
        print("\n🔄 Testing embedding generation...")
        test_text = ["Hello, this is a test"]
        embeddings = model.get_embeddings(test_text)
        
        if embeddings and len(embeddings) > 0:
            print(f"✅ Generated embedding with {len(embeddings[0].values)} dimensions")
            print("🎉 Authentication test passed!")
            return True
        else:
            print("❌ Failed to generate embeddings")
            return False
            
    except Exception as e:
        print(f"❌ Authentication test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_authentication()
    if success:
        print("\n✅ You're ready to run the RAG setup!")
    else:
        print("\n❌ Please check your authentication setup")