"""WebChat client for Task 4 — sends messages, captures responses, reuses session."""
import asyncio
import json
import sys
import websockets

ACCESS_KEY = "nanobot"
HOST = "10.93.25.126"
PORT = 42002


async def create_session():
    """Create a new webchat session and return the chat_id."""
    uri = f"ws://{HOST}:{PORT}/ws/chat?access_key={ACCESS_KEY}"
    async with websockets.connect(uri) as ws:
        # The server assigns a chat_id automatically. We need to discover it.
        # Send a hello message first
        await ws.send(json.dumps({"content": "Hello"}))
        chat_id = None
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(resp)
                # The session file gets created on the server side
                # We can't directly get the chat_id from WS messages
                # Let's check the session files instead
                if data.get("type") == "text":
                    break
            except asyncio.TimeoutError:
                break
    return None


async def send_message(message: str, output_file: str | None = None, idle_timeout: int = 30):
    """Connect to webchat (new session), send a message, and capture all responses."""
    uri = f"ws://{HOST}:{PORT}/ws/chat?access_key={ACCESS_KEY}"
    
    all_messages = []
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"content": message}))
        print(f"Sent: {message}", file=sys.stderr)
        
        last_activity = asyncio.get_event_loop().time()
        
        try:
            while True:
                remaining = idle_timeout - (asyncio.get_event_loop().time() - last_activity)
                if remaining <= 0:
                    print("Idle timeout - stopping", file=sys.stderr)
                    break
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    last_activity = asyncio.get_event_loop().time()
                    data = json.loads(resp)
                    all_messages.append(data)
                    
                    msg_type = data.get("type", "unknown")
                    if msg_type == "text":
                        content = data.get("content", "")
                        print(f"[TEXT] {content[:150]}...", file=sys.stderr)
                    elif msg_type == "composite":
                        parts = data.get("parts", [])
                        print(f"[COMPOSITE] {len(parts)} parts", file=sys.stderr)
                    else:
                        print(f"[{msg_type.upper()}]", file=sys.stderr)
                except asyncio.TimeoutError:
                    print("Idle timeout - stopping", file=sys.stderr)
                    break
        except websockets.ConnectionClosed as e:
            print(f"Connection closed: {e}", file=sys.stderr)
    
    result = json.dumps(all_messages, indent=2, ensure_ascii=False)
    if output_file:
        with open(output_file, 'w') as f:
            f.write(result)
        print(f"Saved to {output_file}", file=sys.stderr)
    else:
        print(result)
    
    return all_messages


async def send_message_existing(message: str, chat_id: str, output_file: str | None = None, idle_timeout: int = 30):
    """Send a message to an existing webchat session by chat_id."""
    uri = f"ws://{HOST}:{PORT}/ws/chat?access_key={ACCESS_KEY}&chat_id={chat_id}"
    
    all_messages = []
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"content": message}))
        print(f"Sent to {chat_id}: {message}", file=sys.stderr)
        
        last_activity = asyncio.get_event_loop().time()
        
        try:
            while True:
                remaining = idle_timeout - (asyncio.get_event_loop().time() - last_activity)
                if remaining <= 0:
                    print("Idle timeout - stopping", file=sys.stderr)
                    break
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    last_activity = asyncio.get_event_loop().time()
                    data = json.loads(resp)
                    all_messages.append(data)
                    
                    msg_type = data.get("type", "unknown")
                    if msg_type == "text":
                        content = data.get("content", "")
                        print(f"[TEXT] {content[:150]}...", file=sys.stderr)
                    elif msg_type == "composite":
                        parts = data.get("parts", [])
                        print(f"[COMPOSITE] {len(parts)} parts", file=sys.stderr)
                    else:
                        print(f"[{msg_type.upper()}]", file=sys.stderr)
                except asyncio.TimeoutError:
                    print("Idle timeout - stopping", file=sys.stderr)
                    break
        except websockets.ConnectionClosed as e:
            print(f"Connection closed: {e}", file=sys.stderr)
    
    result = json.dumps(all_messages, indent=2, ensure_ascii=False)
    if output_file:
        with open(output_file, 'w') as f:
            f.write(result)
        print(f"Saved to {output_file}", file=sys.stderr)
    else:
        print(result)
    
    return all_messages


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: webchat_client.py <message> [chat_id] [output_file]", file=sys.stderr)
        sys.exit(1)
    
    message = sys.argv[1]
    chat_id = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
    output = sys.argv[3] if len(sys.argv) > 3 else None
    
    if chat_id:
        asyncio.run(send_message_existing(message, chat_id, output))
    else:
        asyncio.run(send_message(message, output))
