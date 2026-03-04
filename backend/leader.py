import time
import threading
import sys
import queue
import json
from multiprocessing.connection import Listener, Connection
from message import Message, InternalMessage, ClientMessage, MessageType
from utils import get_logger
import argparse
from client import Client, ClientType
from dotenv import load_dotenv
import os

load_dotenv()

MAX_CLIENT_TIMEOUT = 10
logger = get_logger(__name__)


def _fill_missing_state_from_last_known(cur_state: dict, prev_state: dict):
    for client_id, client_state in prev_state.items():
        if client_id not in cur_state:
            cur_state[client_id] = client_state


def _dispatch_worker_thread(message: ClientMessage, client: Client, out_chan: queue.Queue):
    if not message.send(client.conn):
        out_chan.put((client, Message(MessageType.CONNECTION_ERROR)))
        return

    try:
        if client.conn.poll(MAX_CLIENT_TIMEOUT):
            reply = Message.recv(client.conn)
            out_chan.put((client, reply))
        else:
            out_chan.put((client, Message(MessageType.TIMEOUT_ERROR)))
    except Exception as e:
        logger.error(f"Error communicating with client {client.id}: {e}")
        out_chan.put((client, Message(MessageType.INTERNAL_ERROR)))


def _register_client_worker(conn: Connection, message_q: queue.Queue):
    try:
        msg = Message.recv(conn)
        if msg.message != MessageType.REGISTER:
            logger.error(f"registration failed on connection {conn.fileno()}")
            conn.close()
            return

        client = Client(type=msg.kwargs["client_type"],
                        id=msg.kwargs["client_id"], conn=conn)
        conn.send(Message(MessageType.SUCCESS))
        message_q.put(InternalMessage(MessageType.NEW_CLIENT, client=client))
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        conn.close()


def _network_listener(net_addr, message_queue):
    logger.info(f"Listening for connections on {net_addr}")
    try:
        with Listener(address=net_addr) as listener:
            while True:
                try:
                    conn = listener.accept()
                    logger.info("new client connected")
                    threading.Thread(target=_register_client_worker,
                                     args=(conn, message_queue),
                                     daemon=True).start()
                except ConnectionError as e:
                    logger.error(f"Connection error: {e}")
    except Exception as e:
        logger.error(f"Listener error: {e}")


class Leader:
    QUEUE_POLL_TIMEOUT = 0.2
    CLOCK_RATE_MILLIS = 1000

    def __init__(self, hostname: str, port: int, n_intersection: int):
        self.current_tick: int = 0
        self.messages: queue.Queue = queue.Queue()
        self.net_addr: tuple[str, int] = (hostname, port)
        self.n_intersection: int = n_intersection
        self.clients: dict[int, Client] = {}
        self.current_state = {}

    def stop(self):
        self.messages.put(InternalMessage(MessageType.EXIT))

    def _clean_state_for_healthy_clients(self):
        to_del = []
        for client_id in self.current_state.keys():
            if client_id not in self.clients:
                to_del.append(client_id)

        for client_id in to_del:
            del self.current_state[client_id]

    def _next_state(self):
        q = queue.Queue()
        self._clean_state_for_healthy_clients()
        message = ClientMessage.pulse_message(tick=self.current_tick, current_state=self.current_state)

        for client in self.clients.values():
            worker_args = (message, client, q)
            threading.Thread(target=_dispatch_worker_thread,
                             args=worker_args, daemon=True).start()

        state = {}
        unsuccessful_clients = []
        for _ in range(len(self.clients)):
            client, reply = q.get()
            if reply.message != MessageType.SUCCESS:
                logger.error(
                    f"failed to get state from client {client.id}: {reply.message}")
                unsuccessful_clients.append(client)
                continue

            client_id = reply.kwargs["client_id"]
            state[client_id] = reply.kwargs["state"]

        for client in unsuccessful_clients:
            self.messages.put(InternalMessage(
                MessageType.CLIENT_DISCONNECTED, client=client))

        return state

    def _init(self):
        threading.Thread(
            target=_network_listener, daemon=True, args=(self.net_addr, self.messages)).start()

    def _handle_internal_message(self, msg: Message):
        if msg.message == MessageType.NEW_CLIENT:
            client: Client = msg.kwargs["client"]
            self.clients[client.id] = client
            logger.info(f"client registered: {client.id}")
        elif msg.message == MessageType.CLIENT_DISCONNECTED:
            client: Client = msg.kwargs["client"]
            if client.id in self.clients:
                client.conn.close()
                del self.clients[client.id]
                logger.info(f"client disconnected: {client.id}")

    def _tick(self):
        next_state = self._next_state()
        _fill_missing_state_from_last_known(next_state, self.current_state)
        self.current_state = next_state
        logger.info(f"current state: {next_state}")
        self.current_tick += 1

    def run(self):
        self._init()
        next_tick_time = time.time()

        while True:
            cur_time = time.time()
            if cur_time >= next_tick_time:
                next_tick_time = time.time() + Leader.CLOCK_RATE_MILLIS/1000.0
                self._tick()

            time_to_wait = min(Leader.QUEUE_POLL_TIMEOUT,
                               max(0, next_tick_time - cur_time))
            try:
                msg: InternalMessage = self.messages.get(timeout=time_to_wait)
                if msg.message == MessageType.EXIT:
                    logger.info("operator exit message")
                    break
                self._handle_internal_message(msg)
            except queue.Empty:
                continue


def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    leader_hostname = os.environ["LEADER_HOSTNAME"]
    leader_port = int(os.environ["LEADER_PORT"])
    n_intersection = int(os.environ.get("NUM_INTERSECTIONS", 0))
    config_file = os.environ["CONFIG_FILE"]

    try:
        file = open(config_file, "r").read()
        config = json.loads(file)
        logger.info("Config loaded.")
        print(config)
    except FileNotFoundError as e:
        logger.error(f"Config file not found: {e}")
        sys.exit(1)

    leader = Leader(hostname=leader_hostname,
                    port=leader_port, n_intersection=n_intersection)
    logger.info("Starting leader...")
    threading.Thread(target=leader.run).start()

    try:
        input()
    except KeyboardInterrupt:
        logger.info("Exiting program...")
        leader.stop()


if __name__ == "__main__":
    main()
