"""
Assistant Route — POST /assistant/chat
"""
from fastapi import APIRouter
from pydantic import BaseModel
from services.assistant.assistant_service import chat

router = APIRouter(tags=["Assistant"])


class ChatRequest(BaseModel):
    message: str


@router.post("/assistant/chat")
def assistant_chat(req: ChatRequest):
    return chat(req.message)
