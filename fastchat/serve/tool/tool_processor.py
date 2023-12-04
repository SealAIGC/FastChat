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
        self.tool_message = str()

    
    def retrieve_function(self, function_name: str) -> dict:
        function = self.collection.find_one({"name": function_name})
        return function


    def extraxt_result(self) -> str:
        pattern = re.compile(r'\{(?:[^{}]|(?R))*\}')
        matches = pattern.findall(self.tool_message)

        return matches[0]
            

    def add_message(self, message: str):
        message.replace("data: ", "", 1)

        if "<tool>" in message:
            self.recording = True
            self.tool_message = str()

        if self.recording:
            self.tool_message += message

        if "</tool>" in message:
            self.recording = False
            return "data: " + self.process()
        
    
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