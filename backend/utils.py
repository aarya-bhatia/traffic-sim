import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)sZ - %(name)s - %(levelname)s - %(message)s',
                    datefmt="%Y-%m-%dT%H:%M:%S"
                    )


def get_logger(name: str):
    return logging.getLogger(name)


