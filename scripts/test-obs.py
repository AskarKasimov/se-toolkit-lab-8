#!/usr/bin/env python3
"""Test Task 3C observability MCP tools via webchat WebSocket."""
import asyncio, json, websockets, subprocess, time

async def ask(uri, question, timeout=120):
    async with websockets.connect(uri) as ws:
        msg = json.dumps({'type': 'message', 'text': question})
        await ws.send(msg)
        print(f"Q: {question}")
        full_response = []
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=timeout)
                data = json.loads(resp)
                t = data.get('type','')
                if t == 'message':
                    txt = data.get('text','')
                    full_response.append(txt)
                    print(txt, end='', flush=True)
                elif t == 'done':
                    print("\n---DONE---")
                    break
                elif t == 'tool_call':
                    print(f"\n[TOOL: {data.get('tool_name','')}] ", end='', flush=True)
                elif t == 'tool_result':
                    print(f"\n[TOOL_RESULT] ", end='', flush=True)
            except asyncio.TimeoutError:
                print("\n---TIMEOUT---")
                break
        return '\n'.join(full_response)

def docker_compose(args):
    return subprocess.run(
        ['docker', 'compose', '--env-file', '.env.docker.secret'] + args,
        capture_output=True, text=True
    )

async def main():
    uri = 'ws://localhost:8765/ws/chat?access_key=nanobot'
    
    # Test 1: Normal conditions (postgres running)
    print("=== TEST 1: Normal conditions (postgres running) ===")
    r1 = await ask(uri, "Any LMS backend errors in the last 10 minutes?")
    print(f"\n\nRESULT 1:\n{r1}")
    
    await asyncio.sleep(2)
    
    # Stop postgres
    print("\n=== Stopping postgres ===")
    docker_compose(['stop', 'postgres'])
    time.sleep(3)
    
    # Trigger an error request
    print("=== Triggering error request ===")
    subprocess.run(['curl', '-sf', 'http://localhost:42002/items/', 
                    '-H', 'Authorization: Bearer ggg'], capture_output=True)
    time.sleep(5)
    
    # Test 2: After postgres stop
    print("\n=== TEST 2: After postgres stop ===")
    r2 = await ask(uri, "Any LMS backend errors in the last 10 minutes?")
    print(f"\n\nRESULT 2:\n{r2}")
    
    # Restart postgres
    print("\n=== Restarting postgres ===")
    docker_compose(['start', 'postgres'])
    time.sleep(3)
    
    print("\n\n=== ALL TESTS DONE ===")

if __name__ == '__main__':
    asyncio.run(main())
