#!/usr/bin/env python3
"""Smoke test script for the Voice Mode WebSocket relay.

Usage:
    python scripts/voice_smoke.py [--url ws://localhost:8000/api/v1/voice/session] [--questions 5]
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import websockets


async def main() -> int:
    parser = argparse.ArgumentParser(description="Voice smoke test")
    parser.add_argument(
        "--url",
        default="ws://localhost:8000/api/v1/voice/session",
        help="WebSocket URL",
    )
    parser.add_argument(
        "--questions",
        type=int,
        default=5,
        help="Number of quiz questions",
    )
    parser.add_argument(
        "--origin",
        default="http://localhost:5173",
        help="Origin header",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    guide_path = base_dir / "tests" / "fixtures" / "sample_study_guide.json"
    pcm_path = base_dir / "tests" / "fixtures" / "hello_16k.pcm"

    if not guide_path.exists():
        print(f"Error: Fixture {guide_path} not found.", file=sys.stderr)
        return 1

    study_guide = json.loads(guide_path.read_text(encoding="utf-8"))
    pcm_bytes = pcm_path.read_bytes() if pcm_path.exists() else b"\x00" * 32000

    print(f"Connecting to {args.url} (Origin: {args.origin})...")
    headers = {"Origin": args.origin}

    ssl_context = None
    if args.url.startswith("wss://"):
        import ssl
        try:
            import certifi
            ssl_context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ssl_context = ssl.create_default_context()

    try:
        connect_kwargs = {"additional_headers": headers}
        if ssl_context:
            connect_kwargs["ssl"] = ssl_context
        async with websockets.connect(args.url, **connect_kwargs) as ws:
            # 1. Send start
            start_payload = {
                "type": "start",
                "device_id": "smoke-test-device",
                "study_guide": study_guide,
                "num_questions": args.questions,
            }
            print("Sending start payload...")
            await ws.send(json.dumps(start_payload))

            # 2. Wait for ready
            msg = await ws.recv()
            print(f"< Text: {msg}")
            ready = json.loads(msg)
            if ready.get("type") != "ready":
                print(f"Unexpected initial frame: {msg}", file=sys.stderr)
                return 1

            # 3. Send speech window with audio
            print("Sending speech_start...")
            await ws.send(json.dumps({"type": "speech_start"}))

            # Send in chunks of 8192 bytes
            chunk_size = 8192
            for i in range(0, len(pcm_bytes), chunk_size):
                chunk = pcm_bytes[i : i + chunk_size]
                await ws.send(chunk)
                await asyncio.sleep(0.05)

            print("Sending speech_end...")
            await ws.send(json.dumps({"type": "speech_end"}))

            # 4. Listen for incoming frames
            print("Listening for incoming frames (transcripts, audio, tool calls)...")
            turn_completed = False
            try:
                while True:
                    incoming = await asyncio.wait_for(ws.recv(), timeout=20.0)
                    if isinstance(incoming, bytes):
                        print(f"< Binary audio: {len(incoming)} bytes")
                    else:
                        print(f"< Text: {incoming}")
                        data = json.loads(incoming)
                        if data.get("type") == "turn_complete":
                            turn_completed = True
                            # If we received turn_complete and haven't ended yet, send end
                            print("Turn completed. Sending end...")
                            await ws.send(json.dumps({"type": "end"}))
                        elif data.get("type") == "ended":
                            print(f"Session ended cleanly with reason: {data.get('reason')}")
                            break
                        elif data.get("type") == "error":
                            print(f"Received error: {data}", file=sys.stderr)
                            return 1
            except asyncio.TimeoutError:
                print("Timed out waiting for server response.")
                await ws.send(json.dumps({"type": "end"}))

            return 0
    except websockets.exceptions.ConnectionClosedOK:
        print("WebSocket closed cleanly with code 1000 (OK).")
        return 0
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
