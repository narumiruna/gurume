"""Opt-in live check of Gurume's stdio MCP tools and upstream Tabelog access."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult


def summarize(result: CallToolResult, *, require_items: bool = False) -> dict[str, Any]:
    """Keep live check output small while preserving structured failure guidance."""
    data = result.structuredContent
    if result.isError or not isinstance(data, dict):
        return {"status": "error", "message": "MCP tool did not return a structured response"}

    status = data.get("status")
    if status != "success":
        return {"status": status, "error": data.get("error")}
    count = data.get("returned_count")
    if require_items and (not isinstance(count, int) or count < 1):
        return {"status": "no_results", "message": "Expected at least one result"}
    return {"status": "success", "returned_count": count} if isinstance(count, int) else {"status": "success"}


async def check_live(restaurant_url: str | None = None) -> dict[str, Any]:
    """Check independent tool paths; use a search result URL for details when available."""
    checks: dict[str, dict[str, Any]] = {}
    server = StdioServerParameters(command="uv", args=["run", "gurume", "mcp"])
    async with stdio_client(server) as (reader, writer), ClientSession(reader, writer) as session:
        await session.initialize()
        for name, tool, arguments in (
            ("cuisines", "tabelog_list_cuisines", {}),
            ("area_suggestions", "tabelog_get_area_suggestions", {"query": "東京"}),
            ("search", "tabelog_search_restaurants", {"area": "東京", "cuisine": "寿司", "limit": 1}),
        ):
            response = await session.call_tool(tool, arguments)
            checks[name] = summarize(response, require_items=True)
            if name == "search" and checks[name]["status"] == "success" and restaurant_url is None:
                data = response.structuredContent
                if isinstance(data, dict) and isinstance(data.get("items"), list) and data["items"]:
                    first = data["items"][0]
                    if isinstance(first, dict) and isinstance(first.get("url"), str):
                        restaurant_url = first["url"]

        if restaurant_url:
            response = await session.call_tool(
                "tabelog_get_restaurant_details",
                {
                    "restaurant_url": restaurant_url,
                    "fetch_reviews": False,
                    "fetch_menu": False,
                    "fetch_courses": False,
                },
            )
            checks["details"] = summarize(response)
        else:
            checks["details"] = {
                "status": "skipped",
                "message": "Pass --restaurant-url to test details independently",
            }

    return {
        "status": "ok" if all(check["status"] == "success" for check in checks.values()) else "degraded",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Gurume's stdio MCP tools against live Tabelog pages")
    parser.add_argument("--restaurant-url", help="Known working Tabelog restaurant URL for an independent detail check")
    args = parser.parse_args()
    try:
        result = asyncio.run(check_live(args.restaurant_url))
    except Exception as error:  # noqa: BLE001
        result = {"status": "error", "message": f"MCP connection or check failed: {error}"}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
