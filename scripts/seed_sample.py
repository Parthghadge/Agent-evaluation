"""Seed sample conversations via API (run after API is up)."""
import asyncio
import json
import httpx

API = "http://localhost:8000/api/v1"


async def main():
    with open("sample_conversations.jsonl") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    async with httpx.AsyncClient() as client:
        r = await client.post(f"{API}/ingest/batch", json=lines, timeout=30)
        r.raise_for_status()
        print(r.json())


if __name__ == "__main__":
    asyncio.run(main())
