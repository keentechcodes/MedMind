"""
Answer Attribution Mapping for precise citation granularity.
Maps specific parts of LLM answers to the exact paragraphs that support them.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

import google.generativeai as genai
from physiology_rag.core.paragraph_extractor import Paragraph
from physiology_rag.utils.logging import get_logger

logger = get_logger("answer_attribution")


@dataclass
class Attribution:
    """Maps an answer segment to supporting paragraphs."""
    answer_segment: str
    supporting_paragraphs: List[int]  # Indices of paragraphs that support this segment
    confidence: float
    attribution_type: str  # 'direct', 'inferred', 'synthesized'


@dataclass
class AttributedAnswer:
    """An answer with precise paragraph-level attributions."""
    answer: str
    attributions: List[Attribution]
    paragraphs: List[Paragraph]
    overall_confidence: float


class AnswerAttributionMapper:
    """
    Maps LLM-generated answers to specific supporting paragraphs using Gemini.
    Provides precise citations for each part of the answer.
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize the answer attribution mapper.
        
        Args:
            api_key: Gemini API key
            model_name: Model to use for attribution mapping
        """
        self.api_key = api_key
        self.model_name = model_name
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        logger.info(f"Initialized AnswerAttributionMapper with {model_name}")
    
    async def create_attributed_answer(
        self,
        question: str,
        answer: str,
        paragraphs: List[Paragraph]
    ) -> AttributedAnswer:
        """
        Create an answer with precise paragraph-level attributions.
        
        Args:
            question: The original question
            answer: The generated answer
            paragraphs: Available paragraphs for attribution
            
        Returns:
            AttributedAnswer with precise citations
        """
        logger.info(f"Creating attributed answer for: {question[:50]}...")
        
        try:
            # Split answer into logical segments
            answer_segments = self._split_answer_into_segments(answer)
            logger.info(f"Split answer into {len(answer_segments)} segments")
            
            # Map each segment to supporting paragraphs
            attributions = []
            for i, segment in enumerate(answer_segments):
                attribution = await self._map_segment_to_paragraphs(
                    question, segment, paragraphs, i
                )
                if attribution:
                    attributions.append(attribution)
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(attributions)
            
            attributed_answer = AttributedAnswer(
                answer=answer,
                attributions=attributions,
                paragraphs=paragraphs,
                overall_confidence=overall_confidence
            )
            
            logger.info(f"Created attributed answer with {len(attributions)} attributions")
            return attributed_answer
            
        except Exception as e:
            logger.error(f"Error creating attributed answer: {e}")
            # Return fallback with basic attribution
            return self._create_fallback_attribution(answer, paragraphs)
    
    def _split_answer_into_segments(self, answer: str) -> List[str]:
        """Split answer into logical segments for attribution."""
        # Split by clear logical boundaries
        segments = []
        
        # First try to split by major sections (marked by **headers**)
        section_pattern = r'\*\*([^*]+)\*\*'
        sections = re.split(section_pattern, answer)
        
        if len(sections) > 3:  # If we found clear sections
            current_segment = ""
            for i, section in enumerate(sections):
                if i % 2 == 0:  # Regular text
                    current_segment += section
                else:  # Header
                    if current_segment.strip():
                        segments.append(current_segment.strip())
                    current_segment = f"**{section}**"
            
            if current_segment.strip():
                segments.append(current_segment.strip())
        
        else:
            # Fall back to paragraph splitting
            paragraphs = answer.split('\n\n')
            segments = [p.strip() for p in paragraphs if p.strip()]
        
        # Filter out very short segments
        segments = [s for s in segments if len(s) > 50]
        
        # If still no good segments, split by sentences
        if not segments:
            sentences = re.split(r'[.!?]+', answer)
            segments = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        return segments[:10]  # Limit to prevent too many API calls
    
    async def _map_segment_to_paragraphs(
        self,
        question: str,
        segment: str,
        paragraphs: List[Paragraph],
        segment_index: int
    ) -> Optional[Attribution]:
        """Map an answer segment to supporting paragraphs using Gemini."""
        
        try:
            # Create context for Gemini
            paragraph_context = []
            for i, paragraph in enumerate(paragraphs):
                paragraph_context.append({
                    'index': i,
                    'title': paragraph.title,
                    'content': paragraph.content[:500],  # Limit content for API
                    'document': paragraph.document_name
                })
            
            # Create attribution prompt
            prompt = self._create_attribution_prompt(
                question, segment, paragraph_context
            )
            
            # Get attribution mapping from Gemini
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                attribution = self._parse_attribution_response(
                    response.text, segment, len(paragraphs)
                )
                return attribution
            
        except Exception as e:
            logger.error(f"Error mapping segment to paragraphs: {e}")
        
        return None
    
    def _create_attribution_prompt(
        self,
        question: str,
        segment: str,
        paragraph_context: List[Dict[str, Any]]
    ) -> str:
        """Create prompt for Gemini to map answer segment to paragraphs."""
        
        context_text = "\n".join([
            f"Paragraph {p['index']}: {p['title']}\n{p['content']}\n---"
            for p in paragraph_context
        ])
        
        prompt = f"""You are an expert medical citation system. Your task is to identify which paragraphs from the provided medical documents support a specific part of an answer.

