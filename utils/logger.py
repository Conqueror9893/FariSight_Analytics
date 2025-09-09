import logging
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'project.log')

def get_logger(name: str = "FariSight"):
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s: %(message)s')

        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
    return logger
