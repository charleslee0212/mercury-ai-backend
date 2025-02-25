import logging


def set_up_logger() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: {%(funcName)s} %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
