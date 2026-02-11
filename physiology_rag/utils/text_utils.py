"""
Text utility functions for the RAG system.
"""


def extract_topics_from_query(query: str) -> list:
    """
    Extract medical topics from query.
    
    Searches for common medical terms in the query and returns
    a list of matching topics.
    
    Args:
        query: The user's search query
        
    Returns:
        List of medical topics found in the query
    """
    medical_terms = [
        "neurophysiology", "cardiovascular", "respiratory", "endocrine",
        "musculoskeletal", "digestive", "renal", "immune", "reproduction",
        "metabolism", "homeostasis", "synapse", "neuron", "hormone",
        "blood", "heart", "lung", "kidney", "muscle", "bone",
        "cortex", "brain", "nervous", "circulation"
    ]
    
    query_lower = query.lower()
    return [term for term in medical_terms if term in query_lower]
