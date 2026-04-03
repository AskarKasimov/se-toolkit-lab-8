"""Persistent WebSocket listener for webchat — keeps connection alive to receive cron reports."""
import asyncio
import json
import sys
import websockets

ACCESS_KEY = "nanobot"
HOST = "10.93.25.126"
PORT = 42002
CHAT_ID = "2eae1e37-f93b-4f39-b0da-da82b4440593"


async def listen(output_file: str = "/tmp/task4b_cron_live.json", duration: int = 180):
    """Keep a WebSocket connection open and capture all messages."""
    uri = f"ws://{HOST}:{PORT}/ws/chat?access_key={ACCESS_KEY}&chat_id={CHAT_ID}"
    
    all_messages = []
    try:
        async with websockets.connect(uri, ping_interval=15, ping_timeout=15) as ws:
            print(f"Connected to chat_id: {CHAT_ID}", file=sys.stderr)
            print(f"Listening for {duration} seconds...", file=sys.stderr)
            
            end_time = asyncio.get_event_loop().time() + duration
            
            while asyncio.get_event_loop().time() < end_time:
                remaining = end_time - asyncio.get_event_loop().time()
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 10))
                    data = json.loads(resp)
                    all_messages.append(data)
                    
                    if data.get("type") == "text":
                        content = data.get("content", "")
                        print(f"\n{'='*60}", file=sys.stderr)
                        print(content, file=sys.stderr)
                        print(f"{'='*60}\n", file=sys.stderr)
                    else:
                        print(f"[{data.get('type', 'unknown')}]", file=sys.stderr)
                except asyncio.TimeoutError:
                    pass
    except websockets.ConnectionClosed as e:
        print(f"Connection closed: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    
    result = json.dumps(all_messages, indent=2, ensure_ascii=False)
    with open(output_file, 'w') as f:
        f.write(result)
    print(f"\nSaved {len(all_messages)} messages to {output_file}", file=sys.stderr)
    
    # Print text content for report
    for msg in all_messages:
        if msg.get("type") == "text":
            print(f"\n--- REPORT MESSAGE ---\n{msg['content']}\n")
    
    return all_messages


if __name__ == "__main__":
    asyncio.run(listen())
