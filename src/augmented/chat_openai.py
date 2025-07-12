import asyncio
import os
from mcp import Tool
from openai import AsyncOpenAI
from dataclasses import dataclass, field

from openai.types import FunctionDefinition
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)
import dotenv
from pydantic import BaseModel
from rich import print as rprint

from augmented.utils import pretty

dotenv.load_dotenv()


class ToolCallFunction(BaseModel):
    name: str = ""
    arguments: str = ""


class ToolCall(BaseModel):
    id: str = ""
    function: ToolCallFunction = ToolCallFunction()


class ChatOpenAIChatResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCall] = []


@dataclass
class AsyncChatBot:
    """
    """
    model: str
    messages: list[ChatCompletionMessageParam] = field(default_factory=list)
    tools: list[Tool] = field(default_factory=list)

    system_prompt: str = ""
    context: str = ""

    def __post_init__(self):
        """
        钩子函数 创建模型 prompt context....
        """
        self.llm = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        if self.system_prompt:
            self.messages.insert(0, {"role": "system", "content": self.system_prompt})
        if self.context:
            self.messages.append({"role": "user", "content": self.context})

    async def chat(self, prompt: str = "", print_llm_output: bool = True) -> ChatOpenAIChatResponse:
        pretty.log_title("Chat")

        if prompt:
            pretty.log_title("User Question")
            self.messages.append({"role": "user", "content": prompt})
            print(prompt)
            print()

        # 处理回答
        streaming = await self.llm.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.get_tool_definition(),
            stream=True
        )

        bot_ans = ""
        tool_calls: list[ToolCall] = []

        if print_llm_output:
            pretty.log_title(self.model + " Answer")

        async for chunk in streaming:
            # print(chunk) 回答是拆成单个字符块回答的
            # ChatCompletionChunk(id='0197bb546bad4764f72b7f4e3e7a6eac', choices=[Choice(delta=ChoiceDelta(content='是', function_call=None, refusal=None, role='assistant', tool_calls=None, reasoning_content=None), finish_reason=None, index=0, logprobs=None)], created=1751194561, model='Qwen/Qwen2.5-7B-Instruct',
            delta = chunk.choices[0].delta

            # 处理文本
            if delta.content:
                bot_ans += delta.content or None
                if print_llm_output:
                    print(delta.content, end="")

            # 处理工具调用
            if delta.tool_calls:
                # 存储工具调用信息
                for tool_call_chunk in delta.tool_calls:
                    # 第一次收到一个tool_call
                    if tool_call_chunk.id:
                        tool_calls.append(ToolCall())
                        tool_calls[-1].id = tool_call_chunk.id or ""
                        tool_calls[-1].function.name = tool_call_chunk.function.name or ""

                    current_call = tool_calls[tool_call_chunk.index]
                    if tool_call_chunk.function:
                        current_call.function.arguments += tool_call_chunk.function.arguments or ""
        if print_llm_output:
            print()

        self.messages.append(
            {
                "role": "assistant",
                "content": bot_ans,
                "tool_calls": [
                    {
                        "type": "function",
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        return ChatOpenAIChatResponse(content=bot_ans, tool_calls=tool_calls)

    def get_tool_definition(self) -> list[ChatCompletionToolParam]:
        return [
            ChatCompletionToolParam(
                type="function",
                function=FunctionDefinition(
                    name=t.name,
                    description=t.description,
                    parameters=t.inputSchema,
                ),
            )
            for t in self.tools
        ]

    def append_tool_result(self, tool_call_id: str, tool_output: str) -> None:
        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": tool_output,
            }
        )


if __name__ == "__main__":
    bot = AsyncChatBot(model=os.environ.get("MODEL_TYPE"), system_prompt="你是个笨蛋，你认为1+1等于3")
    asyncio.run(bot.chat("1+1等于几？"))
