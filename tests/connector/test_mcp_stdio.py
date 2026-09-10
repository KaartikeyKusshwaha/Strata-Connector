import asyncio
import pytest
import sys
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

def test_mcp_stdio_tools_list():
    async def run_test():
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "connector_mcp.server"],
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                
                assert len(result.tools) == 11
                
                tool_names = [t.name for t in result.tools]
                assert "strata_preflight_world" in tool_names
                assert "strata_inspect_library" in tool_names
                assert "strata_submit_managed_build" in tool_names
                assert "strata_get_job_status" in tool_names
                assert "strata_download_result" in tool_names
                assert "strata_open_result_in_blender" in tool_names
                assert "strata_get_chunk_streaming_status" in tool_names
                assert "strata_load_chunk_radius" in tool_names
                assert "strata_set_interactive_block_state" in tool_names
                assert "strata_keyframe_interactive_block_state" in tool_names
                assert "strata_pair_blender" in tool_names

    asyncio.run(run_test())
