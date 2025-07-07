"""
Advanced chunking strategies for medical documents.
Implements semantic chunking with medical concept awareness and overlapping windows.
"""

import re
import json
from typing import List, Dict, Any, Set, Tuple
from pathlib import Path
from dataclasses import dataclass

from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger

logger = get_logger("advanced_chunking")


@dataclass
class ChunkMetadata:
    """Metadata for advanced chunks."""
    start_idx: int
    end_idx: int
    medical_concepts: List[str]
    section_hierarchy: List[str]
    concept_density: float
    overlap_with_previous: bool = False
    overlap_with_next: bool = False


class MedicalConceptDetector:
    """Detects medical concepts and terminology in text."""
    
    def __init__(self):
        """Initialize with medical terminology patterns."""
        self.medical_patterns = {
            'anatomy': [
                r'\b(?:cortex|cerebral|cerebellum|brainstem|hippocampus|amygdala)\b',
                r'\b(?:neuron|synapse|axon|dendrite|myelin|glia)\b',
                r'\b(?:heart|lung|kidney|liver|spleen|stomach|intestine)\b',
                r'\b(?:artery|vein|capillary|vessel|circulation)\b',
                r'\b(?:muscle|bone|joint|cartilage|tendon|ligament)\b',
            ],
            'physiology': [
                r'\b(?:homeostasis|metabolism|respiration|circulation|digestion)\b',
                r'\b(?:action\s+potential|depolarization|repolarization)\b',
                r'\b(?:hormone|enzyme|receptor|channel|transporter)\b',
                r'\b(?:blood\s+pressure|heart\s+rate|stroke\s+volume)\b',
                r'\b(?:filtration|reabsorption|secretion|excretion)\b',
            ],
            'pathology': [
                r'\b(?:disease|disorder|syndrome|condition|pathology)\b',
                r'\b(?:inflammation|infection|tumor|cancer|neoplasm)\b',
                r'\b(?:hypertension|diabetes|stroke|myocardial\s+infarction)\b',
                r'\b(?:arrhythmia|bradycardia|tachycardia|fibrillation)\b',
            ],
            'pharmacology': [
                r'\b(?:drug|medication|pharmaceutical|therapeutic)\b',
                r'\b(?:agonist|antagonist|inhibitor|activator)\b',
                r'\b(?:absorption|distribution|metabolism|excretion)\b',
                r'\b(?:dose|dosage|concentration|bioavailability)\b',
            ]
        }
        
        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for category, patterns in self.medical_patterns.items():
            self.compiled_patterns[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        logger.info("Initialized MedicalConceptDetector with medical terminology patterns")
    
    def detect_concepts(self, text: str) -> Dict[str, List[str]]:
        """
        Detect medical concepts in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary of detected concepts by category
        """
        detected = {}
        
        for category, patterns in self.compiled_patterns.items():
            matches = set()
            for pattern in patterns:
                found = pattern.findall(text)
                matches.update(found)
            detected[category] = list(matches)
        
        return detected
    
    def calculate_concept_density(self, text: str) -> float:
        """
        Calculate density of medical concepts in text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Concept density score (0-1)
        """
        if not text:
            return 0.0
        
        total_concepts = 0
        for category_concepts in self.detect_concepts(text).values():
            total_concepts += len(category_concepts)
        
        # Normalize by text length (concepts per 100 words)
        words = len(text.split())
        if words == 0:
            return 0.0
        
        density = min(total_concepts / (words / 100), 1.0)
        return density
    
    def is_medical_boundary(self, text_before: str, text_after: str) -> bool:
        """
        Determine if there's a medical concept boundary between two text segments.
        
        Args:
            text_before: Text before potential boundary
            text_after: Text after potential boundary
            
        Returns:
            True if boundary exists between different medical concepts
        """
        concepts_before = self.detect_concepts(text_before)
        concepts_after = self.detect_concepts(text_after)
        
        # Check if concepts differ significantly
        all_before = set()
        all_after = set()
        
        for concepts in concepts_before.values():
            all_before.update(concepts)
        
        for concepts in concepts_after.values():
            all_after.update(concepts)
        
        # Calculate concept overlap
        if not all_before and not all_after:
            return False
        
        overlap = len(all_before & all_after)
        total = len(all_before | all_after)
        
        if total == 0:
            return False
        
        # If overlap is less than 50%, consider it a boundary
        return (overlap / total) < 0.5


class SemanticChunker:
    """Advanced chunking with semantic boundaries and medical concept awareness."""
    
    def __init__(self, chunk_size: int = 1000, overlap_ratio: float = 0.1):
        """
        Initialize semantic chunker.
        
        Args:
            chunk_size: Target chunk size in characters
            overlap_ratio: Ratio of overlap between chunks (0-0.5)
        """
        self.chunk_size = chunk_size
        self.overlap_ratio = min(overlap_ratio, 0.5)  # Cap at 50%
        self.overlap_size = int(chunk_size * overlap_ratio)
        
        self.concept_detector = MedicalConceptDetector()
        
        logger.info(f"Initialized SemanticChunker with chunk_size={chunk_size}, overlap_ratio={overlap_ratio}")
    
    def find_semantic_boundaries(self, text: str) -> List[int]:
        """
        Find semantic boundaries in text for optimal chunking.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of character positions for semantic boundaries
        """
        boundaries = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_pos = 0
        for i, sentence in enumerate(sentences):
            # Check for paragraph boundaries
            if '\n\n' in sentence:
                boundaries.append(current_pos + sentence.find('\n\n'))
            
            # Check for medical concept boundaries
            if i > 0:
                prev_sentence = sentences[i-1]
                if self.concept_detector.is_medical_boundary(prev_sentence, sentence):
                    boundaries.append(current_pos)
            
            current_pos += len(sentence) + 1  # +1 for space
        
        return sorted(set(boundaries))
    
    def create_overlapping_chunks(
        self, 
        text: str, 
        boundaries: List[int],
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Create overlapping chunks with semantic boundaries.
        
        Args:
            text: Input text to chunk
            boundaries: List of semantic boundary positions
            metadata: Additional metadata for chunks
            
        Returns:
            List of chunk dictionaries with metadata
        """
        chunks = []
        text_length = len(text)
        
        # Add start and end boundaries
        all_boundaries = [0] + boundaries + [text_length]
        all_boundaries = sorted(set(all_boundaries))
        
        i = 0
        while i < len(all_boundaries) - 1:
            chunk_start = all_boundaries[i]
            chunk_end = chunk_start + self.chunk_size
            
            # Find the best boundary within chunk size
            best_boundary = None
            for boundary in all_boundaries:
                if chunk_start < boundary <= chunk_end:
                    best_boundary = boundary
                elif boundary > chunk_end:
                    break
            
            if best_boundary:
                chunk_end = best_boundary
            else:
                # If no boundary found, use chunk size but try to break at sentence
                chunk_text = text[chunk_start:chunk_end]
                last_sentence = chunk_text.rfind('. ')
                if last_sentence > self.chunk_size * 0.7:  # At least 70% of chunk size
                    chunk_end = chunk_start + last_sentence + 2
            
            # Ensure we don't exceed text length
            chunk_end = min(chunk_end, text_length)
            
            if chunk_start >= chunk_end:
                break
            
            chunk_text = text[chunk_start:chunk_end]
            
            # Detect medical concepts in chunk
            concepts = self.concept_detector.detect_concepts(chunk_text)
            all_concepts = []
            for concept_list in concepts.values():
                all_concepts.extend(concept_list)
            
            # Create chunk metadata
            chunk_metadata = ChunkMetadata(
                start_idx=chunk_start,
                end_idx=chunk_end,
                medical_concepts=all_concepts,
                section_hierarchy=metadata.get('section_hierarchy', []) if metadata else [],
                concept_density=self.concept_detector.calculate_concept_density(chunk_text),
                overlap_with_previous=chunk_start > 0 and chunk_start < all_boundaries[i] + self.overlap_size,
                overlap_with_next=chunk_end < text_length
            )
            
            chunk_dict = {
                'text': chunk_text,
                'type': 'semantic',
                'size': len(chunk_text),
                'start_idx': chunk_start,
                'end_idx': chunk_end,
                'medical_concepts': all_concepts,
                'concept_density': chunk_metadata.concept_density,
                'overlap_previous': chunk_metadata.overlap_with_previous,
                'overlap_next': chunk_metadata.overlap_with_next
            }
            
            # Add original metadata
            if metadata:
                chunk_dict.update({
                    'title': metadata.get('title', ''),
                    'page_id': metadata.get('page_id', 0),
                    'section_hierarchy': metadata.get('section_hierarchy', [])
                })
            
            chunks.append(chunk_dict)
            
            # Move to next chunk with overlap
            if chunk_end >= text_length:
                break
            
            # Calculate next start position with overlap
            next_start = max(chunk_end - self.overlap_size, chunk_start + 1)
            
            # Find the next boundary index
            next_boundary_idx = None
            for j, boundary in enumerate(all_boundaries):
                if boundary > next_start:
                    next_boundary_idx = j
                    break
            
            if next_boundary_idx is None:
                break
            
            i = next_boundary_idx - 1 if next_boundary_idx > 0 else 0
        
        logger.info(f"Created {len(chunks)} overlapping semantic chunks")
        return chunks
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Main chunking method with semantic boundaries.
        
        Args:
            text: Input text to chunk
            metadata: Additional metadata for chunks
            
        Returns:
            List of chunk dictionaries
        """
        if not text or len(text) < 50:  # Skip very short texts
            return []
        
        # Find semantic boundaries
        boundaries = self.find_semantic_boundaries(text)
        
        # Create overlapping chunks
        chunks = self.create_overlapping_chunks(text, boundaries, metadata)
        
        # Filter out chunks that are too small
        min_chunk_size = max(100, self.chunk_size * 0.1)
        filtered_chunks = [chunk for chunk in chunks if chunk['size'] >= min_chunk_size]
        
        logger.info(f"Filtered {len(chunks)} chunks to {len(filtered_chunks)} (min_size={min_chunk_size})")
        
        return filtered_chunks


class AdvancedDocumentProcessor:
    """Enhanced document processor with advanced chunking capabilities."""
    
    def __init__(self, chunk_size: int = 1000, overlap_ratio: float = 0.1):
        """
        Initialize advanced document processor.
        
        Args:
            chunk_size: Target chunk size in characters
            overlap_ratio: Overlap ratio between chunks
        """
        self.chunker = SemanticChunker(chunk_size, overlap_ratio)
        self.concept_detector = MedicalConceptDetector()
        
        logger.info("Initialized AdvancedDocumentProcessor")
    
    def process_document_with_advanced_chunking(
        self, 
        text: str, 
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Process document with advanced chunking strategies.
        
        Args:
            text: Document text to process
            metadata: Document metadata
            
        Returns:
            List of advanced chunks with enriched metadata
        """
        logger.info("Processing document with advanced chunking")
        
        # Use semantic chunking
        chunks = self.chunker.chunk_text(text, metadata)
        
        # Enhance chunks with additional analysis
        enhanced_chunks = []
        for i, chunk in enumerate(chunks):
            # Add chunk index and relationships
            chunk['chunk_index'] = i
            chunk['total_chunks'] = len(chunks)
            
            # Add concept analysis
            chunk['concept_analysis'] = self.concept_detector.detect_concepts(chunk['text'])
            
            # Add readability metrics (simple implementation)
            chunk['readability_score'] = self._calculate_readability(chunk['text'])
            
            # Add relationship flags
            chunk['is_concept_dense'] = chunk['concept_density'] > 0.3
            chunk['is_transition_chunk'] = chunk.get('overlap_previous', False) or chunk.get('overlap_next', False)
            
            enhanced_chunks.append(chunk)
        
        logger.info(f"Created {len(enhanced_chunks)} enhanced chunks with advanced analysis")
        return enhanced_chunks
    
    def _calculate_readability(self, text: str) -> float:
        """
        Calculate simple readability score for text.
        
        Args:
            text: Input text
            
        Returns:
            Readability score (0-1, higher is more readable)
        """
        if not text:
            return 0.0
        
        # Simple metrics: average sentence length and word complexity
        sentences = re.split(r'[.!?]+', text)
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        
        # Count complex words (>6 characters)
        complex_words = sum(1 for word in words if len(word) > 6)
        complexity_ratio = complex_words / len(words) if words else 0
        
        # Simple readability score (inverse of complexity)
        readability = max(0, 1 - (avg_sentence_length / 20) - complexity_ratio)
        return min(readability, 1.0)


def main():
    """CLI entry point for testing advanced chunking."""
    processor = AdvancedDocumentProcessor(chunk_size=800, overlap_ratio=0.15)
    
    # Test with sample medical text
    sample_text = """
    The cerebral cortex is the outermost layer of the brain, composed of gray matter containing neuronal cell bodies. 
    It plays a crucial role in higher-order brain functions such as cognition, memory, and consciousness.
    
    The cortex is divided into four main lobes: frontal, parietal, temporal, and occipital. Each lobe has specific functions.
    The frontal lobe is responsible for executive functions, decision-making, and motor control.
    
    Neurons in the cerebral cortex communicate through synapses, forming complex neural networks.
    Action potentials travel along axons, transmitting electrical signals between neurons.
    Neurotransmitters are released at synapses to facilitate communication.
    
    The blood-brain barrier protects the brain from harmful substances while allowing essential nutrients to pass through.
    This selective permeability is crucial for maintaining brain homeostasis and proper neuronal function.
    """
    
    chunks = processor.process_document_with_advanced_chunking(
        sample_text, 
        metadata={'title': 'Cerebral Cortex Overview', 'page_id': 1}
    )
    
    print(f"Created {len(chunks)} advanced chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Size: {chunk['size']} characters")
        print(f"Medical concepts: {len(chunk['medical_concepts'])}")
        print(f"Concept density: {chunk['concept_density']:.2f}")
        print(f"Readability: {chunk['readability_score']:.2f}")
        print(f"Text preview: {chunk['text'][:100]}...")


if __name__ == "__main__":
    main()