QUESTION: {question}

ANSWER SEGMENT TO ANALYZE:
{segment}

AVAILABLE PARAGRAPHS:
{context_text}

TASK: Determine which paragraphs (by index number) directly support the claims made in the answer segment above.

RESPOND WITH A JSON OBJECT ONLY:
{{
    "supporting_paragraph_indices": [list of paragraph indices that support this segment],
    "confidence": number between 0.0 and 1.0,
    "attribution_type": "direct" or "inferred" or "synthesized",
    "reasoning": "brief explanation of why these paragraphs support the segment"
}}

GUIDELINES:
- "direct": Information is explicitly stated in the paragraphs
- "inferred": Information can be reasonably inferred from the paragraphs  
- "synthesized": Information combines ideas from multiple paragraphs
- Only include paragraph indices that actually support the segment
- Be precise - don't include paragraphs that are only tangentially related
- Confidence should reflect how well the paragraphs support the segment"""

        return prompt
    
    def _parse_attribution_response(
        self,
        response_text: str,
        segment: str,
        total_paragraphs: int
    ) -> Optional[Attribution]:
        """Parse Gemini's attribution response."""
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in attribution response")
                return None
            
            attribution_data = json.loads(json_match.group(0))
            
            # Validate and extract data
            supporting_indices = attribution_data.get('supporting_paragraph_indices', [])
            confidence = float(attribution_data.get('confidence', 0.0))
            attribution_type = attribution_data.get('attribution_type', 'direct')
            
            # Validate indices
            valid_indices = [
                idx for idx in supporting_indices 
                if isinstance(idx, int) and 0 <= idx < total_paragraphs
            ]
            
            if not valid_indices:
                logger.warning("No valid paragraph indices found")
                return None
            
            return Attribution(
                answer_segment=segment,
                supporting_paragraphs=valid_indices,
                confidence=confidence,
                attribution_type=attribution_type
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing attribution response: {e}")
            return None
    
    def _calculate_overall_confidence(self, attributions: List[Attribution]) -> float:
        """Calculate overall confidence from individual attributions."""
        if not attributions:
            return 0.0
        
        # Weighted average based on segment length
        total_weight = 0
        weighted_confidence = 0
        
        for attribution in attributions:
            weight = len(attribution.answer_segment)
            weighted_confidence += attribution.confidence * weight
            total_weight += weight
        
        return weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def _create_fallback_attribution(
        self,
        answer: str,
        paragraphs: List[Paragraph]
    ) -> AttributedAnswer:
        """Create fallback attribution when mapping fails."""
        
        # Simple fallback - attribute entire answer to all paragraphs
        attribution = Attribution(
            answer_segment=answer,
            supporting_paragraphs=list(range(len(paragraphs))),
            confidence=0.5,
            attribution_type="synthesized"
        )
        
        return AttributedAnswer(
            answer=answer,
            attributions=[attribution],
            paragraphs=paragraphs,
            overall_confidence=0.5
        )
    
    def format_attributed_answer_for_display(
        self,
        attributed_answer: AttributedAnswer
    ) -> Dict[str, Any]:
        """Format attributed answer for display in UI."""
        
        formatted_attributions = []
        for attribution in attributed_answer.attributions:
            # Get supporting paragraph details
            supporting_paragraphs = []
            for idx in attribution.supporting_paragraphs:
                if idx < len(attributed_answer.paragraphs):
                    paragraph = attributed_answer.paragraphs[idx]
                    supporting_paragraphs.append({
                        'title': paragraph.title,
                        'document': paragraph.document_name,
                        'content_preview': paragraph.content[:200] + "..." if len(paragraph.content) > 200 else paragraph.content,
                        'confidence': attribution.confidence,
                        'type': attribution.attribution_type
                    })
            
            formatted_attributions.append({
                'segment': attribution.answer_segment,
                'supporting_paragraphs': supporting_paragraphs,
                'confidence': attribution.confidence,
                'type': attribution.attribution_type
            })
        
        return {
            'answer': attributed_answer.answer,
            'attributions': formatted_attributions,
            'overall_confidence': attributed_answer.overall_confidence,
            'total_segments': len(attributed_answer.attributions),
            'total_paragraphs': len(attributed_answer.paragraphs)
        }