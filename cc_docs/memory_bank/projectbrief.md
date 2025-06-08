# Project Brief: MedMind - AI-Powered Medical Education Platform

## Core Requirements

**Primary Goal**: Create a comprehensive multi-agent AI tutoring system for physiology education that provides adaptive learning experiences including quiz generation, progress tracking, and intelligent tutoring for medical students.

## Key Capabilities

1. **Multi-Agent Architecture**: Specialized PydanticAI agents for coordinated learning assistance
   - **Coordinator Agent**: Routes requests and orchestrates learning experiences
   - **Quiz Agent**: Generates adaptive quizzes with difficulty progression
   - **Progress Agent**: Tracks learning analytics and spaced repetition
   - **Tutor Agent**: Provides personalized explanations and Q&A
   - **Validation Agent**: Ensures medical accuracy and fact-checking

2. **Foundation RAG System**: Convert physiology PDFs to structured knowledge base
3. **Adaptive Learning**: Personalized difficulty, spaced repetition, mastery tracking
4. **Type-Safe Operations**: Pydantic models for validated inputs/outputs throughout

## Success Criteria

- ✅ **Foundation Complete**: RAG system with 13 physiology documents, 643 chunks, working vector database
- 🔄 **Agent Architecture**: PydanticAI multi-agent system with specialized learning agents
- 🔄 **Adaptive Learning**: Quiz generation, progress tracking, spaced repetition algorithms
- 🔄 **Type Safety**: Pydantic models ensuring validated operations throughout
- ✅ **Professional Structure**: Clean package architecture, environment-based config, comprehensive testing

## Current Status

**ARCHITECTURAL TRANSFORMATION IN PROGRESS**: Converting from monolithic RAG system to multi-agent PydanticAI architecture. Foundation RAG system operational, now implementing specialized learning agents for comprehensive educational experience.

**Next Phase**: Coordinator Agent + Quiz Agent implementation to establish agentic foundation.

## Scope Boundaries

- **Focus**: Physiology education with potential expansion to other medical subjects
- **AI Framework**: PydanticAI for agent coordination + Google Gemini for LLM capabilities
- **Target Users**: Medical students seeking adaptive, personalized learning assistance
- **Architecture**: Multi-agent system with specialized educational roles
- **Deployment**: Self-contained package with potential institutional scaling