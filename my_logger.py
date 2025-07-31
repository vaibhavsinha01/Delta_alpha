# mylogger.py
import os
import logging
from datetime import datetime

def get_logger(name: str = "main"):
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Create filename with current date
    log_filename = f"logs/{datetime.now().strftime('%Y-%m-%d')}.log"

    # Create a custom logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # You can set to INFO or ERROR as needed

    # Avoid adding multiple handlers
    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
