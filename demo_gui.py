from collections import Counter
import json
import random
from typing import Literal
import os
import tempfile
import time
from pathlib import Path
import argparse
from typing import Optional
import uuid

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

parser = argparse.ArgumentParser()
parser.add_argument("--base_config", type=str, required=True)
parser.add_argument("--model_config", type=str, required=True)
args = parser.parse_args()

from hydra_vl4ai.util.config import Config

Config.base_config_path = args.base_config
Config.model_config_path = args.model_config
Config.debug = True

from hydra_vl4ai.execution.toolbox import Toolbox
from hydra_vl4ai.util.console import logger
from naver import Naver
from naver.agent.states import States, State
from naver.context import Context


SystemState = Literal["IDLE", "BUSY", "STOPPED"]


class ExecutionState(BaseModel):
    session_id: str
    current_state: SystemState = "IDLE"
    error: Optional[str] = None


class StateInfo(BaseModel):
    current_state: str | None  # the class name of the State
    history: list[str]


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.session_states: dict[str, ExecutionState] = {}
        self.naver_instances: dict[str, Naver] = {}
        self.naver_prev_state: dict[str, State | None] = {}
        self.state_info: dict[str, StateInfo] = {}

    async def create(self, session_id: str, image_path: str, query: str) -> None:
        try:
            logger.info(f"Creating Naver agent for session: {session_id}")
            self.naver_instances[session_id] = Naver(image_path, query)
            self.naver_prev_state[session_id] = None
            self.session_states[session_id] = ExecutionState(session_id=session_id)
            self.state_info[session_id] = StateInfo(current_state=None, history=[])
            logger.info(f"Naver agent created successfully for session: {session_id}")
        except Exception as e:
            logger.error(f"Error creating Naver agent for session {session_id}: {e}")
            raise
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_states[session_id] = ExecutionState(session_id=session_id)
        logger.info(f"WebSocket connected for session: {session_id}")
    
    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            socket = self.active_connections[session_id]
            await socket.close()
            del self.active_connections[session_id]
            del socket
        if session_id in self.session_states:
            del self.session_states[session_id]
        if session_id in self.naver_instances:
            del self.naver_instances[session_id]
        if session_id in self.state_info:
            del self.state_info[session_id]
        logger.info(f"WebSocket disconnected for session: {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        websocket = self.active_connections.get(session_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
    
    async def broadcast_to_session(self, session_id: str, message_type: str, data: dict):
        message = {
            "type": message_type,
            "data": data,
            "timestamp": time.time()
        }
        await self.send_message(session_id, message)
    

# Initialize Toolbox for NAVER
Toolbox.init(["naver.tool"])

# Global connection manager
manager = ConnectionManager()

# Initialize FastAPI app
app = FastAPI(
    title="NAVER Agent Execution Platform",
    description="Real-time visualization platform for NAVER agent execution",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the built SvelteKit frontend
frontend_build_path = Path("gui/build")
if not frontend_build_path.exists():
    print("Frontend not built. Run 'cd gui && npm run build' first.")
    exit(1)

# used to visualize the agent messages
class ExecutionMessage(BaseModel):
    type: Literal["thinking", "action", "result"]
    content: str

# each type includes multiple templates to make it more diversed
message_templates = {
    "initial_input": [
        "As user requested for {query} in the image, I'm starting to look for it. I need to start with initial perception.",
        "Let me begin searching for {query} in this image. First, I'll perform an initial perception scan.",
        "I've received a request to find {query} in the image. Starting with comprehensive perception analysis.",
        "Time to locate {query} in this image! Let me initiate the perception process to get started.",
        "Beginning my search for {query}. I'll start by examining what's visible in the image through perception."
    ],
    "perception_multiple_found": [
        "I found {entity_counter_str} entities in the image. For so many entities, I need to generate logic to reason to find the {query}.",
        "Great! I detected {entity_counter_str} entities in this image. With multiple objects present, I'll need to create logical reasoning to identify the {query}.",
        "The perception phase revealed {entity_counter_str} entities. Given this complexity, I should develop reasoning logic to pinpoint the {query}.",
        "I've identified {entity_counter_str} entities in the scene. Since there are multiple objects, I'll generate logical queries to find the specific {query}.",
        "Perception complete! Found {entity_counter_str} entities. With this many objects detected, logical reasoning will help me locate the {query}."
    ],
    "perception_retry": [
        "Oops, seems something wrong in the perception. Let me retry it.",
        "The perception didn't work as expected. I'll give it another try.",
        "Something went wrong during perception. Let me run it again to get better results.",
        "Hmm, the perception phase encountered an issue. I'll retry the process.",
        "The initial perception had some problems. Let me attempt it once more."
    ],
    "perception_no_entity": [
        "I didn't find any entity in the image. Let me use the fallback method to find the {query}.",
        "No entities were detected in the initial perception. I'll try the fallback approach to locate the {query}.",
        "The perception phase came up empty. Time to switch to the fallback method for finding the {query}.",
        "Unfortunately, no entities were identified. Let me employ the backup detection method to search for the {query}.",
        "The standard perception didn't detect anything. I'll use an alternative approach to find the {query}."
    ],
    "perception_one_entity": [
        "I found one entity ({entity_category}) in the image. I don't think it's necessary to run the logic generation. Let me check if it's the {query}.",
        "Perfect! I detected a single entity ({entity_category}) in the image. Since there's only one object, I can skip logic generation and directly verify if it's the {query}.",
        "Great news! One entity ({entity_category}) was found. With just one object present, I can immediately check if this is the {query} I'm looking for.",
        "The perception found exactly one entity ({entity_category}). No need for complex reasoning - let me simply verify if this matches the {query}.",
        "Excellent! I identified one entity ({entity_category}) in the scene. Since it's the only object, I can directly assess whether it's the {query}."
    ],
    "fallback_perception_no_entity": [
        "I didn't find the {query} in the image even with the fallback method. I'm sorry.",
        "Unfortunately, even the fallback approach couldn't locate the {query} in this image. My apologies.",
        "I've exhausted all detection methods but couldn't find the {query} in the image. Sorry about that.",
        "Despite trying multiple approaches, I wasn't able to identify the {query} in this image. I apologize.",
        "Even with the backup detection method, I couldn't locate the {query}. I'm afraid it may not be present in the image."
    ],
    "fallback_perception_one_entity": [
        "I found the {query}. Let me use the fallback result.",
        "Success! The fallback method detected the {query}. I'll proceed with this result.",
        "Great! The backup approach successfully identified the {query}. Using this detection.",
        "Excellent! The fallback detection found the {query}. I'll work with this result.",
        "Perfect! The alternative method located the {query}. Proceeding with this finding."
    ],
    "logic_generation_first_no_feedback": [
        "By using LLM, I successfully get the logic query. Now I need to run some perception and reasoning to find the {query}.",
        "The LLM has generated a logic query for me. Time to execute perception and reasoning to locate the {query}.",
        "Great! I've obtained a logic query from the LLM. Now I'll apply perception and reasoning to find the {query}.",
        "Successfully generated logical reasoning with LLM assistance. Next, I'll run perception and analysis to identify the {query}.",
        "The language model provided me with a logic query. I'll now use perception and reasoning to search for the {query}."
    ],
    "logic_generation_retry_with_feedback": [
        "Now this time with extra feedback, I get the logic query. Now I need to run some perception and reasoning to find the {query}.",
        "With the additional feedback incorporated, I've generated an improved logic query. Time to apply perception and reasoning for the {query}.",
        "Thanks to the feedback, I now have a better logic query. Let me proceed with perception and reasoning to locate the {query}.",
        "The feedback helped me create a refined logic query. I'll now use perception and reasoning to find the {query}.",
        "Armed with feedback-enhanced logic, I'm ready to run perception and reasoning to identify the {query}."
    ],
    "logic_reasoning_success": [
        "I get a potential target from logic reasoning. Let me final double check it.",
        "Logic reasoning has identified a potential candidate. Time for final verification.",
        "Great! The reasoning process found a possible target. Let me confirm this result.",
        "Logic analysis has produced a candidate match. I'll perform a final validation check.",
        "Excellent! Reasoning has yielded a potential target. Now for the final confirmation step."
    ],
    "logic_reasoning_success_with_retry": [
        "This time I seems successfully get a target from logic reasoning. Let me final double check it.",
        "After the retry, logic reasoning has found a target. Time for final verification.",
        "Success on this attempt! Logic reasoning identified a candidate. Let me confirm it.",
        "The second attempt at reasoning worked! Found a potential target - now to verify it.",
        "This retry was successful! Logic reasoning produced a candidate that needs final validation."
    ],
    "logic_reasoning_failed": [
        "I failed to get a target from logic reasoning. Let me try to generate the logic query again.",
        "The logic reasoning didn't produce a valid target. I'll regenerate the logic query.",
        "Logic reasoning came up empty. Time to create a new logic query and try again.",
        "The reasoning process failed to identify a target. Let me generate fresh logic.",
        "Logic reasoning wasn't successful this time. I'll develop a new logical approach."
    ],
    "answering_failed": [
        "The final verification failed. Let me try to use another logic reasoning candidate.",
        "Verification didn't pass. I'll try the next candidate from logic reasoning.",
        "The final check failed. Time to test another potential target from my reasoning results.",
        "Final verification was unsuccessful. Let me explore the next reasoning candidate.",
        "The validation didn't work out. I'll move on to another logic reasoning option."
    ],
    "final_result": [
        "I found the {query} in the image. The result is {result}.",
        "Success! I've located the {query} in the image. Here's the result: {result}.",
        "Great news! I found the {query} you were looking for. The result is {result}.",
        "Mission accomplished! The {query} has been identified in the image. Result: {result}.",
        "Excellent! I successfully detected the {query} in the image. The final result is {result}."
    ]
}

def build_message_content(template_type: str, **kwargs) -> str:
    return random.choice(message_templates[template_type]).format(**kwargs)


def generate_intermediate_messages(naver: Naver, session_id: str) -> list[ExecutionMessage]:
    # the message for the first iteration
    if manager.naver_prev_state[session_id] is None:
        assert isinstance(naver.state, States.Perception), f"The first iteration should be in the perception state, but got {naver.state}"
        thinking_message = ExecutionMessage(type="thinking", content=build_message_content("initial_input", query=naver.query))
        action_message = ExecutionMessage(type="action", content="Run Perception()")
        return [thinking_message, action_message]
    
    assert (prev_state := manager.naver_prev_state[session_id]) is not None, f"The previous state is not found for session {session_id}"
    
    match (prev_state, naver.state):
        case (States.Perception(_), States.LogicGeneration()):
            # it means multiple objects are found, and prepare for logic generation
            context = naver.state_memory_bank.context
            assert context is not None, f"The context is not found for session {session_id}"
            entity_categories = [entity.category for entity in context.entities.values()]
            entity_counter = Counter(entity_categories)
            entity_counter_str = ", ".join([f"{count} {category}" for category, count in entity_counter.items()])
            thinking_message = ExecutionMessage(type="thinking", content=build_message_content("perception_multiple_found", entity_counter_str=entity_counter_str, query=naver.query))
            action_message = ExecutionMessage(type="action", content="Run LogicGeneration()")
            return [thinking_message, action_message]
        
        case (States.Perception(_), States.Perception(_)):
            # it means the perception has something wrong, just retry
            thinking_message = ExecutionMessage(type="thinking", content=build_message_content("perception_retry", query=naver.query))
            action_message = ExecutionMessage(type="action", content="Run Perception()")
            return [thinking_message, action_message]
        
        case (States.Perception(_), States.Answering(None, None, 0)):
            # no entity
            thinking_message = ExecutionMessage(type="thinking", content=build_message_content("perception_no_entity", query=naver.query))
            action_message = ExecutionMessage(type="action", content="Run fallback perception")
            fallback_entity = naver.fallback_result
            if fallback_entity is None:
                thinking_message_2 = ExecutionMessage(type="thinking", content=build_message_content("fallback_perception_no_entity", query=naver.query))
            else:
                thinking_message_2 = ExecutionMessage(type="thinking", content=build_message_content("fallback_perception_one_entity", query=naver.query))
            action_message_2 = ExecutionMessage(type="action", content="Run Answering(result=...)")
            return [thinking_message, action_message, thinking_message_2, action_message_2]
        
        case (States.Perception(_), States.Answering(entity, None, 0)) if entity is not None:
            # one entity
            thinking_message = ExecutionMessage(type="thinking", content=build_message_content("perception_one_entity", entity_category=entity.category, query=naver.query))
            action_message = ExecutionMessage(type="action", content="Run Answering(result=...)")
            return [thinking_message, action_message]
        
        case (States.LogicGeneration(None), States.LogicReasoning(_, 0)):
            # the first time running logic generation (i.e. without feedback)
            thinking_message = ExecutionMessage(type="thinking", content=build_message_content("logic_generation_first_no_feedback", query=naver.query))
            action_message = ExecutionMessage(type="action", content="Run LogicReasoning(logic_query=...)")
            return [thinking_message, action_message]
        
        case (States.LogicGeneration(_), States.LogicReasoning(_, 0)):
            # the second time running logic generation (i.e. with feedback)
            thinking_message = ExecutionMessage(type="thinking", content=build_message_content("logic_generation_retry_with_feedback", query=naver.query))
            action_message = ExecutionMessage(type="action", content="Run LogicReasoning(logic_query=...)")
            return [thinking_message, action_message]
        
        case (States.LogicReasoning(_, 0), States.Answering(_, _, _)):
            # if success to get a target candidate
            thinking_message = ExecutionMessage(type="thinking", content=build_message_content("logic_reasoning_success"))
            action_message = ExecutionMessage(type="action", content="Run Answering(result=...)")
            return [thinking_message, action_message]
        
        case (States.LogicReasoning(_, skip_num), States.Answering(_, _, _)) if skip_num > 0:
            # if failed to get a target candidate
            thinking_message = ExecutionMessage(type="thinking", content=build_message_content("logic_reasoning_success_with_retry"))
            action_message = ExecutionMessage(type="action", content="Run Answering(result=...)")
            return [thinking_message, action_message]
        
        case (States.LogicReasoning(_, _), States.LogicGeneration(_)):
            # if failed to get a target candidate
            thinking_message = ExecutionMessage(type="thinking", content=build_message_content("logic_reasoning_failed"))
            action_message = ExecutionMessage(type="action", content="Run LogicGeneration(feedback=...)")
            return [thinking_message, action_message]
        
        case (States.Answering(_, _, _), States.LogicReasoning(_, _)):
            # if failed to get a target candidate
            thinking_message = ExecutionMessage(type="thinking", content=build_message_content("answering_failed"))
            action_message = ExecutionMessage(type="action", content="Run LogicReasoning(logic_query=..., skip_top=...)")
            return [thinking_message, action_message]
        
        case _:
            raise ValueError(f"Unknown state: {prev_state} -> {naver.state}")


def update_state_info(naver: Naver, session_id: str) -> StateInfo:
    state_info = manager.state_info[session_id]
    if state_info.current_state is not None:
        state_info.history.append(state_info.current_state)
    state_info.current_state = naver.state.__class__.__name__
    manager.state_info[session_id] = state_info
    return state_info


def context_to_dict(context: Context) -> dict:
    entities = [{
        "id": v.id,
        "category": v.category,
        "bbox": v.bbox,
        "bbox_confidence": v.bbox_confidence
    } for v in context.entities.values()]

    relations = [{
        "subject_entity_id": v.subject_entity_id,
        "object_entity_id": v.object_entity_id,
        "relation_name": v.relation_name,
    } for v in context.relations]

    attributes = [{
        "entity_id": v.entity_id,
        "attribute_name": v.attribute_name,
        "prob": v.prob
    } for v in context.attributes]

    return {"entities": entities, "relations": relations, "attributes": attributes}

# WebSocket endpoint (used for main inference pipeline)
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            naver = manager.naver_instances[session_id]
            logger.info(f"WebSocket connected for session: {session_id}, current state: {naver.state}")
            # generate the thinkings for preparing the next action
            intermediate_messages: list[ExecutionMessage] = generate_intermediate_messages(naver, session_id)
            
            for message in intermediate_messages:
                await manager.send_message(session_id, {
                    "type": "execution_message",
                    "body": message.model_dump()
                })

            # after propose the action, send the message for the state change
            state_info = update_state_info(naver, session_id)
            await manager.send_message(session_id, {
                "type": "state_info",
                "body": state_info.model_dump()
            })

            prev_state = naver.state  # the current state, but not executed yet
            result, _ = await naver.step()  # now the state is executed, and changed
            manager.naver_prev_state[session_id] = prev_state

            if result is not None:
                # if the result is valid, send the final result message
                result_message = build_message_content("final_result", query=naver.query, result=result.bbox)
                await manager.send_message(
                    session_id, 
                    {
                        "type": "execution_message",
                        "body": {
                            "type": "result",
                            "content": result_message
                        }
                    }
                )
                # send the final state info
                await manager.send_message(session_id, {
                    "type": "state_info",
                    "body": {
                        "current_state": "Output",
                        "history": [*state_info.history, "Output"]
                    }
                })
                # send the logic context
                assert naver.state_memory_bank.context is not None, f"The context is not found for session {session_id}"
                await manager.send_message(session_id, {
                    "type": "context",
                    "body": context_to_dict(naver.state_memory_bank.context)
                })
                break

    except WebSocketDisconnect:
        await manager.disconnect(session_id)

    finally:
        await manager.disconnect(session_id)


# API endpoints
@app.post("/api/start")
async def start(
    image: UploadFile = File(...),
    query: str = Form(...)
):
    """Start NAVER agent inference"""

    # initialize a random session id
    session_id = str(uuid.uuid4())
    
    # check if the session id is already in the manager
    if session_id in manager.session_states:
        await manager.disconnect(session_id)
    
    try:
        # Save uploaded image (use the system temp directory)
        image_path = os.path.join(tempfile.gettempdir(), f"{session_id}_{image.filename}")
        
        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)

        # Start analysis in background
        await manager.create(session_id, image_path, query)
        state = manager.session_states[session_id]
        
        # Update state
        state.current_state = "BUSY"
        state.error = None
        
        return {"status": "started", "session_id": session_id}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error starting analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/{session_id}/stop")
async def stop_execution(session_id: str):
    """Stop running execution"""
    
    if session_id not in manager.session_states:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    state = manager.session_states[session_id]
    state.current_state = "STOPPED"
    
    await manager.broadcast_to_session(
        session_id,
        "execution_error", 
        {
            "error": "Execution stopped by user",
            "current_state": "STOPPED"
        }
    )

    await manager.disconnect(session_id)
    
    return {"status": "stopped"}


# Serve static files from SvelteKit build
app.mount("/_app", StaticFiles(directory=str(frontend_build_path / "_app")), name="assets")

@app.get("/favicon.svg")
async def favicon_svg():
    favicon_path = frontend_build_path / "favicon.svg"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    return JSONResponse(status_code=404, content={"error": "Favicon not found"})

# Fallback route to serve the main app for any unmatched routes (SPA routing)
@app.get("/{path:path}")
async def serve_spa(path: str):
    """Serve the SvelteKit app for all non-API routes"""
    # Don't serve SPA for API routes or WebSocket
    if path.startswith("api/") or path.startswith("ws/"):
        return JSONResponse(status_code=404, content={"error": "Not found"})
    
    index_file = frontend_build_path / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Frontend not built. Run 'cd gui && npm run build' first."}
        )


if __name__ == "__main__":

    logger.info("Starting the NAVER GUI server...")
    uvicorn.run(
        "demo_gui:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
        workers=1,  # Ensure only one instance to avoid CUDA OOM
    )
