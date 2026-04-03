"""Task 4 Part B — WebChat client with persistent session for cron health checks."""
import asyncio
import json
import sys
import websockets

ACCESS_KEY = "nanobot"
HOST = "10.93.25.126"
PORT = 42002


async def run_task4b():
    """
    Part B workflow:
    1. Connect to webchat, ask agent to create a health check cron job
    2. Ask agent to list scheduled jobs
    3. Trigger fresh failure
    4. Wait for proactive health report from cron
    """
    uri = f"ws://{HOST}:{PORT}/ws/chat?access_key={ACCESS_KEY}"
    
    async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
        # Step 1: Ask agent to create a health check cron job
        msg1 = (
            "Create a health check for this chat that runs every 2 minutes using your cron tool. "
            "Each run should check for LMS/backend errors in the last 2 minutes, inspect a trace if needed, "
            "and post a short summary here. If there are no recent errors, say the system looks healthy."
        )
        print(f"\n=== Sending: {msg1[:80]}... ===", file=sys.stderr)
        await ws.send(json.dumps({"content": msg1}))
        await _capture_responses(ws, "task4b_step1", idle_timeout=45)
        
        # Step 2: Ask agent to list scheduled jobs
        msg2 = "List scheduled jobs."
        print(f"\n=== Sending: {msg2} ===", file=sys.stderr)
        await ws.send(json.dumps({"content": msg2}))
        await _capture_responses(ws, "task4b_step2", idle_timeout=30)
        
        # Steps 3-4 will be done manually after triggering failure
        print("\n=== Session ready for Part B steps 3-4 ===", file=sys.stderr)
        print("Now trigger a fresh failure and wait for cron reports.", file=sys.stderr)
        
        # Keep connection alive to receive cron reports
        print("\n=== Waiting for cron health reports (up to 5 minutes) ===", file=sys.stderr)
        await _capture_responses(ws, "task4b_cron_reports", idle_timeout=300)


async def _capture_responses(ws, label: str, idle_timeout: int = 30):
    """Capture all responses from WebSocket and save to file."""
    all_messages = []
    output_file = f"/tmp/{label}.json"
    
    last_activity = asyncio.get_event_loop().time()
    
    try:
        while True:
            remaining = idle_timeout - (asyncio.get_event_loop().time() - last_activity)
            if remaining <= 0:
                print(f"[{label}] Idle timeout - stopping", file=sys.stderr)
                break
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=remaining)
                last_activity = asyncio.get_event_loop().time()
                data = json.loads(resp)
                all_messages.append(data)
                
                msg_type = data.get("type", "unknown")
                if msg_type == "text":
                    content = data.get("content", "")
                    print(f"[{label}] [TEXT] {content[:150]}...", file=sys.stderr)
                elif msg_type == "composite":
                    parts = data.get("parts", [])
                    print(f"[{label}] [COMPOSITE] {len(parts)} parts", file=sys.stderr)
                elif msg_type == "tool_call":
                    print(f"[{label}] [TOOL_CALL]", file=sys.stderr)
                else:
                    print(f"[{label}] [{msg_type.upper()}]", file=sys.stderr)
            except asyncio.TimeoutError:
                print(f"[{label}] Idle timeout - stopping", file=sys.stderr)
                break
    except websockets.ConnectionClosed as e:
        print(f"[{label}] Connection closed: {e}", file=sys.stderr)
    
    result = json.dumps(all_messages, indent=2, ensure_ascii=False)
    with open(output_file, 'w') as f:
        f.write(result)
    print(f"[{label}] Saved to {output_file}", file=sys.stderr)
    
    return all_messages


if __name__ == "__main__":
    asyncio.run(run_task4b())
