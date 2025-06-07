"""
Document processing module for the Physiology RAG system.
Handles conversion of markdown documents to structured chunks.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger

logger = get_logger("document_processor")


class DocumentProcessor:
    """
    Processes markdown documents into structured chunks for RAG.
    
    Uses metadata from marker-pdf to create intelligent, section-aware chunks
    that preserve document structure and improve retrieval quality.
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize document processor.
        
        Args:
            output_dir: Directory containing processed documents (defaults to settings)
        """
        settings = get_settings()
        self.output_dir = Path(output_dir or settings.processed_data_dir)
        self.chunk_size = settings.chunk_size
        
        logger.info(f"Initialized DocumentProcessor with output_dir: {self.output_dir}")
        
    def chunk_markdown_with_metadata(
        self, 
        text: str, 
        metadata: Dict, 
        chunk_size: int = None
    ) -> List[Dict[str, Any]]:
        """
        Chunk markdown text using metadata table of contents for better structure.
        
        Args:
            text: Markdown content to chunk
            metadata: Document metadata from marker-pdf
            chunk_size: Maximum chunk size (defaults to settings)
            
        Returns:
            List of structured chunks with metadata
        """
        chunk_size = chunk_size or self.chunk_size
        chunks = []
        toc = metadata.get('table_of_contents', [])
        
        if not toc:
            logger.warning("No table of contents found, using simple chunking")
            return self.simple_chunk_text(text, chunk_size)
        
        # Group TOC items by page
        pages = {}
        for item in toc:
            page_id = item.get('page_id', 0)
            if page_id not in pages:
                pages[page_id] = []
            pages[page_id].append(item)
        
        logger.info(f"Processing {len(pages)} pages with table of contents")
        
        # Split text into sections using headers from TOC
        for page_id, page_items in pages.items():
            for item in page_items:
                title = item.get('title', '').strip()
                if not title:
                    continue
                
                # Find this section in the text
                section_text = self.extract_section_text(text, title, chunk_size)
                if section_text:
                    chunks.append({
                        'text': section_text,
                        'type': 'section',
                        'title': title,
                        'page_id': page_id,
                        'size': len(section_text)
                    })
        
        # If no sections found, fallback to simple chunking
        if not chunks:
            logger.warning("No sections extracted, falling back to simple chunking")
            chunks = self.simple_chunk_text(text, chunk_size)
        else:
            logger.info(f"Successfully extracted {len(chunks)} section-based chunks")
        
        return chunks
    
    def extract_section_text(self, text: str, title: str, max_size: int) -> str:
        """
        Extract text for a specific section title.
        
        Args:
            text: Full document text
            title: Section title to find
            max_size: Maximum section size
            
        Returns:
            Extracted section text
        """
        # Clean title for regex matching
        clean_title = re.escape(title.replace('\n', ' ').strip())
        pattern = rf".*{clean_title}.*"
        
        lines = text.split('\n')
        start_idx = None
        
        # Find the section start
        for i, line in enumerate(lines):
            if re.search(pattern, line, re.IGNORECASE):
                start_idx = i
                break
        
        if start_idx is None:
            return ""
        
        # Extract section text (limited size)
        section_lines = []
        total_chars = 0
        
        for i in range(start_idx, min(start_idx + 50, len(lines))):
            line = lines[i]
            if total_chars + len(line) > max_size:
                break
            section_lines.append(line)
            total_chars += len(line) + 1
        
        return '\n'.join(section_lines).strip()
    
    def simple_chunk_text(self, text: str, chunk_size: int) -> List[Dict[str, Any]]:
        """
        Simple text chunking fallback for documents without metadata.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum chunk size
            
        Returns:
            List of text chunks
        """
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk + sentence) < chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'type': 'content',
                        'size': len(current_chunk)
                    })
                current_chunk = sentence + " "
        
        if current_chunk:
            chunks.append({
                'text': current_chunk.strip(),
                'type': 'content', 
                'size': len(current_chunk)
            })
        
        return chunks
    
    def extract_images_metadata(self, doc_dir: Path) -> List[Dict[str, Any]]:
        """
        Extract metadata about images in the document directory.
        
        Args:
            doc_dir: Directory containing document images
            
        Returns:
            List of image metadata dictionaries
        """
        images = []
        for img_file in doc_dir.glob("*.jpeg"):
            # Parse filename for page and figure info
            filename = img_file.name
            page_match = re.search(r'_page_(\d+)_', filename)
            figure_match = re.search(r'(Figure|Picture)_(\d+)', filename)
            
            images.append({
                'filename': filename,
                'path': str(img_file),
                'page': int(page_match.group(1)) if page_match else None,
                'type': figure_match.group(1) if figure_match else 'unknown',
                'number': int(figure_match.group(2)) if figure_match else None
            })
        
        return sorted(images, key=lambda x: (x['page'] or 0, x['number'] or 0))
    
    def process_document(self, doc_name: str) -> Dict[str, Any]:
        """
        Process a single document directory and return structured data.
        
        Args:
            doc_name: Name of the document directory
            
        Returns:
            Processed document data with chunks and metadata
            
        Raises:
            FileNotFoundError: If markdown file doesn't exist
        """
        doc_dir = self.output_dir / doc_name
        md_file = doc_dir / f"{doc_name}.md"
        
        if not md_file.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_file}")
        
        logger.info(f"Processing document: {doc_name}")
        
        # Read markdown content
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Read metadata
        metadata_file = doc_dir / "metadata.txt"
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.loads(f.read())
        
        # Process content using metadata
        chunks = self.chunk_markdown_with_metadata(content, metadata)
        images = self.extract_images_metadata(doc_dir)
        
        result = {
            'document_name': doc_name,
            'content': content,
            'chunks': chunks,
            'images': images,
            'metadata': metadata,
            'total_chunks': len(chunks),
            'total_images': len(images)
        }
        
        logger.info(f"Processed {doc_name}: {len(chunks)} chunks, {len(images)} images")
        return result
    
    def process_all_documents(self) -> List[Dict[str, Any]]:
        """
        Process all documents in the output directory.
        
        Returns:
            List of processed document data
        """
        documents = []
        
        if not self.output_dir.exists():
            logger.error(f"Output directory does not exist: {self.output_dir}")
            return documents
        
        logger.info(f"Processing all documents in: {self.output_dir}")
        
        for doc_dir in self.output_dir.iterdir():
            if doc_dir.is_dir():
                try:
                    doc_data = self.process_document(doc_dir.name)
                    documents.append(doc_data)
                    logger.info(
                        f"Successfully processed: {doc_dir.name} "
                        f"({doc_data['total_chunks']} chunks, {doc_data['total_images']} images)"
                    )
                except Exception as e:
                    logger.error(f"Error processing {doc_dir.name}: {e}")
        
        logger.info(f"Completed processing {len(documents)} documents")
        return documents
    
    def save_processed_documents(
        self, 
        documents: List[Dict[str, Any]], 
        output_file: str = None
    ) -> None:
        """
        Save processed documents to JSON file.
        
        Args:
            documents: List of processed documents
            output_file: Output file path (defaults to processed_documents.json)
        """
        settings = get_settings()
        output_file = output_file or str(Path(settings.processed_data_dir) / "processed_documents.json")
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(documents)} processed documents to {output_file}")


def main():
    """CLI entry point for document processing."""
    processor = DocumentProcessor()
    documents = processor.process_all_documents()
    processor.save_processed_documents(documents)
    
    print(f"\nProcessed {len(documents)} documents")
    print("Saved to processed_documents.json")


if __name__ == "__main__":
    main()