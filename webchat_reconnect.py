"""Reconnect to existing webchat session and wait for cron reports."""
import asyncio
import json
import sys
import websockets

ACCESS_KEY = "nanobot"
HOST = "10.93.25.126"
PORT = 42002
CHAT_ID = "2eae1e37-f93b-4f39-b0da-da82b4440593"


async def wait_for_cron_reports(output_file: str = "/tmp/task4b_cron_report.json"):
    """Reconnect to existing chat_id and wait for cron health reports."""
    uri = f"ws://{HOST}:{PORT}/ws/chat?access_key={ACCESS_KEY}&chat_id={CHAT_ID}"
    
    all_messages = []
    async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
        print(f"Reconnected to chat_id: {CHAT_ID}", file=sys.stderr)
        print("Waiting for cron reports (up to 3 minutes)...", file=sys.stderr)
        
        last_activity = asyncio.get_event_loop().time()
        timeout = 180  # 3 minutes
        
        try:
            while True:
                remaining = timeout - (asyncio.get_event_loop().time() - last_activity)
                if remaining <= 0:
                    print("Timeout reached", file=sys.stderr)
                    break
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 30))
                    last_activity = asyncio.get_event_loop().time()
                    data = json.loads(resp)
                    all_messages.append(data)
                    
                    msg_type = data.get("type", "unknown")
                    if msg_type == "text":
                        content = data.get("content", "")
                        print(f"\n[TEXT]\n{content}\n", file=sys.stderr)
                    elif msg_type == "composite":
                        parts = data.get("parts", [])
                        print(f"\n[COMPOSITE] {len(parts)} parts", file=sys.stderr)
                        for p in parts:
                            if p.get("type") == "text":
                                print(f"\n[TEXT PART]\n{p.get('content', '')}\n", file=sys.stderr)
                    else:
                        print(f"\n[{msg_type.upper()}]\n", file=sys.stderr)
                except asyncio.TimeoutError:
                    print("30s silence, still listening...", file=sys.stderr)
        except websockets.ConnectionClosed as e:
            print(f"Connection closed: {e}", file=sys.stderr)
    
    result = json.dumps(all_messages, indent=2, ensure_ascii=False)
    with open(output_file, 'w') as f:
        f.write(result)
    print(f"\nSaved to {output_file}", file=sys.stderr)
    
    return all_messages


if __name__ == "__main__":
    asyncio.run(wait_for_cron_reports())
