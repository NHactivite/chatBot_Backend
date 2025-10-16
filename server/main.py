import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.llm import stream_process_msg,get_conversation_history,retriveAllThreads

sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
fastapi_app = FastAPI()

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # for testing, later restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount FastAPI inside socketio.ASGIApp
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

# Example event
@sio.event
async def connect(sid, environ):
    print("🔌 Client connected:", sid)

@sio.event
async def disconnect(sid):
    print("❌ Client disconnected:", sid)


# ✅ Listen for human messages
@sio.on("human_message")
async def handle_human_message(sid, data):
    user_input = data.get("message", "")
    threadId=data.get("threadId","")
    print(f"👤 Human({sid}): {user_input}")
    print(f"👤 threadId({sid}): {threadId}")
    
    for chunk in stream_process_msg(user_input, threadId):
        if chunk["type"] == "tool_start":
            await sio.emit("tool_status", {"tool": chunk["tool"]}, to=sid)

        elif chunk["type"] == "ai_message":
            await sio.emit("ai_chunk", {"text": chunk["text"]}, to=sid)

    await sio.emit("ai_done", {}, to=sid)


@sio.on("message_history")
async def handle_message_history(sid, data):
    threadId = data.get("threadId", "")
    print(f"👤 threadId({sid}): {threadId}")

    history = get_conversation_history(threadId)

    # send history back only to this client
    await sio.emit("message_history", {"threadId": threadId, "history": history}, to=sid)

@sio.on("OldThreads_history")
async def handle_message_history(sid):
    
    threads = retriveAllThreads()

    # send history back only to this client
    await sio.emit("threads_history", {"threads":threads}, to=sid)