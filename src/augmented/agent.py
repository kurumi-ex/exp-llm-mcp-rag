import asyncio
import json
import os

from typing import Optional
from mcp import Tool
from rich import print as rprint

from mcp_client import MCPClient
from chat_openai import AsyncChatBot
from utils import pretty


class Agent:
    def __init__(
            self,
            model: str,
            mcp_clients: Optional[list[MCPClient]],
            system_prompt: str = "",
            context: str = ""
    ):
        self.llm = None
        self.tools = None
        self.model: str = model
        self.system_prompt: str = system_prompt
        self.context: str = context
        self.mcp_clients: list[MCPClient] = mcp_clients

    async def init(self):
        for client in self.mcp_clients:
            await client.init()
        self.tools: list[Tool] = [tool for client in self.mcp_clients for tool in client.get_tools()]
        rprint("\nConnected to server with tools:", [tool.name for tool in self.tools])
        self.llm = AsyncChatBot(
            self.model,
            system_prompt=self.system_prompt,
            context=self.context,
            tools=self.tools,
        )

    async def close(self):
        for client in self.mcp_clients:
            await client.close()

    async def invoke(self, prompt: str):
        if not prompt:
            Exception("No prompt provided")
        response = await self.llm.chat(prompt)

        while True:
            if len(response.tool_calls) > 0:
                for tool_call in response.tool_calls:
                    mcp = None
                    for client in self.mcp_clients:
                        for tool in client.get_tools():
                            if tool.name == tool_call.function.name:
                                mcp = client
                                break
                    if mcp:
                        pretty.log_title(f"TOOL USE '{tool_call.function.name}'")
                        rprint("With args:", tool_call.function.arguments)
                        ans = await mcp.call_tool(tool_call.function.name, json.loads(tool_call.function.arguments))
                        rprint("Result:", ans)
                        self.llm.append_tool_result(tool_call.id, ans.model_dump_json())
                    else:
                        print("Error: Tool not found")
                        self.llm.append_tool_result(tool_call.id, "Tool not found")
                response = await self.llm.chat()
            else:
                return


async def main():
    fetch_client = MCPClient(name="fetch_client", command="uvx", args=["mcp-server-fetch"])
    file_args = [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        os.path.join("G:\\code\\python\\exp-llm-mcp-rag", "tmp_file"),
    ]
    file_client = MCPClient(name="file_client", command="npx", args=file_args)
    system_prompt = "你使用write_file工具进行总结时，你要结合你上文获取的内容进行总结，用中文回答问题"
    agent = Agent("Qwen/Qwen2.5-7B-Instruct", mcp_clients=[fetch_client, file_client], system_prompt=system_prompt)
    await agent.init()
    await agent.invoke("访问https://www.ty-penguin.org.uk/~auj/blog/2025/03/25/fake-jpeg/这个网站，先以markdown的形式为我总结这个页面的内容，"
                       "然后将结果存到本地G:\\code\\python\\exp-llm-mcp-rag\\tmp_file文件夹中")
    await agent.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
