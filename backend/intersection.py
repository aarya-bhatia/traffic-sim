from multiprocessing.connection import Client
from client import ClientType
from utils import get_logger
import sys
import argparse
import time
from message import ClientMessage, Message, MessageType
from dotenv import load_dotenv
import os

load_dotenv()

leader_hostname = os.environ["LEADER_HOSTNAME"]
leader_port = int(os.environ["LEADER_PORT"])
leader_addr = (leader_hostname, leader_port)

parser = argparse.ArgumentParser()
parser.add_argument("--id", required=True, type=int)
args = parser.parse_args()
id = args.id

connection_retry_interval = 1
logger = get_logger(__name__)

MAX_CLIENT_TIMEOUT = 10

while True:
    try:
        with Client(leader_addr) as conn:
            logger.info("connected to leader")
            msg = ClientMessage.register_message(
                client_type=ClientType.INTERSECTION_CLIENT, client_id=id)
            conn.send(msg)
            
            msg = Message.recv(conn)
            if msg.message != MessageType.SUCCESS:
                logger.error(f"registration failed: {msg.message}")
                sys.exit(0)

            while True:
                logger.debug("waiting for command from leader")
                if not conn.poll(MAX_CLIENT_TIMEOUT):
                    raise Exception("Connection Timeout")
                
                msg = Message.recv(conn)
                if msg.message == MessageType.PULSE:
                    tick = msg.kwargs.get('tick')
                    logger.info(f"Got pulse at {tick}")
                    
                    # TODO: Implement actual state logic here
                    current_state = {"status": "green"} 
                    
                    # Send response back to leader
                    response = Message(MessageType.SUCCESS, 
                                     client_id=id, 
                                     state=current_state)
                    conn.send(response)
                elif msg.message == MessageType.CONNECTION_ERROR:
                    raise Exception("Leader closed connection")

    except Exception as e:
        logger.error(f"client disconnected: {e}")

    logger.info(f"Reconnecting in {connection_retry_interval} seconds...")
    time.sleep(connection_retry_interval)
