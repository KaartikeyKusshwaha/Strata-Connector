import json
import os
import asyncio
from pathlib import Path
from connector_mcp.server import mcp

def test_mcp_tool_contract():
    # Load golden fixture
    fixture_path = Path(__file__).parent.parent.parent / "contracts" / "fixtures" / "mcp_tool_contract_golden.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        golden = json.load(f)

    # In mcp library list_tools might be async or synchronous depending on FastMCP version
    # Let's inspect tools directly. FastMCP tool_manager.list_tools() could be async.
    # We will try to handle if it is a coroutine
    try:
        tools_result = mcp._tool_manager.list_tools()
        if asyncio.iscoroutine(tools_result):
            actual_tools = asyncio.run(tools_result)
        else:
            actual_tools = tools_result
    except Exception:
        # Fallback
        actual_tools = mcp._tool_manager.list_tools()
        
    assert len(actual_tools) == golden["tool_count"]
    
    golden_tools_dict = {t["name"]: t for t in golden["tools"]}
    for actual_tool in actual_tools:
        name = actual_tool.name
        assert name in golden_tools_dict, f"Tool {name} not in golden fixture"
        golden_tool = golden_tools_dict[name]
        
        # Compare description (first line)
        first_line = actual_tool.description.split("\n")[0].strip()
        assert first_line == golden_tool["description"]
        
        # Test mutating flag
        is_mutating = "MUTATING" in actual_tool.description
        assert is_mutating == golden_tool["is_mutating"]
        
        if golden_tool["is_mutating"]:
            assert "MUTATING" in actual_tool.description
