#!/usr/bin/env python3
"""
Entrypoint for nanobot Docker deployment.

Resolves environment variables into the config at runtime, then launches nanobot gateway.
This is needed because Docker passes config via env vars, not by editing files.

Environment variables read:
- LLM_API_KEY -> providers.custom.apiKey
- LLM_API_BASE_URL -> providers.custom.apiBase
- LLM_API_MODEL -> agents.defaults.model
- NANOBOT_GATEWAY_CONTAINER_ADDRESS -> gateway.host
- NANOBOT_GATEWAY_CONTAINER_PORT -> gateway.port
- NANOBOT_LMS_BACKEND_URL -> tools.mcpServers.lms.env.NANOBOT_LMS_BACKEND_URL
- NANOBOT_LMS_API_KEY -> tools.mcpServers.lms.env.NANOBOT_LMS_API_KEY
- NANOBOT_WEBCHAT_CONTAINER_ADDRESS -> channels.webchat.host
- NANOBOT_WEBCHAT_CONTAINER_PORT -> channels.webchat.port
- NANOBOT_ACCESS_KEY -> channels.webchat.accessKey
- NANOBOT_WEBSOCKET_RELAY_URL -> tools.mcpServers.webchat.env.NANOBOT_WEBSOCKET_RELAY_URL
- NANOBOT_WEBSOCKET_TOKEN -> tools.mcpServers.webchat.env.NANOBOT_WEBSOCKET_TOKEN
- NANOBOT_VICTORIALOGS_URL -> tools.mcpServers.obs.env.NANOBOT_VICTORIALOGS_URL
- NANOBOT_VICTORIATRACES_URL -> tools.mcpServers.obs.env.NANOBOT_VICTORIATRACES_URL
"""

import json
import os
import sys


def load_config(config_path: str) -> dict:
    """Load the base config from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def resolve_config(config: dict) -> dict:
    """
    Override config fields from environment variables.
    
    Only modifies fields that have corresponding env vars set.
    This keeps the base config.json as the source of truth for defaults.
    """
    # LLM provider config
    llm_api_key = os.environ.get('LLM_API_KEY')
    if llm_api_key:
        config['providers']['custom']['apiKey'] = llm_api_key
    
    llm_api_base = os.environ.get('LLM_API_BASE_URL')
    if llm_api_base:
        config['providers']['custom']['apiBase'] = llm_api_base
    
    llm_api_model = os.environ.get('LLM_API_MODEL')
    if llm_api_model:
        config['agents']['defaults']['model'] = llm_api_model
    
    # Gateway config
    gateway_host = os.environ.get('NANOBOT_GATEWAY_CONTAINER_ADDRESS')
    if gateway_host:
        config['gateway']['host'] = gateway_host
    
    gateway_port = os.environ.get('NANOBOT_GATEWAY_CONTAINER_PORT')
    if gateway_port:
        config['gateway']['port'] = int(gateway_port)
    
    # MCP server (LMS) config
    lms_backend_url = os.environ.get('NANOBOT_LMS_BACKEND_URL')
    if lms_backend_url:
        config['tools']['mcpServers']['lms']['env']['NANOBOT_LMS_BACKEND_URL'] = lms_backend_url
    
    lms_api_key = os.environ.get('NANOBOT_LMS_API_KEY')
    if lms_api_key:
        config['tools']['mcpServers']['lms']['env']['NANOBOT_LMS_API_KEY'] = lms_api_key
    
    # Webchat channel config
    webchat_host = os.environ.get('NANOBOT_WEBCHAT_CONTAINER_ADDRESS')
    if webchat_host:
        config['channels']['webchat']['host'] = webchat_host
    
    webchat_port = os.environ.get('NANOBOT_WEBCHAT_CONTAINER_PORT')
    if webchat_port:
        config['channels']['webchat']['port'] = int(webchat_port)
    
    # Webchat access key
    access_key = os.environ.get('NANOBOT_ACCESS_KEY')
    if access_key:
        config['channels']['webchat']['accessKey'] = access_key
    
    # MCP webchat server config
    websocket_relay_url = os.environ.get('NANOBOT_WEBSOCKET_RELAY_URL')
    if websocket_relay_url:
        config['tools']['mcpServers']['webchat']['env']['NANOBOT_WEBSOCKET_RELAY_URL'] = websocket_relay_url
    
    websocket_token = os.environ.get('NANOBOT_WEBSOCKET_TOKEN')
    if websocket_token:
        config['tools']['mcpServers']['webchat']['env']['NANOBOT_WEBSOCKET_TOKEN'] = websocket_token

    # MCP observability server config
    victorialogs_url = os.environ.get('NANOBOT_VICTORIALOGS_URL')
    if victorialogs_url:
        config['tools']['mcpServers']['obs']['env']['NANOBOT_VICTORIALOGS_URL'] = victorialogs_url

    victoriatraces_url = os.environ.get('NANOBOT_VICTORIATRACES_URL')
    if victoriatraces_url:
        config['tools']['mcpServers']['obs']['env']['NANOBOT_VICTORIATRACES_URL'] = victoriatraces_url

    return config


def main():
    """Main entrypoint: resolve config and exec nanobot gateway."""
    # Determine paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.json')
    # Write resolved config to /tmp since /app/nanobot may be bind-mounted and not writable
    resolved_config_path = '/tmp/config.resolved.json'
    workspace_path = os.path.join(script_dir, 'workspace')
    
    # Load and resolve config
    print(f"Loading config from: {config_path}")
    config = load_config(config_path)
    resolved = resolve_config(config)
    
    # Write resolved config
    print(f"Writing resolved config to: {resolved_config_path}")
    with open(resolved_config_path, 'w') as f:
        json.dump(resolved, f, indent=2)
    
    # Log key resolved values for debugging (redact sensitive parts)
    api_base = resolved.get('providers', {}).get('custom', {}).get('apiBase', '<not set>')
    model = resolved.get('agents', {}).get('defaults', {}).get('model', '<not set>')
    gateway_host = resolved.get('gateway', {}).get('host', '<not set>')
    gateway_port = resolved.get('gateway', {}).get('port', '<not set>')
    
    print(f"Resolved LLM API base: {api_base}")
    print(f"Resolved model: {model}")
    print(f"Resolved gateway: {gateway_host}:{gateway_port}")
    
    # Exec nanobot gateway - replaces this process
    os.execvp("nanobot", ["nanobot", "gateway", "--config", resolved_config_path, "--workspace", workspace_path])


if __name__ == "__main__":
    main()
