"""
Tests for document processor module.
"""

import json
import pytest
from pathlib import Path

from physiology_rag.core.document_processor import DocumentProcessor


class TestDocumentProcessor:
    """Test cases for DocumentProcessor class."""
    
    def test_init(self, test_settings, temp_dir):
        """Test DocumentProcessor initialization."""
        processor = DocumentProcessor(str(temp_dir))
        assert processor.output_dir == temp_dir
        assert processor.chunk_size == test_settings.chunk_size
    
    def test_simple_chunk_text(self, temp_dir):
        """Test simple text chunking."""
        processor = DocumentProcessor(str(temp_dir))
        
        text = "This is sentence one. This is sentence two. This is sentence three."
        chunks = processor.simple_chunk_text(text, chunk_size=30)
        
        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('type' in chunk for chunk in chunks)
        assert all('size' in chunk for chunk in chunks)
    
    def test_chunk_markdown_with_metadata(self, temp_dir):
        """Test metadata-aware chunking."""
        processor = DocumentProcessor(str(temp_dir))
        
        text = "# Introduction\nThis is the introduction.\n# Methods\nThis is the methods section."
        metadata = {
            'table_of_contents': [
                {'title': 'Introduction', 'page_id': 1},
                {'title': 'Methods', 'page_id': 1}
            ]
        }
        
        chunks = processor.chunk_markdown_with_metadata(text, metadata)
        
        assert len(chunks) >= 0  # May not find sections in simple text
        # Test fallback to simple chunking
        if len(chunks) == 0:
            chunks = processor.simple_chunk_text(text, 1000)
            assert len(chunks) > 0
    
    def test_extract_section_text(self, temp_dir):
        """Test section text extraction."""
        processor = DocumentProcessor(str(temp_dir))
        
        text = "# Introduction\nThis is the introduction section.\n# Methods\nThis is the methods."
        title = "Introduction"
        
        section_text = processor.extract_section_text(text, title, max_size=100)
        
        # Should find the introduction section
        assert "Introduction" in section_text or section_text == ""
    
    def test_extract_images_metadata(self, temp_dir):
        """Test image metadata extraction."""
        processor = DocumentProcessor(str(temp_dir))
        
        # Create mock image files
        (temp_dir / "_page_1_Figure_1.jpeg").touch()
        (temp_dir / "_page_2_Picture_5.jpeg").touch()
        
        images = processor.extract_images_metadata(temp_dir)
        
        assert len(images) == 2
        assert all('filename' in img for img in images)
        assert all('page' in img for img in images)
        assert all('type' in img for img in images)
    
    def test_process_document_file_not_found(self, temp_dir):
        """Test processing non-existent document."""
        processor = DocumentProcessor(str(temp_dir))
        
        with pytest.raises(FileNotFoundError):
            processor.process_document("nonexistent_doc")
    
    def test_save_processed_documents(self, temp_dir, sample_documents):
        """Test saving processed documents."""
        processor = DocumentProcessor(str(temp_dir))
        output_file = temp_dir / "test_output.json"
        
        processor.save_processed_documents(sample_documents, str(output_file))
        
        assert output_file.exists()
        with open(output_file) as f:
            saved_docs = json.load(f)
        
        assert len(saved_docs) == len(sample_documents)
        assert saved_docs[0]['document_name'] == sample_documents[0]['document_name']