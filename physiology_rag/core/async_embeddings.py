"""
Async embeddings service for improved performance.
Provides batch processing and concurrent operations for embeddings generation.
"""

import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
import time

import google.generativeai as genai

from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger
from physiology_rag.core.cache_manager import get_cache_manager

logger = get_logger("async_embeddings")


class AsyncEmbeddingsService:
    """Async embeddings service with concurrent processing."""
    
    def __init__(self, api_key: str = None, max_workers: int = 4):
        """
        Initialize async embeddings service.
        
        Args:
            api_key: Gemini API key
            max_workers: Maximum concurrent workers
        """
        settings = get_settings()
        
        # Configure API
        api_key = api_key or settings.gemini_api_key
        genai.configure(api_key=api_key)
        
        self.embedding_model = settings.gemini_embedding_model
        self.batch_size = settings.batch_size
        self.max_workers = max_workers
        self.cache_manager = get_cache_manager()
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        logger.info(f"Initialized AsyncEmbeddingsService with {max_workers} workers")
    
    async def generate_single_embedding(
        self, 
        text: str, 
        task_type: str = "retrieval_document"
    ) -> Optional[List[float]]:
        """
        Generate embedding for a single text asynchronously.
        
        Args:
            text: Input text
            task_type: Type of task (retrieval_document or retrieval_query)
            
        Returns:
            Embedding vector or None if failed
        """
        text_content = text[:1000]  # Limit for API
        
        # Check cache first
        cache_key = f"{task_type}:{text_content}"
        cached_embedding = self.cache_manager.get_embedding(cache_key)
        
        if cached_embedding is not None:
            logger.debug("Using cached embedding")
            return cached_embedding
        
        # Generate embedding in thread pool
        loop = asyncio.get_event_loop()
        
        try:
            def _generate():
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=text_content,
                    task_type=task_type
                )
                return result['embedding']
            
            embedding = await loop.run_in_executor(self.executor, _generate)
            
            # Cache the result
            self.cache_manager.set_embedding(cache_key, embedding)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    async def generate_batch_embeddings(
        self, 
        texts: List[str], 
        task_type: str = "retrieval_document",
        batch_size: int = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts concurrently.
        
        Args:
            texts: List of input texts
            task_type: Type of task
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        batch_size = batch_size or self.batch_size
        total_texts = len(texts)
        
        logger.info(f"Generating embeddings for {total_texts} texts with async processing")
        
        # Create tasks for concurrent processing
        tasks = []
        for text in texts:
            task = self.generate_single_embedding(text, task_type)
            tasks.append(task)
        
        # Process in batches to avoid overwhelming the API
        all_embeddings = []
        start_time = time.time()
        
        for i in range(0, len(tasks), batch_size):
            batch_tasks = tasks[i:i + batch_size]
            
            # Process batch concurrently
            batch_embeddings = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for j, result in enumerate(batch_embeddings):
                if isinstance(result, Exception):
                    logger.error(f"Error in embedding {i+j}: {result}")
                    all_embeddings.append([0.0] * 768)  # Fallback
                elif result is None:
                    logger.warning(f"No embedding generated for text {i+j}")
                    all_embeddings.append([0.0] * 768)  # Fallback
                else:
                    all_embeddings.append(result)
            
            # Progress logging
            current_batch = i // batch_size + 1
            total_batches = (len(tasks) + batch_size - 1) // batch_size
            elapsed = time.time() - start_time
            
            logger.info(
                f"✓ Async batch {current_batch}/{total_batches} complete "
                f"({len(all_embeddings)}/{total_texts} embeddings, {elapsed:.1f}s)"
            )
            
            # Small delay between batches to be API-friendly
            if i + batch_size < len(tasks):
                await asyncio.sleep(0.1)
        
        total_time = time.time() - start_time
        logger.info(f"Completed {total_texts} embeddings in {total_time:.1f}s")
        
        return all_embeddings
    
    async def search_similar_async(
        self, 
        query: str, 
        collection,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """
        Perform async similarity search.
        
        Args:
            query: Search query
            collection: ChromaDB collection
            n_results: Number of results
            
        Returns:
            Search results
        """
        # Generate query embedding
        query_embedding = await self.generate_single_embedding(query, "retrieval_query")
        
        if query_embedding is None:
            return {'query': query, 'results': [], 'error': 'Failed to generate query embedding'}
        
        # Perform search in thread pool
        loop = asyncio.get_event_loop()
        
        def _search():
            return collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
        
        try:
            results = await loop.run_in_executor(self.executor, _search)
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity_score': 1 - results['distances'][0][i]
                })
            
            return {
                'query': query,
                'results': formatted_results
            }
            
        except Exception as e:
            logger.error(f"Error in async search: {e}")
            return {'query': query, 'results': [], 'error': str(e)}
    
    async def batch_add_to_collection(
        self, 
        texts: List[str], 
        metadatas: List[Dict[str, Any]], 
        ids: List[str],
        collection
    ) -> None:
        """
        Add documents to collection with async embedding generation.
        
        Args:
            texts: List of texts
            metadatas: List of metadata dicts
            ids: List of document IDs
            collection: ChromaDB collection
        """
        logger.info(f"Adding {len(texts)} documents to collection with async embeddings")
        
        # Generate embeddings concurrently
        embeddings = await self.generate_batch_embeddings(texts)
        
        # Add to collection in thread pool
        loop = asyncio.get_event_loop()
        
        def _add():
            collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
        
        await loop.run_in_executor(self.executor, _add)
        logger.info(f"Successfully added {len(texts)} documents to collection")
    
    def close(self):
        """Close the thread pool executor."""
        self.executor.shutdown(wait=True)
        logger.info("AsyncEmbeddingsService closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()


class BatchProcessor:
    """Utility class for batch processing operations."""
    
    @staticmethod
    async def process_documents_async(
        documents: List[Dict[str, Any]], 
        async_embeddings: AsyncEmbeddingsService,
        collection
    ) -> None:
        """
        Process multiple documents asynchronously.
        
        Args:
            documents: List of document data
            async_embeddings: Async embeddings service
            collection: ChromaDB collection
        """
        all_texts = []
        all_metadatas = []
        all_ids = []
        
        logger.info(f"Preparing {len(documents)} documents for async processing")
        
        for doc in documents:
            doc_name = doc['document_name']
            
            for i, chunk in enumerate(doc['chunks']):
                chunk_id = f"{doc_name}_chunk_{i}"
                
                all_texts.append(chunk['text'])
                all_ids.append(chunk_id)
                
                # Enhanced metadata
                metadata = {
                    'document_name': doc_name,
                    'chunk_index': i,
                    'chunk_type': chunk.get('type', 'content'),
                    'chunk_size': chunk.get('size', len(chunk['text'])),
                    'total_chunks': doc.get('total_chunks', len(doc['chunks'])),
                    'total_images': doc.get('total_images', 0)
                }
                
                # Add advanced chunking metadata if available
                if 'medical_concepts' in chunk:
                    metadata['medical_concepts'] = chunk['medical_concepts']
                if 'concept_density' in chunk:
                    metadata['concept_density'] = chunk['concept_density']
                if 'title' in chunk:
                    metadata['title'] = chunk['title']
                if 'page_id' in chunk:
                    metadata['page_id'] = chunk['page_id']
                
                all_metadatas.append(metadata)
        
        # Process all documents concurrently
        await async_embeddings.batch_add_to_collection(
            all_texts, all_metadatas, all_ids, collection
        )


async def main():
    """Test async embeddings service."""
    async with AsyncEmbeddingsService(max_workers=2) as async_service:
        # Test single embedding
        test_text = "The cerebral cortex is responsible for higher-order thinking."
        embedding = await async_service.generate_single_embedding(test_text)
        print(f"Generated embedding with {len(embedding)} dimensions")
        
        # Test batch embeddings
        test_texts = [
            "Neurons communicate through synapses.",
            "The heart pumps blood through the circulatory system.",
            "Homeostasis maintains internal balance."
        ]
        
        embeddings = await async_service.generate_batch_embeddings(test_texts)
        print(f"Generated {len(embeddings)} batch embeddings")
        
        # Show cache stats
        cache_stats = async_service.cache_manager.get_comprehensive_stats()
        print(f"Cache stats: {cache_stats}")


if __name__ == "__main__":
    asyncio.run(main())