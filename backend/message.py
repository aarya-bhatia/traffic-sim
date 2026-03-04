from multiprocessing.connection import Connection
from utils import get_logger
from client import Client, ClientType
from enum import Enum

logger = get_logger(__name__)


class MessageType(Enum):
    EMPTY = 0
    INTERNAL_ERROR = 1
    MALFORMED_ERROR = 2
    CONNECTION_ERROR = 3
    TIMEOUT_ERROR = 4
    
    # Internal Leader Messages
    EXIT = 10
    NEW_CONNECTION = 11
    NEW_CLIENT = 12
    CLIENT_DISCONNECTED = 13
    
    # Client/Protocol Messages
    PULSE = 20
    REGISTER = 21
    ERROR_UNREGISTERED_CLIENT = 22
    SUCCESS = 23
    ERROR_RESPONSE = 24


class Message:
    def __init__(self, message: MessageType, **kwargs):
        self.message = message
        self.kwargs = kwargs

    def send(self, conn: Connection) -> bool:
        try:
            conn.send(self)
            return True
        except (ConnectionError, BrokenPipeError) as e:
            logger.error(f"failed to send message: {e}")
            return False

    @staticmethod
    def recv(conn: Connection) -> 'Message':
        try:
            message = conn.recv()
            if not isinstance(message, Message):
                logger.error(f"received unexpected object type: {type(message)}")
                return Message(MessageType.MALFORMED_ERROR)
            return message
        except EOFError:
            return Message(MessageType.CONNECTION_ERROR)
        except (ConnectionError, BrokenPipeError):
            return Message(MessageType.CONNECTION_ERROR)
        except Exception as e:
            logger.error(f"unexpected error during receive: {e}")
            return Message(MessageType.INTERNAL_ERROR)


class InternalMessage(Message):
    @staticmethod
    def new_connection_message(connection: Connection) -> 'InternalMessage':
        return InternalMessage(MessageType.NEW_CONNECTION, connection=connection)

    @staticmethod
    def new_client_message(client: Client) -> 'InternalMessage':
        return InternalMessage(MessageType.NEW_CLIENT, client=client)

    @staticmethod
    def exit_message() -> 'InternalMessage':
        return InternalMessage(MessageType.EXIT)


class ClientMessage(Message):
    @staticmethod
    def pulse_message(tick: int, current_state: dict = None) -> 'ClientMessage':
        return ClientMessage(MessageType.PULSE, tick=tick, current_state=current_state or {})

    @staticmethod
    def register_message(client_type: ClientType, client_id: int) -> 'ClientMessage':
        return ClientMessage(MessageType.REGISTER, client_type=client_type, client_id=client_id)

    @staticmethod
    def error_message(error: str) -> 'ClientMessage':
        return ClientMessage(MessageType.ERROR_RESPONSE, error=error)
