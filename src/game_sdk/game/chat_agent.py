from typing import Any, Callable, Dict, List, Optional
from game_sdk.game.custom_types import (
    FunctionResult,
    GameChatResponse,
    Function,
    AgentMessage,
)
from game_sdk.game.api_v2 import GAMEClientV2


class Chat:
    def __init__(
        self,
        conversation_id: str,
        client: GAMEClientV2,
        message_handler: Callable[[AgentMessage], None],
        action_space: Optional[List[Function]] = None,
        get_state_fn: Optional[Callable[[], Dict[str, Any]]] = None,
    ):
        self.chat_id = conversation_id
        self.client = client
        self.action_space = (
            {f.fn_name: f for f in action_space} if action_space else None
        )
        self.get_state_fn = get_state_fn
        self.message_handler = message_handler

    def next(self, message: str) -> bool:
        convo_response = self._update_conversation(message)

        if convo_response.message:
            self.message_handler(
                AgentMessage(message=convo_response.message, chat_id=self.chat_id)
            )

        if convo_response.function_call:
            if not self.action_space:
                raise Exception("No functions provided")

            fn_name = convo_response.function_call.fn_name

            fn_to_call = self.action_space.get(fn_name)
            if not fn_to_call:
                raise Exception(
                    f"Function {fn_name}, returned by the agent, not found in action space"
                )

            result = fn_to_call.execute(
                **{
                    "fn_id": convo_response.function_call.id,
                    "args": convo_response.function_call.args,
                }
            )
            function_report_response = self._report_function_result(result)
            self.message_handler(
                AgentMessage(message=function_report_response, chat_id=self.chat_id)
            )
        return not convo_response.is_finished

    def end(self, message: Optional[str] = None):
        self.client.end_chat(
            self.chat_id,
            {
                "message": message,
            },
        )

    def _update_conversation(self, message: str) -> GameChatResponse:
        data = {
            "message": message,
            "state": self.get_state_fn() if self.get_state_fn else None,
            "functions": (
                [f.get_function_def() for f in self.action_space.values()]
                if self.action_space
                else None
            ),
        }
        result = self.client.update_chat(self.chat_id, data)
        return GameChatResponse.model_validate(result)

    def _report_function_result(self, result: FunctionResult) -> str:
        data = {
            "fn_id": result.action_id,
            "result": (
                f"{result.action_status.value}: {result.feedback_message}"
                if result.feedback_message
                else result.action_status.value
            ),
        }
        response = self.client.report_function(self.chat_id, data)

        message = response.get("message")
        if not message:
            raise Exception("Agent did not return a message for the function report.")
        return message


class ChatAgent:
    def __init__(
        self,
        prompt: str,
        api_key: str,
        get_state_fn: Optional[Callable[[], Dict[str, Any]]] = None,
    ):
        self.prompt = prompt
        self.api_key = api_key
        self.get_state_fn = get_state_fn

        if api_key.startswith("apt-"):
            self.client = GAMEClientV2(api_key)
        else:
            raise Exception("Please use V2 API key to use ChatAgent")

    def create_chat(
        self,
        partner_id: str,
        partner_name: str,
        message_handler: Callable[[AgentMessage], None],
        action_space: Optional[List[Function]] = None,
    ) -> Chat:
        chat_id = self.client.create_chat(
            {
                "prompt": self.prompt,
                "partner_id": partner_id,
                "partner_name": partner_name,
            },
        )

        return Chat(
            chat_id,
            self.client,
            message_handler,
            action_space,
            self.get_state_fn,
        )