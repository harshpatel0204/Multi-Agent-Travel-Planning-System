import os

from collections.abc import AsyncIterable
from typing import Any, Literal

import httpx

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


memory = MemorySaver()


@tool
def get_exchange_rate(
    currency_from: str = 'USD',
    currency_to: str = 'EUR',
    currency_date: str = 'latest',
):
    """Use this to get the current exchange rate.

    Args:
        currency_from: The currency to convert from (e.g., "USD").
        currency_to: The currency to convert to (e.g., "EUR").
        currency_date: The date for the exchange rate or "latest". Defaults to
            "latest".

    Returns:
        A dictionary containing the exchange rate data, or an error message if
        the request fails.
    """
    try:
        response = httpx.get(
            f'https://api.frankfurter.app/{currency_date}',
            params={'from': currency_from, 'to': currency_to},
        )
        response.raise_for_status()

        data = response.json()
        if 'rates' not in data:
            return {'error': 'Invalid API response format.'}
        return data
    except httpx.HTTPError as e:
        return {'error': f'API request failed: {e}'}
    except ValueError:
        return {'error': 'Invalid JSON response from API.'}


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""

    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class CurrencyAgent:
    """CurrencyAgent - a specialized assistant for currency conversions."""

    SYSTEM_INSTRUCTION = (
        'You are a specialized assistant for currency conversions. '
        "Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates. "
        'If the user asks about anything other than currency conversion or exchange rates, '
        'politely state that you cannot help with that topic and can only assist with currency-related queries. '
        'Do not attempt to answer unrelated questions or use tools for other purposes.'
    )

    FORMAT_INSTRUCTION = (
        'Set response status to input_required if the user needs to provide more information to complete the request.'
        'Set response status to error if there is an error while processing the request.'
        'Set response status to completed if the request is complete.'
    )

    def __init__(self):
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set.")
        
        self.model = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
            model="openai/gpt-4o-mini",
            temperature=0,
            default_headers={
                "HTTP-Referer": "http://localhost",  # required by OpenRouter
                "X-Title": "TravelPlanningSystem",  # optional but good practice
            },
            model_kwargs={},  # ← CRITICAL: empty this to prevent unsupported params
        )
        
        self.tools = [get_exchange_rate]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
        )

    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': context_id}}

        for item in self.graph.stream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Looking up the exchange rates...',
                }
            elif isinstance(message, ToolMessage):
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing the exchange rates..',
                }

        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        messages = current_state.values.get("messages", [])
        
        if messages:
            final_message = messages[-1]
            if hasattr(final_message, 'content'):
                response_text = final_message.content
            else:
                response_text = str(final_message)
            
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response_text,
            }
        
        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": (
                "We are unable to process your request at the moment. "
                "Please try again."
            ),
        }

    def invoke(self, query, context_id):
        """Synchronously invoke method for compatibility."""
        try:
            print(f"💱 CurrencyAgent.invoke called with query: {query}, context_id: {context_id}")
            config: RunnableConfig = {"configurable": {"thread_id": context_id}}
            
            print(f"🔄 Calling self.graph.invoke...")
            response = self.graph.invoke({"messages": [("user", query)]}, config)
            print(f"📦 Graph response received: {type(response)}")
            
            # Extract the final message content
            if "messages" not in response:
                print(f"❌ No 'messages' key in response: {response}")
                return "Error: No messages in response"
                
            messages = response["messages"]
            print(f"📧 Number of messages: {len(messages)}")
            
            if not messages:
                print(f"❌ Empty messages list")
                return "Error: Empty messages list"
                
            final_message = messages[-1]
            print(f"📧 Final message type: {type(final_message)}")
            
            if hasattr(final_message, 'content'):
                response_text = final_message.content
                print(f"✅ Extracted content: {response_text}")
            else:
                response_text = str(final_message)
                print(f"✅ Converted to string: {response_text}")
            
            print(f"🎯 Final response: {response_text}")
            return response_text
        except Exception as e:
            print(f"💥 Exception in CurrencyAgent.invoke: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"🔍 Full traceback: {traceback.format_exc()}")
            raise

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']