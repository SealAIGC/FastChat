from pydantic import BaseModel
from enum import Enum

class RouteEnum(Enum):
    sendToRAG = 1
    sendToWorker = 2
    functionCallExtractor = 3

class RouterEnum(Enum):
    JUST_USER_QUERY = 1
    JUST_AI_QUERY = 2
    SYSTEM_AND_USER_QUERY = 3
    SYSTEM_AND_AI_QUERY = 4
    SYSTEM_CHAT_HISTORY = 5
    CHAT_HISTORY = 6

class ActionEnum(Enum):
    NEXT = 1
    ADD_TAG_TO_QUERY = 2
    ADD_TAG_TO_SYSTEM = 3
    ADD_ANSWER_TO_QUERY = 4
    ADD_ANSWER_TO_SYSTEM = 5
