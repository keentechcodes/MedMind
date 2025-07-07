"""
Embeddings service for the Physiology RAG system.
Handles Google Gemini API embeddings and ChromaDB vector database operations.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import chromadb
import google.generativeai as genai

from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger
from physiology_rag.core.cache_manager import get_cache_manager

logger = get_logger("embeddings_service")


class EmbeddingsService:
    """
    Service for generating embeddings and managing vector database operations.
    
    Uses Google Gemini API for embeddings generation and ChromaDB for
    vector storage with persistent storage and cosine similarity.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize embeddings service.
        
        Args:
            api_key: Gemini API key (defaults to settings)
        """
        settings = get_settings()
        
        # Configure Gemini API
        api_key = api_key or settings.gemini_api_key
        genai.configure(api_key=api_key)
        
        # Store settings
        self.embedding_model = settings.gemini_embedding_model
        self.batch_size = settings.batch_size
        
        # Initialize cache manager
        self.cache_manager = get_cache_manager()
        
        # Initialize ChromaDB
        self.vector_db_path = Path(settings.vector_db_path)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=str(self.vector_db_path))
        self.collection = self.client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": settings.similarity_metric}
        )
        
        logger.info(f"Initialized EmbeddingsService with model: {self.embedding_model}")
        logger.info(f"Vector DB path: {self.vector_db_path}")
        logger.info(f"Collection: {settings.collection_name}")
    
    def generate_embeddings(
        self, 
        texts: List[str], 
        batch_size: int = None
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using Gemini API.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (defaults to settings)
            
        Returns:
            List of embedding vectors
        """
        batch_size = batch_size or self.batch_size
        all_embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        logger.info(f"Generating embeddings for {len(texts)} texts in {total_batches} batches")
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = []
            
            for j, text in enumerate(batch):
                try:
                    # Check cache first
                    text_content = text[:1000]  # Limit text length for API
                    cached_embedding = self.cache_manager.get_embedding(text_content)
                    
                    if cached_embedding is not None:
                        batch_embeddings.append(cached_embedding)
                        logger.debug(f"Using cached embedding for text {i+j}")
                    else:
                        # Generate new embedding
                        result = genai.embed_content(
                            model=self.embedding_model,
                            content=text_content,
                            task_type="retrieval_document"
                        )
                        embedding = result['embedding']
                        batch_embeddings.append(embedding)
                        
                        # Cache the embedding
                        self.cache_manager.set_embedding(text_content, embedding)
                        
                except Exception as e:
                    logger.error(f"Error generating embedding for text {i+j}: {e}")
                    # Use zero vector as fallback
                    batch_embeddings.append([0.0] * 768)
            
            all_embeddings.extend(batch_embeddings)
            current_batch = i//batch_size + 1
            logger.info(
                f"✓ Batch {current_batch}/{total_batches} complete "
                f"({len(all_embeddings)}/{len(texts)} embeddings)"
            )
        
        logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
        return all_embeddings
    
    def create_chunk_id(self, doc_name: str, chunk_index: int) -> str:
        """
        Create unique ID for a document chunk.
        
        Args:
            doc_name: Document name
            chunk_index: Chunk index within document
            
        Returns:
            Unique chunk identifier
        """
        return f"{doc_name}_chunk_{chunk_index}"
    
    def add_documents_to_vector_db(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add processed documents to the vector database.
        
        Args:
            documents: List of processed document data
        """
        all_texts = []
        all_metadatas = []
        all_ids = []
        
        logger.info(f"Preparing {len(documents)} documents for vector database")
        
        for doc in documents:
            doc_name = doc['document_name']
            
            for i, chunk in enumerate(doc['chunks']):
                chunk_id = self.create_chunk_id(doc_name, i)
                
                all_texts.append(chunk['text'])
                all_ids.append(chunk_id)
                
                # Enhanced metadata with section information
                metadata = {
                    'document_name': doc_name,
                    'chunk_index': i,
                    'chunk_type': chunk['type'],
                    'chunk_size': chunk['size'],
                    'total_chunks': doc['total_chunks'],
                    'total_images': doc['total_images']
                }
                
                # Add section-specific metadata if available
                if 'title' in chunk:
                    metadata['title'] = chunk['title']
                if 'page_id' in chunk:
                    metadata['page_id'] = chunk['page_id']
                
                all_metadatas.append(metadata)
        
        logger.info(f"Generating embeddings for {len(all_texts)} chunks")
        embeddings = self.generate_embeddings(all_texts)
        
        logger.info("Adding embeddings to vector database")
        self.collection.add(
            embeddings=embeddings,
            documents=all_texts,
            metadatas=all_metadatas,
            ids=all_ids
        )
        
        logger.info(f"Successfully added {len(all_texts)} chunks to vector database")
    
    def search_documents(self, query: str, n_results: int = None) -> Dict[str, Any]:
        """
        Search for relevant document chunks based on query.
        
        Args:
            query: Search query
            n_results: Number of results to return (defaults to settings)
            
        Returns:
            Search results with documents, metadata, and similarity scores
        """
        settings = get_settings()
        n_results = n_results or settings.max_retrieval_results
        
        logger.info(f"Searching for: '{query}' (top {n_results} results)")
        
        try:
            # Check cache for query embedding
            cached_embedding = self.cache_manager.get_embedding(f"query:{query}")
            
            if cached_embedding is not None:
                query_embedding = cached_embedding
                logger.debug("Using cached query embedding")
            else:
                # Generate embedding for query
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=query,
                    task_type="retrieval_query"
                )
                query_embedding = result['embedding']
                
                # Cache the query embedding
                self.cache_manager.set_embedding(f"query:{query}", query_embedding)
            
            # Search in vector database
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity_score': 1 - results['distances'][0][i]  # Convert distance to similarity
                })
            
            logger.info(f"Found {len(formatted_results)} relevant chunks")
            
            return {
                'query': query,
                'results': formatted_results
            }
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return {
                'query': query,
                'results': [],
                'error': str(e)
            }
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database collection.
        
        Returns:
            Collection statistics
        """
        try:
            count = self.collection.count()
            stats = {
                'total_chunks': count,
                'collection_name': self.collection.name,
                'vector_db_path': str(self.vector_db_path)
            }
            logger.info(f"Collection stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {'error': str(e)}
    
    def reset_collection(self) -> None:
        """Reset the vector database collection (for development/testing)."""
        logger.warning("Resetting vector database collection")
        try:
            self.client.delete_collection(self.collection.name)
            settings = get_settings()
            self.collection = self.client.get_or_create_collection(
                name=settings.collection_name,
                metadata={"hnsw:space": settings.similarity_metric}
            )
            logger.info("Successfully reset collection")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")


def main():
    """CLI entry point for embeddings service."""
    settings = get_settings()
    embeddings_service = EmbeddingsService()
    
    # Load processed documents
    processed_file = Path(settings.processed_data_dir) / "processed_documents.json"
    
    if not processed_file.exists():
        logger.error(f"Processed documents file not found: {processed_file}")
        logger.info("Run document processing first")
        return
    
    with open(processed_file, "r", encoding="utf-8") as f:
        documents = json.load(f)
    
    # Add to vector database
    embeddings_service.add_documents_to_vector_db(documents)
    
    # Show stats
    stats = embeddings_service.get_collection_stats()
    print(f"\nVector database stats: {stats}")
    
    # Test search
    test_query = "What is the cerebral cortex?"
    results = embeddings_service.search_documents(test_query)
    
    print(f"\nTest search results for '{test_query}':")
    for i, result in enumerate(results['results'][:3]):
        print(f"{i+1}. Score: {result['similarity_score']:.3f}")
        print(f"   Document: {result['metadata']['document_name']}")
        print(f"   Text: {result['document'][:200]}...")
        print()


if __name__ == "__main__":
    main()