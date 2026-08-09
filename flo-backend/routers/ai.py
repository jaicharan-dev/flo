import os
from fastapi import APIRouter, HTTPException
from google.antigravity import Agent, LocalAgentConfig
from dotenv import load_dotenv

# Load environment variables (this will pull your GEMINI_API_KEY)
load_dotenv()

router = APIRouter(
    prefix="/ai",
    tags=["AI Agent"]
)

@router.get("/test")
async def test_ai():
    try:
        # Initialize the Antigravity configuration
        config = LocalAgentConfig()
        
        # Open an async context manager for the Agent
        async with Agent(config) as agent:
            # Send a prompt to the agent
            response = await agent.chat("Say hello from Flo AI!")
            
            # Await the text generation natively
            text = await response.text()
            
            return {"status": "success", "ai_response": text}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Antigravity AI Error: {str(e)}")