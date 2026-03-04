from enum import Enum
from multiprocessing.connection import Connection


class ClientType(Enum):
    INTERSECTION_CLIENT = 0
    CAR_CLIENT = 1


class Client:
    def __init__(self, type: ClientType, id: int, conn: Connection):
        self.type = type
        self.id = id
        self.conn = conn

