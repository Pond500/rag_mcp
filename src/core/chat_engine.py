"""Chat Engine - LLM Chat with Conversation History

Manages conversation history and generates answers using LLM.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChatEngine:
    """LLM chat engine with conversation memory
    
    Usage:
        chat_engine = ChatEngine(
            llm_client=llm_client,
            config=settings.chat
        )
        
        response = chat_engine.chat(
            query="อาวุธปืนต้องขออนุญาตอย่างไร",
            context=["มาตรา 3 ห้ามมิให้ผู้ใดมีอาวุธปืน..."],
            history=[{"role": "user", "content": "..."}],
            session_id="session_123"
        )
    """
    
    def __init__(self, llm_client, config=None):
        self.llm_client = llm_client
        
        # Config with defaults
        self.system_prompt = getattr(config, "system_prompt", "") if config else ""
        self.memory_token_limit = getattr(config, "memory_token_limit", 3000) if config else 3000
        
        # In-memory conversation storage (simple dict)
        # In production, use Redis or database
        self._sessions: Dict[str, List[Dict[str, Any]]] = {}
    
    def chat(
        self,
        query: str,
        context: Optional[List[str]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        session_id: Optional[str] = None,
        qa_prompt_template: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate answer using LLM
        
        Args:
            query: User query
            context: Retrieved context documents
            history: Conversation history [{"role": "user/assistant", "content": "..."}]
            session_id: Session ID for storing conversation
            qa_prompt_template: Optional QA prompt template (with {context} and {query} placeholders)
            
        Returns:
            {
                "answer": "...",
                "model": "gpt-4o-mini",
                "context_used": ["..."],
                "session_id": "...",
                "timestamp": "..."
            }
        """
        try:
            # Get or create session history
            if session_id:
                if session_id not in self._sessions:
                    self._sessions[session_id] = []
                history = self._sessions[session_id]
            else:
                history = history or []
            
            # Build prompt
            prompt = self._build_prompt(
                query=query,
                context=context,
                history=history,
                qa_prompt_template=qa_prompt_template
            )
            
            # Generate answer
            response = self.llm_client.generate(prompt)
            answer = response.get("text", "")
            
            # Store in session history
            if session_id:
                self._sessions[session_id].append({
                    "role": "user",
                    "content": query,
                    "timestamp": datetime.now().isoformat()
                })
                self._sessions[session_id].append({
                    "role": "assistant",
                    "content": answer,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Trim history if too long
                self._trim_history(session_id)
            
            # Extract token usage from OpenAI response
            usage = response.get("usage")
            tokens = {}
            if usage:
                tokens = {
                    "input": getattr(usage, "prompt_tokens", 0),
                    "output": getattr(usage, "completion_tokens", 0),
                    "total": getattr(usage, "total_tokens", 0)
                }
            
            logger.info("Generated answer: %d chars (model: %s, tokens: %s)", 
                       len(answer), response.get("model", "unknown"), tokens)
            
            return {
                "answer": answer,
                "model": response.get("model", "unknown"),
                "context_used": context or [],
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "tokens": tokens
            }
            
        except Exception as e:
            logger.error("Chat failed: %s", e)
            return {
                "answer": f"ขออภัย เกิดข้อผิดพลาด: {str(e)}",
                "model": "error",
                "context_used": [],
                "tokens": {},
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
    
    def _build_prompt(
        self,
        query: str,
        context: Optional[List[str]],
        history: Optional[List[Dict[str, str]]],
        qa_prompt_template: Optional[str]
    ) -> str:
        """Build prompt with system, history, context, and query"""
        parts = []
        
        # System prompt
        if self.system_prompt:
            parts.append(self.system_prompt)
        
        # Conversation history (recent only)
        if history:
            recent_history = history[-10:]  # Last 10 turns
            for turn in recent_history:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role == "user":
                    parts.append(f"User: {content}")
                else:
                    parts.append(f"Assistant: {content}")
        
        # Context from retrieval
        if context:
            context_text = "\n\n".join(context)
            
            # Use custom template or default
            if qa_prompt_template:
                # Replace placeholders
                qa_part = qa_prompt_template.format(
                    context=context_text,
                    query=query
                )
                parts.append(qa_part)
            else:
                # Default QA prompt
                parts.append(f"Context:\n{context_text}")
                parts.append(f"\nQuestion: {query}\n\nAnswer:")
        else:
            # No context - just answer
            parts.append(f"Question: {query}\n\nAnswer:")
        
        return "\n\n".join(parts)
    
    def _trim_history(self, session_id: str):
        """Trim conversation history to stay under token limit"""
        if session_id not in self._sessions:
            return
        
        history = self._sessions[session_id]
        
        # Simple token estimation: ~4 chars per token
        total_chars = sum(len(turn.get("content", "")) for turn in history)
        estimated_tokens = total_chars / 4
        
        # Trim from oldest if over limit
        while estimated_tokens > self.memory_token_limit and len(history) > 2:
            history.pop(0)  # Remove oldest turn
            total_chars = sum(len(turn.get("content", "")) for turn in history)
            estimated_tokens = total_chars / 4
        
        logger.debug("Session %s: %d turns, ~%d tokens",
                    session_id, len(history), int(estimated_tokens))
    
    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for session"""
        return self._sessions.get(session_id, [])
    
    def clear_history(self, session_id: str) -> bool:
        """Clear conversation history for session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("Cleared history for session: %s", session_id)
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """List all active session IDs"""
        return list(self._sessions.keys())
    
    def rewrite_query(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
        rewrite_prompt_template: Optional[str] = None
    ) -> str:
        """Rewrite query using conversation history
        
        Useful for resolving pronouns and references (e.g., "มันต้องทำอย่างไร" → "อาวุธปืนต้องทำอย่างไร")
        
        Args:
            query: Original query
            history: Conversation history
            rewrite_prompt_template: Optional template (with {history} and {query} placeholders)
            
        Returns:
            Rewritten query
        """
        if not history or len(history) == 0:
            return query  # No history, return as-is
        
        try:
            # Build prompt
            if rewrite_prompt_template:
                history_text = "\n".join([
                    f"{turn['role']}: {turn['content']}"
                    for turn in history[-5:]  # Last 5 turns
                ])
                prompt = rewrite_prompt_template.format(
                    history=history_text,
                    query=query
                )
            else:
                # Default prompt
                history_text = "\n".join([
                    f"{turn['role']}: {turn['content']}"
                    for turn in history[-5:]
                ])
                prompt = f"""Given the conversation history, rewrite the query to be standalone:

History:
{history_text}

Query: {query}

Rewritten query:"""
            
            response = self.llm_client.generate(prompt, max_tokens=100)
            rewritten = response.get("text", "").strip()
            
            if rewritten and len(rewritten) > 5:
                logger.info("Rewrote query: '%s' → '%s'", query[:50], rewritten[:50])
                return rewritten
            else:
                return query
                
        except Exception as e:
            logger.error("Query rewrite failed: %s", e)
            return query
