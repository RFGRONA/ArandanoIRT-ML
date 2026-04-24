from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ChatRequest(BaseModel):
    question: str
    iot_context: Optional[str] = None
    expertise_level: Optional[str] = "AGRONOMO"

class LogEntry(BaseModel):
    observation_id: str
    text_content: str
    metadata: Optional[Dict[str, Any]] = None

class BatchIngestLogRequest(BaseModel):
    logs: List[LogEntry]

class UpdateApiKeyRequest(BaseModel):
    api_key: str
