"""Wait for cron health check reports in an existing session."""
import asyncio
import json
import sys
import websockets

ACCESS_KEY = "nanobot"
HOST = "10.93.25.126"
PORT = 42002


async def wait_for_cron_reports(output_file: str = "/tmp/task4b_cron_report.json", wait_minutes: int = 5):
    """Connect and wait for cron health reports."""
    uri = f"ws://{HOST}:{PORT}/ws/chat?access_key={ACCESS_KEY}"
    
    all_messages = []
    async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
        print("Connected. Waiting for cron reports...", file=sys.stderr)
        
        last_activity = asyncio.get_event_loop().time()
        timeout = wait_minutes * 60
        
        try:
            while True:
                remaining = timeout - (asyncio.get_event_loop().time() - last_activity)
                if remaining <= 0:
                    break
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 30))
                    last_activity = asyncio.get_event_loop().time()
                    data = json.loads(resp)
                    all_messages.append(data)
                    
                    msg_type = data.get("type", "unknown")
                    if msg_type == "text":
                        content = data.get("content", "")
                        print(f"[TEXT] {content[:200]}...", file=sys.stderr)
                    else:
                        print(f"[{msg_type.upper()}]", file=sys.stderr)
                except asyncio.TimeoutError:
                    print("30s silence, still listening...", file=sys.stderr)
        except websockets.ConnectionClosed as e:
            print(f"Connection closed: {e}", file=sys.stderr)
    
    result = json.dumps(all_messages, indent=2, ensure_ascii=False)
    with open(output_file, 'w') as f:
        f.write(result)
    print(f"Saved to {output_file}", file=sys.stderr)
    
    # Also print the full text content
    for msg in all_messages:
        if msg.get("type") == "text":
            print(f"\n--- Message ---\n{msg['content']}\n")
    
    return all_messages


if __name__ == "__main__":
    asyncio.run(wait_for_cron_reports())
