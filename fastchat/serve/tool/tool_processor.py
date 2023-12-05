import os
from pymongo import MongoClient, collection, database

import requests
import regex as re
import json


class toolProcessor:
    def __init__(self, chat_message):
        # setup mongo client
        mongo_uri: str = os.environ.get(
            "MONGO_URI", "mongodb://seal:seal-mongo-password@140.113.114.146:27017"
        )
        self.client: MongoClient = MongoClient(mongo_uri)
        self.db: database = self.client["APIStore"]
        self.collection: collection = self.db["APIs"]

        # setup chat message
        self.chat_message = chat_message
        self.last_check_index = 0

        self.tool_message = None

    def retrieve_function(self, function_name: str) -> dict:
        function = self.collection.find_one({"name": function_name})
        return function

    def extraxt_result(self) -> str:
        output_message = self.chat_message[-1]["content"]
        self.tool_message = output_message[
            output_message.find("<tool>") : output_message.find("</tool>") + 7
        ]

        pattern = re.compile(r"\{(?:[^{}]|(?R))*\}")
        matches = pattern.findall(self.tool_message)

        return json.loads(matches[0].replace("\\", ""))

    def add_message(self, message: str):
        message = message.replace("data: ", "", 1)
        if "[DONE]" in message:
            return

        template = message = json.loads(message)

        if "role" in message["choices"][0]["delta"]:
            self.chat_message.append(
                {"role": message["choices"][0]["delta"]["role"], "content": str()}
            )

        if "content" in message["choices"][0]["delta"]:
            self.chat_message[-1]["content"] += message["choices"][0]["delta"][
                "content"
            ]

        if "</tool>" in self.chat_message[-1]["content"][self.last_check_index :]:
            response = self.extraxt_result()

            response["result"] = self.process()
            template["choices"][0]["delta"]["content"] = "<tool>" + json.dumps(response) + "</tool>"

            self.chat_message[-1]["content"] = self.chat_message[-1]["content"].replace(
                self.tool_message, response["result"]
            )
            self.last_check_index = len(self.chat_message[-1]["content"])

            return "data: " + json.dumps(template) + "\n\n"

    def send_request(self, function: dict, params: dict) -> dict:
        url = function["execute"]["url"]
        method = function["execute"]["method"]

        response = requests.request(method, url, params=params)

        return response.text

    def process(self) -> str:
        call_info = self.extraxt_result()
        function_name = call_info["function_name"]
        params = call_info["argument"]

        function = self.retrieve_function(function_name)

        result = self.send_request(function, params)
        return result
