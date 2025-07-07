"""
Paragraph-level extraction for enhanced citation granularity.
Breaks down document chunks into meaningful paragraphs with proper titles.
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass

from physiology_rag.utils.logging import get_logger

logger = get_logger("paragraph_extractor")


@dataclass
class Paragraph:
    """A paragraph extracted from a document chunk."""
    title: str
    content: str
    paragraph_index: int
    source_chunk_index: int
    document_name: str
    metadata: Dict[str, Any]


class ParagraphExtractor:
    """
    Extracts meaningful paragraphs from document chunks for precise citations.
    """
    
    def __init__(self):
        self.logger = logger
        
    def extract_paragraphs_from_chunk(
        self, 
        chunk_text: str, 
        chunk_metadata: Dict[str, Any]
    ) -> List[Paragraph]:
        """
        Extract paragraphs from a document chunk.
        
        Args:
            chunk_text: The text content of the chunk
            chunk_metadata: Metadata about the chunk
            
        Returns:
            List of extracted paragraphs with titles
        """
        if not chunk_text or not chunk_text.strip():
            return []
            
        paragraphs = []
        doc_name = chunk_metadata.get('document_name', 'Unknown Document')
        chunk_index = chunk_metadata.get('chunk_index', 0)
        
        # Split by clear section markers first
        sections = self._split_by_section_markers(chunk_text)
        
        paragraph_index = 0
        for section in sections:
            section_paragraphs = self._extract_paragraphs_from_section(section)
            
            for para_text in section_paragraphs:
                if len(para_text.strip()) < 50:  # Skip very short paragraphs
                    continue
                    
                # Extract title for this paragraph
                title = self._extract_paragraph_title(para_text)
                
                paragraph = Paragraph(
                    title=title,
                    content=para_text.strip(),
                    paragraph_index=paragraph_index,
                    source_chunk_index=chunk_index,
                    document_name=doc_name,
                    metadata={
                        **chunk_metadata,
                        'paragraph_index': paragraph_index,
                        'extraction_method': 'paragraph_extractor'
                    }
                )
                
                paragraphs.append(paragraph)
                paragraph_index += 1
                
        logger.info(f"Extracted {len(paragraphs)} paragraphs from chunk {chunk_index}")
        return paragraphs
    
    def _split_by_section_markers(self, text: str) -> List[str]:
        """Split text by major section markers."""
        # Look for clear section boundaries
        section_patterns = [
            r'\n#{2,4}\s+.+\n',  # Markdown headers
            r'\n\*\*[^*]+\*\*\s*\n',  # Bold headers
            r'\n[A-Z\s]{3,}\n',  # All caps headers
            r'\n\d+\.\s+[A-Z].+\n',  # Numbered sections
        ]
        
        # Try to split by major sections
        sections = []
        current_section = ""
        lines = text.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check if this line is a section header
            is_header = False
            for pattern in section_patterns:
                if re.match(pattern.strip(), f'\n{line}\n'):
                    is_header = True
                    break
            
            if is_header and current_section.strip():
                # Save previous section and start new one
                sections.append(current_section.strip())
                current_section = line + '\n'
            else:
                current_section += line + '\n'
        
        # Add the last section
        if current_section.strip():
            sections.append(current_section.strip())
        
        # If no clear sections found, treat as one section
        if not sections:
            sections = [text]
            
        return sections
    
    def _extract_paragraphs_from_section(self, section_text: str) -> List[str]:
        """Extract paragraphs from a section of text."""
        # Split by double newlines first (natural paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', section_text)
        
        # Clean up and filter paragraphs
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            
            # Skip empty paragraphs
            if not para:
                continue
                
            # Skip paragraphs that are just headers or figures
            if self._is_header_or_figure_only(para):
                continue
                
            # Skip table of contents lines
            if self._is_table_of_contents(para):
                continue
                
            cleaned_paragraphs.append(para)
        
        return cleaned_paragraphs
    
    def _is_header_or_figure_only(self, text: str) -> bool:
        """Check if text is just a header or figure reference."""
        text_stripped = text.strip()
        
        # Check for figure references
        if re.match(r'^\!?\[.*\]\(.*\)$', text_stripped):
            return True
            
        # Check for standalone headers
        if re.match(r'^#{2,4}\s+.+$', text_stripped):
            return True
            
        # Check for bold headers only
        if re.match(r'^\*\*[^*]+\*\*\s*$', text_stripped):
            return True
            
        return False
    
    def _is_table_of_contents(self, text: str) -> bool:
        """Check if text appears to be table of contents."""
        text_lower = text.lower()
        
        # Look for common TOC patterns
        toc_indicators = [
            'table of contents',
            'overview',
            'book chapter',
            'legend',
            'abbreviations'
        ]
        
        # Check if it's a table structure
        if '|' in text and text.count('|') > 4:
            return True
            
        # Check for TOC-like structure
        for indicator in toc_indicators:
            if indicator in text_lower and len(text) < 500:
                return True
                
        return False
    
    def _extract_paragraph_title(self, paragraph_text: str) -> str:
        """Extract a meaningful title from paragraph text."""
        if not paragraph_text:
            return "Content"
        
        lines = paragraph_text.strip().split('\n')
        
        # Try different title extraction patterns
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if not line:
                continue
                
            # Pattern 1: Markdown headers
            if re.match(r'^#{2,4}\s+(.+)', line):
                title = re.sub(r'^#{2,4}\s+', '', line).strip()
                if len(title) > 3:
                    return title
            
            # Pattern 2: Bold headers
            bold_match = re.match(r'^\*\*(.+?)\*\*', line)
            if bold_match:
                title = bold_match.group(1).strip()
                if len(title) > 3 and not title.isdigit():
                    return title
            
            # Pattern 3: Numbered sections
            numbered_match = re.match(r'^\d+\.\s+(.+)', line)
            if numbered_match:
                title = numbered_match.group(1).strip()
                if len(title) > 3:
                    return title
            
            # Pattern 4: All caps headers
            if line.isupper() and len(line) > 3 and len(line) < 80:
                return line
        
        # Pattern 5: First meaningful sentence
        sentences = re.split(r'[.!?]', paragraph_text)
        for sentence in sentences[:2]:
            sentence = sentence.strip()
            if len(sentence) > 10 and len(sentence) < 100:
                # Extract key concepts
                return self._extract_key_concepts(sentence)
        
        # Fallback: use first line
        first_line = lines[0].strip()
        if len(first_line) > 10:
            return first_line[:50] + "..." if len(first_line) > 50 else first_line
        
        return "Content"
    
    def _extract_key_concepts(self, text: str) -> str:
        """Extract key medical concepts from text for title generation."""
        # Medical concept patterns
        medical_patterns = [
            r'blood.brain.barrier',
            r'sympathetic.nervous.system',
            r'cerebral.blood.flow',
            r'cerebrospinal.fluid',
            r'autoregulation',
            r'microcirculation',
            r'choroid.plexus',
            r'arachnoid.villi',
            r'brain.edema',
            r'hydrocephalus'
        ]
        
        text_lower = text.lower()
        
        for pattern in medical_patterns:
            if re.search(pattern, text_lower):
                # Extract the concept and format it nicely
                match = re.search(pattern, text_lower)
                if match:
                    concept = match.group(0).replace('.', ' ').title()
                    return f"{concept} Function"
        
        # Extract first key noun phrase
        noun_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', text)
        if noun_phrases:
            return noun_phrases[0]
        
        return "Medical Concept"
    
    def extract_paragraphs_from_sources(self, sources: List[Dict[str, Any]]) -> List[Paragraph]:
        """
        Extract paragraphs from multiple RAG sources.
        
        Args:
            sources: List of source dictionaries from RAG system
            
        Returns:
            List of all extracted paragraphs
        """
        all_paragraphs = []
        
        for source in sources:
            chunk_text = source.get('document', '')
            chunk_metadata = source.get('metadata', {})
            
            paragraphs = self.extract_paragraphs_from_chunk(chunk_text, chunk_metadata)
            all_paragraphs.extend(paragraphs)
        
        logger.info(f"Extracted {len(all_paragraphs)} total paragraphs from {len(sources)} sources")
        return all_paragraphs