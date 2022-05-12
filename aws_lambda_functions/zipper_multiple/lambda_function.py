import json

from config import VALID_CUSTOM_EVENT_LIST
from zipper_multiple import ZipperMultiple

from logger_builder import build_logger
import logging

logger = logging.getLogger()


def lambda_handler(event, context):

    # build_logger
    build_logger(log_level=logging.INFO, request_id=context.aws_request_id)

    logger.info(f"event: {event}")

    # valid event
    if validate_event(event):

        logger.info("event json valid, OK!")
        bucket_name = event['custom_event']['bucket_name']
        main_dir = event['custom_event']['main_dir']
        zip_files(bucket_name, main_dir)

        return {
            'statusCode': 200,
            'body': json.dumps('OK!')
        }

    # NOT valid event
    else:
        error_msg = "event json NOT valid, you must specify an event json with the structure:" \
                    " {\"custom_event\": {\"bucket_name\": str, {\"main_dir\": str} }" \
                    ", and it has be valid values: " + str(VALID_CUSTOM_EVENT_LIST)
        logger.info(error_msg)
        return {
            'statusCode': 400,
            'body': json.dumps(error_msg)
        }


def validate_event(event):
    if 'custom_event' not in event:
        return False
    else:
        for d in VALID_CUSTOM_EVENT_LIST:
            if all([event['custom_event'].get(k) == d[k] for k in d]):
                return True
        return False


def zip_files(bucket_name, main_dir):
    logger.info(f"zipping files for bucket '{bucket_name}', main_dir '{main_dir}'")

    prefix = f"{main_dir}/{ZipperMultiple.TAG_YEAR}-{ZipperMultiple.TAG_MONTH}-"
    filename_regex = rf"^{ZipperMultiple.TAG_YEAR}-{ZipperMultiple.TAG_MONTH}-\d{{2}}-\d{{2}}-\d{{2}}-\d{{2}}.+"
    file_zip = f"{main_dir}/zip/{ZipperMultiple.TAG_YEAR}-{ZipperMultiple.TAG_MONTH}.zip"
    delete_files = True

    zm = ZipperMultiple(bucket_name, prefix, filename_regex, file_zip)
    zm.zip_files_month_ago(delete_files=delete_files)
