import os
import json
import httpx
import regex as re

from .router_base import RouterEnum, ActionEnum
from fastchat.conversation import Conversation, SeparatorStyle

from typing import Generator, Any, Dict
from pymongo import MongoClient, collection, database

class routerProcessor:
    def __init__(self, chat_message, params) -> None:
        # setup mongo client
        mongo_uri: str = os.environ.get('MONGO_URI', "mongodb://seal:seal-mongo-password@140.113.114.146:27017")
        self.client: MongoClient = MongoClient(mongo_uri)
        self.db: database = self.client['Agent']
        self.collection: collection = self.db['apps']

        # setup chat message
        self.params = params
        self.chat_message = chat_message

        # init vars
        self.app = None
        self.isRAG = None
        self.routers = None

    def build_data(self, query_type: str) -> list:
        query_type = RouterEnum[query_type]

        if query_type == RouterEnum.JUST_USER_QUERY:
            user_query = []
            for message in self.chat_message:
                user_query.append(message)
            return user_query[-1:]


    def build_params(self, parameter: dict) -> dict:
        prompt = ""
        params = {}
        for param in parameter:
            params[param] = parameter[param]['value']

        prompt = params['app_prompt']
        del params['app_prompt']

        return prompt, params
    
    def build_prompt(self, format: str, keyword: str, prompt: str, messages: dict) -> str:
        for message in messages:
            prompt += f""" USER: <INPUT>{json.dumps(
                {
                    keyword: message['content']
                }
            )}</INPUT>"""

        return prompt + " ASSISTANT:"
    
    def extraxt_result(self, format: str, keyword: str, response: dict) -> str:
        response = response['text']

        pattern = re.compile(r'\{(?:[^{}]|(?R))*\}')
        matches = pattern.findall(response[response.find("<RESULT>") : response.find("</RESULT>") + 9])

        for match in matches:
            match = json.loads(match)
            if keyword in match:
                return match[keyword]

    def do_action(self, actions: list, result: str) -> str:
        for action in actions:
            if result != action['extract_answer']:
                continue

            action_type = ActionEnum[action['action']]

            if action_type == ActionEnum.NEXT:
                pass
            elif action_type == ActionEnum.ADD_TAG_TO_QUERY:
                self.chat_message[-1]['content'] += "\n\n" + action['tag']
            return action['message']

    
    async def get_worker_address(self, model_name: str, client: httpx.AsyncClient) -> str:
        controller_address = "http://controller.spearlink.seal3.io"

        ret = await client.post(
            controller_address + "/get_worker_address", json={"model": model_name}
        )
        worker_addr = ret.json()["address"]
        # No available worker
        if worker_addr == "":
            raise ValueError(f"No available worker for {model_name}")

        return worker_addr
    
    async def generate_completion(self, payload: Dict[str, Any]):
        async with httpx.AsyncClient() as client:
            worker_addr = await self.get_worker_address(payload["model"], client)

            response = await client.post(
                worker_addr + "/worker_generate",
                headers={"User-Agent": "FastChat API Server"},
                json=payload,
                timeout=3000,
            )
            
            completion = response.json()
            return completion
        
    def pack_message(self, message: str) -> str:
        return f"""data: {
            json.dumps({
                "choices": [
                    {
                        "delta": {
                            "content": message,
                            "role": "assistant"
                        }
                    }
                ]
            })
        }\n\n"""

    async def process(self) -> Generator[str, Any, None]:
        if not self.isRAG:
            return
        if self.isRAG['RAG'] == True:
            yield self.pack_message(f"""<SYSTEM>{
                    {"task":"RAG","params":{"message": f"start {self.app['AgentName']} RAG"}}
                }</SYSTEM>""")

        for router in self.routers:
            router_app = self.collection.find_one({"AgentName": router['name']})

            yield self.pack_message(f"""<SYSTEM>{
                {"task":"agentLinkAction","params":{"message": f"Start " + router['name']}}
            }</SYSTEM>""")

            prompt, params = self.build_params(router_app['Parameter'])

            query_data = self.build_data(router['input'])

            params = self.params

            params['prompt'] = self.build_prompt(
                format=router_app['api_parameter']['input_format'],
                keyword=router_app['api_parameter']['inpurt_extract_word'],
                prompt=prompt,
                messages=query_data
            )

            response = await self.generate_completion(params)

            result = self.extraxt_result(
                format=router_app['api_parameter']['output_format'],
                keyword=router_app['api_parameter']['output_extract_word'],
                response=response
            )

            action_message = self.do_action(router_app['api_parameter']['result_and_action'], result)

            return_message = response['text'].replace("\"", "\\\"")
            yield self.pack_message(f"""<SYSTEM>{
                {"task":"agentLinkAction","params":{"message": return_message}}
            }</SYSTEM>""")
        if self.isRAG['RAG'] == True or len(self.routers) > 0:
            yield self.pack_message(f"""<SYSTEM>{
                {"task":"done","params":{"message":""}}
            }</SYSTEM>""")

    def retrieve_routes(self, app_name: str) -> None:
        self.app = self.collection.find_one({"AgentName": app_name})
        if self.app['isRAG'] is not None:
            self.isRAG = self.app['isRAG']
        self.routers = self.app['routers']

    def __del__(self) -> None:
        self.client.close()
