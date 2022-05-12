import io
import json
import os
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from alert_cams_img_service import AlertCamsImgService
from config import LABELS_ALERT, AWS_SES_REGION, SENDER, RECIPIENT_LIST, SUBJECT, CHARSET,\
    BODY_TEXT_TEMPLATE, BODY_HTML_TEMPLATE

from logger_builder import build_logger
import logging

logger = logging.getLogger()


def lambda_handler(event, context):
    """
    https://docs.aws.amazon.com/ses/latest/dg/send-email-raw.html

    lambda layer dependencies:
        - logger_builder
        - alert_cams_img_service
    """

    # build_logger
    build_logger(log_level=logging.INFO, request_id=context.aws_request_id)

    # AlertCamsImgService
    alert_service = AlertCamsImgService()
    alert_validate, (alert_period, alert_last_date, alert_second_since_last) = \
        alert_service.validate_period(return_metadata=True)

    # do not alert before alert_period
    if not alert_validate:
        log_msg = f"NOT checking new alerts BEFORE alert period ({alert_period} s)" \
                  f", last alert was on '{alert_last_date}' ({alert_second_since_last} s ago)"
        logger.info(log_msg)
        return {
            'statusCode': 409,
            'body': json.dumps(log_msg)
        }

    # if alert_period exceeded, check new alerts
    else:
        logger.info(
            f"checking new alerts after alert period ({alert_period} s)"
            f", last alert was on '{alert_last_date}' ({alert_second_since_last} s ago)")

        # get dict with the classification information:
        # s3_bucket_name_src, s3_object_key_src, s3_bucket_name_dst, s3_object_key_dst, labels
        class_dict = get_class_dict(event)
        logger.info(f"s3_src: '{class_dict['s3_bucket_name_src']}/{class_dict['s3_object_key_src']}'")
        logger.info(f"s3_dst: '{class_dict['s3_bucket_name_dst']}/{class_dict['s3_object_key_dst']}'")
        logger.info(f"labels: '{class_dict['labels']}'")
        logger.info(f"labels_alert: '{LABELS_ALERT}'")

        # validate alert:

        # labels_alert_found ?
        labels_alert_lower = [label_alert.lower() for label_alert in LABELS_ALERT]
        labels_alert_found = [label for label in class_dict['labels'] if label.lower() in labels_alert_lower]

        # no: no alert, ok
        if len(labels_alert_found) == 0:
            log_msg = f"label alerts ({LABELS_ALERT}) NOT found in labels ({class_dict['labels']}), NO alert, OK!"
            logger.info(log_msg)
            return {
                'statusCode': 200,
                'body': json.dumps(log_msg)
            }

        # yes: alert!
        else:
            log_msg = f"label alerts found ({labels_alert_found}) in labels, ALERT !!!"
            logger.info(log_msg)
            logger.info(f"SENDER: {SENDER}")
            logger.info(f"RECIPIENT_LIST: {RECIPIENT_LIST}")
            logger.info(f"SUBJECT: {SUBJECT}")

            # build_ses_msg
            msg = build_ses_msg(class_dict, labels_alert_found)

            # send_ses_msg
            response = send_ses_msg(msg)

            # update alert_last_date
            alert_service.update_last_date()

            # return OK
            if response:
                return {
                    'statusCode': 200,
                    'body': json.dumps(f"Email sent, OK!: ({log_msg})")
                }


def get_output_dict(event):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    s3_resource = boto3.resource('s3')
    obj = s3_resource.Object(bucket, key)
    data = obj.get()['Body'].read().decode('utf-8')
    data_dict = json.loads(data)

    return data_dict


def get_class_dict(event):
    output_dict = get_output_dict(event)
    class_dict = output_dict['Classification']
    return class_dict


def get_att_data_bytes(class_dict):
    data_stream = io.BytesIO()

    s3 = boto3.client('s3')
    s3.download_fileobj(class_dict['s3_bucket_name_src'], class_dict['s3_object_key_src'], data_stream)

    data_stream.seek(0)
    data_bytes = data_stream.getvalue()

    return data_bytes


def build_ses_msg(class_dict, labels_alert_found):
    # Create a multipart/mixed parent container.
    msg = MIMEMultipart('mixed')
    # Add subject, from and to lines.
    msg['Subject'] = SUBJECT
    msg['From'] = SENDER
    msg['To'] = ','.join(RECIPIENT_LIST)

    # Create a multipart/alternative child container.
    msg_body = MIMEMultipart('alternative')

    # replace template strings with the corresponding data
    labels_alert_found_str = ",".join(labels_alert_found)
    event_time_str = class_dict['eventTime'].replace('T', ' ').replace('Z', ' ')
    body_text = BODY_TEXT_TEMPLATE\
        .replace('__labels_alert_found__', labels_alert_found_str)\
        .replace('__eventTime__', event_time_str)
    body_html = BODY_HTML_TEMPLATE\
        .replace('__labels_alert_found__', labels_alert_found_str)\
        .replace('__eventTime__', event_time_str)

    # Encode the text and HTML content and set the character encoding. This step is
    # necessary if you're sending a message with characters outside the ASCII range.
    textpart = MIMEText(body_text.encode(CHARSET), 'plain', CHARSET)
    htmlpart = MIMEText(body_html.encode(CHARSET), 'html', CHARSET)

    # Add the text and HTML parts to the child container.
    msg_body.attach(textpart)
    msg_body.attach(htmlpart)

    # Define the attachment part and encode it using MIMEApplication.
    data_bytes = get_att_data_bytes(class_dict)
    att = MIMEApplication(data_bytes)

    # Add a header to tell the email client to treat this part as an attachment,
    # and to give the attachment a name.
    att.add_header('Content-Disposition', 'attachment', filename=os.path.basename(class_dict['s3_object_key_src']))

    # Attach the multipart/alternative child container to the multipart/mixed
    # parent container.
    msg.attach(msg_body)

    # Add the attachment to the parent container.
    msg.attach(att)

    return msg


def send_ses_msg(msg):
    # Create a new SES client and specify a region.
    ses = boto3.client('ses', region_name=AWS_SES_REGION)

    try:
        # Provide the contents of the email.
        response = ses.send_raw_email(
            Source=SENDER,
            Destinations=RECIPIENT_LIST,
            RawMessage={
                'Data': msg.as_string(),
            },
            # ConfigurationSetName=CONFIGURATION_SET
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        logger.info(e.response['Error']['Message'])
        response = False
    else:
        logger.info(f"Email sent! Message ID: {response['MessageId']}"),
        logger.info(f"response: {response}")

    return response
