import logging
import os
import sys
import uuid

# ------------------------------------------------------------------------------
# USAGE:
#
# lambda_function.py:
#
#   # import the logger normally, from logging, and also build_logger:
#   from logger_builder import build_logger
#   import logging
#   logger = logging.getLogger()
#
#   # call build_logger() in the first line of lambda_handler()
#   def lambda_handler(event, context):
#       build_logger(log_level=logging.INFO, request_id=context.aws_request_id)
#
# any_other_file.py
#   # import the logger normally, from logging:
#   import logging
#   logger = logging.getLogger()
# ------------------------------------------------------------------------------


# config logger
LOG_LEVEL_DEFAULT = logging.INFO
LOGGER_FORMAT = '[%(asctime)s] [%(levelname)s] [__request_id__] %(module)s.%(funcName)s[#%(lineno)s]: %(message)s'
REQUEST_ID_DEFAULT_LEN = 8


def build_logger(log_level=LOG_LEVEL_DEFAULT, request_id=None):
    
    # clear logger
    logger = logging.getLogger()
    logger.handlers = []
    
    # formatter
    if request_id is None:
        request_id = _get_request_id_default()
    stdout_formatter = logging.Formatter(fmt=LOGGER_FORMAT.replace('__request_id__', request_id))
    
    # handler
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.setFormatter(stdout_formatter)
    logger.addHandler(stdout_handler)

    if "DEBUG" in os.environ and os.environ["DEBUG"] == "true":
        logger.setLevel("DEBUG")
    else:
        logger.setLevel(log_level)
        logging.getLogger("boto3").setLevel(logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)

    return logger


def _get_request_id_default(request_id_len=REQUEST_ID_DEFAULT_LEN):
    request_id = uuid.uuid4().hex
    request_id = request_id[:min(request_id_len, len(request_id))]
    return request_id
