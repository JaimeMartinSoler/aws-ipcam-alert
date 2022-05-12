import boto3
from datetime import datetime as dt
import json

from rekognition_api_calls_service import RekognitionApiCallsService
from config import BUCKET_OUTPUT, FOLDER_OUTPUT, MAX_LABELS, MIN_CONFIDENCE

from logger_builder import build_logger
import logging

logger = logging.getLogger()


def lambda_handler(event, context):
    """
    lambda layer dependencies:
        - logger_builder
        - rekognition_api_calls_service
            - alert_cams_img_service
    """

    # build_logger
    build_logger(log_level=logging.INFO, request_id=context.aws_request_id)

    # get bucket, obj from event
    t_classification = f"{dt.utcnow().isoformat()}Z"
    bucket = event['Records'][0]['s3']['bucket']['name']
    obj = event['Records'][0]['s3']['object']['key']
    logger.info(f"bucket: {bucket}")
    logger.info(f"object: {obj}")

    # validate_and_alert
    rek_api_calls_service = RekognitionApiCallsService()
    validate, (validate_cause, api_calls_month_current, api_calls_month_max_100)\
        = rek_api_calls_service.validate_and_alert(return_metadata=True)

    if validate:

        # get labels
        response_labels = detect_labels(bucket, obj)
        print_labels_data(bucket, obj, response_labels)

        # update rekognition api calls
        rek_api_calls_service.increment_api_calls_month_current()

        # save json with labels data
        json_dict = get_json_data(event, response_labels, bucket, obj, t_classification)
        save_json_dict(json_dict)
        logger.info(
            f"json file created in '{json_dict['Classification']['s3_bucket_name_dst']}"
            f"/{json_dict['Classification']['s3_object_key_dst']}'")

        # return OK
        return {
            'statusCode': 200,
            'body': json.dumps(
                f"File '{bucket}/{obj}' processed, file '{json_dict['Classification']['s3_bucket_name_dst']}"
                f"/{json_dict['Classification']['s3_object_key_dst']}' created, OK!")
        }

    else:
        return {
            'statusCode': 409,  # conflict
            'body': json.dumps(f"File '{bucket}/{obj}' NOT processed, not validated: '{validate_cause}'")
        }


def detect_labels(bucket, obj):
    client = boto3.client('rekognition')

    response = client.detect_labels(
        Image={'S3Object': {'Bucket': bucket, 'Name': obj}},
        MaxLabels=MAX_LABELS,
        MinConfidence=MIN_CONFIDENCE)

    return response


def print_labels_data(bucket, obj, response_labels):
    labels_str_list = ["'{}' ({:.2f}%, #{})".format(label['Name'], label['Confidence'], len(label['Instances']))
                       for label in response_labels['Labels']]
    labels_str = ', '.join(labels_str_list)
    logger.info(f"Detected labels for '{bucket}/{obj}': {labels_str}")


def get_json_data(event, response_labels, bucket, obj, t_classification):
    classification_dict = {
        'Classification': {
            's3_bucket_name_src': bucket,
            's3_object_key_src': obj,
            's3_bucket_name_dst': BUCKET_OUTPUT,
            's3_object_key_dst': f"{FOLDER_OUTPUT}{obj.split('/')[-1]}.json",
            'eventTime': event['Records'][0]['eventTime'],
            'classificationTime': t_classification,
            'MaxLabels': MAX_LABELS,
            'MinConfidence': MIN_CONFIDENCE,
            'labels': [label['Name'] for label in response_labels['Labels']],
        }
    }
    json_dict = {**classification_dict, **event, **response_labels}
    return json_dict


def save_json_dict(json_dict):
    s3 = boto3.client("s3")
    response = s3.put_object(
        Body=json.dumps(json_dict),
        Bucket=json_dict['Classification']['s3_bucket_name_dst'],
        Key=json_dict['Classification']['s3_object_key_dst']
    )
    return response
