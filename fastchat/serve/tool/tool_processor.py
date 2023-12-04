import os
from pymongo import MongoClient, collection, database

import requests
import regex as re
import json

class toolProcessor:
    def __init__(self):
         # setup mongo client
        mongo_uri: str = os.environ.get('MONGO_URI', "mongodb://seal:seal-mongo-password@140.113.114.146:27017")
        self.client: MongoClient = MongoClient(mongo_uri)
        self.db: database = self.client['APIStore']
        self.collection: collection = self.db['APIs']

        # setup record
        self.recording = False
        self.output_message = str()

    
    def retrieve_function(self, function_name: str) -> dict:
        function = self.collection.find_one({"name": function_name})
        return function


    def extraxt_result(self) -> str:
        tool_message = self.output_message[self.output_message.find("<tool>"):self.output_message.find("</tool>")+7]

        pattern = re.compile(r'\{(?:[^{}]|(?R))*\}')
        matches = pattern.findall(tool_message)

        return matches[0]
            

    def add_message(self, message: str):
        message = message.replace("data: ", "", 1)
        if "[DONE]" in message:
            return

        template = message = json.loads(message)

        if 'content' not in message['choices'][0]['delta']:
            return
        
        message = message['choices'][0]['delta']['content']
        self.output_message += message

        if "</tool>" in self.output_message:
            self.recording = False
            response = json.loads(self.extraxt_result())
            response['result'] = "<tool>" + self.process() + "</tool>"
            template['choices'][0]['delta']['content'] = response
            self.output_message = str()
            return "data: " + json.dumps(template) + "\n\n"
        
    
    def send_request(self, function: dict, params: dict) -> dict:
        url = function["execute"]["url"]
        method = function["execute"]["method"]

        response = requests.request(method, url, params=params)

        return response.text


    def process(self) -> str:
        generate_call_info = self.extraxt_result()

        call_info = json.loads(generate_call_info)
        function_name = call_info["function_name"]
        params = call_info["argument"]

        function = self.retrieve_function(function_name)

        result = self.send_request(function, params)
        return result