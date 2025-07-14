import os
import logging


def get_logger(name: str = __name__) -> logging.Logger:
    """
    Returns a configured logger instance for the given module name.

    This logger logs to both:
    - A file located at backend/config/logs/app.log
    - The console (stdout)

    The function ensures the logs directory exists before writing.

    Args:
        name (str): The name of the logger (usually __name__).

    Returns:
        logging.Logger: Configured logger instance.
    """
    log_dir = os.path.join("backend", "config")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    logger = logging.getLogger(name)

    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)

        # File Handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(file_formatter)
        logger.addHandler(console_handler)

    return logger
