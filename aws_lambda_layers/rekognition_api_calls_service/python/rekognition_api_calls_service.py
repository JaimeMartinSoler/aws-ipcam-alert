import boto3

from rekognition_api_calls_dao import RekognitionApiCallsDAO
from alert_cams_img_service import AlertCamsImgService

from config import SNS_TOPIC_ARN_DEFAULT

import logging
logger = logging.getLogger()


class RekognitionApiCallsService:
    """
    lambda layer dependencies:
        - alert_cams_img_service
    """
    
    def __init__(self, do_create_month_current_if_not_exists=True, sns_topic_arn=SNS_TOPIC_ARN_DEFAULT):
        self.rek_api_calls_dao = RekognitionApiCallsDAO(do_create_month_current_if_not_exists)
        self.alert_service = AlertCamsImgService()
        self.client_sns = boto3.client('sns') if sns_topic_arn is not None else None
        self.sns_topic_arn = sns_topic_arn if sns_topic_arn is not None else None
        
    def create_api_calls_month_current_if_not_exists(self):
        return self.rek_api_calls_dao.create_api_calls_month_current_if_not_exists()
        
    def get_api_calls_month_current(self):
        return self.rek_api_calls_dao.get_api_calls_month_current()
        
    def increment_api_calls_month_current(self, api_calls_month_current=None):
        return self.rek_api_calls_dao.increment_api_calls_month_current(api_calls_month_current)
    
    def get_api_calls_month_max_50(self):
        return self.rek_api_calls_dao.get_api_calls_month_max_50()
    
    def get_api_calls_month_max_100(self):
        return self.rek_api_calls_dao.get_api_calls_month_max_100()
        
    def get_api_calls_disable_until_alert_period(self):
        return self.rek_api_calls_dao.get_api_calls_disable_until_alert_period()

    def validate_and_alert(self, return_metadata=False):
        
        # return_metadata
        validate_cause = None
        api_calls_month_current = None
        api_calls_month_max_100 = None
        
        # validate according to api_calls_disable_until_alert_period
        api_calls_disable_until_alert_period = self.get_api_calls_disable_until_alert_period()
        logger.info(f"rekognition_api_calls_disable_until_alert_period: {api_calls_disable_until_alert_period}")
        if api_calls_disable_until_alert_period:
            alert_validate, (alert_period, alert_last_date, alert_second_since_last) =\
                self.alert_service.validate_period(return_metadata=True)
            if not alert_validate:
                validate = False
                validate_cause = f"NO more rekognition api calls BEFORE alert period ({alert_period} s)" \
                                 f", last alert was on '{alert_last_date}' ({alert_second_since_last} s ago)"
                logger.info(validate_cause)
            else:
                validate = True
                logger.info(f"checking api calls thresholds after alert period ({alert_period} s)"
                            f", last alert was on '{alert_last_date}' ({alert_second_since_last} s ago)")
        else:
            validate = True
       
        # validate according to api calls thresholds
        if validate:
            
            # get api_calls_month current and thresholds
            api_calls_month_current = self.get_api_calls_month_current()
            api_calls_month_max_50 = self.get_api_calls_month_max_50()
            api_calls_month_max_100 = self.get_api_calls_month_max_100()
            logger.info(f"api_calls_month_current: {api_calls_month_current}")
            logger.info(f"api_calls_month_max_50: {api_calls_month_max_50}")
            logger.info(f"api_calls_month_max_100: {api_calls_month_max_100}")
        
            alert_subject = "AWS Rekognition API calls Threshold {}%"
            alert_message = "The AWS Rekognition API calls Threshold {}% ({} calls) has been reached."
            
            if api_calls_month_current + 1 < api_calls_month_max_50:
                # do nothing, OK
                validate = True
                
            elif api_calls_month_current + 1 == api_calls_month_max_50:
                # alert threshold 50% reached
                logger.info(f"rekognition api calls threshold 50% reached just now"
                            f" ({api_calls_month_max_50})! alert!")
                validate = True
                if self.client_sns is not None and self.sns_topic_arn is not None:
                    self.client_sns.publish(
                        TopicArn=self.sns_topic_arn,
                        Message=alert_message.format(50, api_calls_month_max_50),
                        Subject=alert_subject.format(50))
                    
            elif api_calls_month_max_50 < api_calls_month_current + 1 < api_calls_month_max_100:
                # do nothing, OK
                logger.info(f"rekognition api calls threshold 50% exceeded ({api_calls_month_max_50})!")
                validate = True
                
            elif api_calls_month_current + 1 == api_calls_month_max_100:
                # alert threshold 100% reached
                logger.info(f"rekognition api calls threshold 100% reached just now"
                            f" ({api_calls_month_max_100})! alert!")
                validate = True
                if self.client_sns is not None and self.sns_topic_arn is not None:
                    self.client_sns.publish(
                        TopicArn=self.sns_topic_arn,
                        Message=f"{alert_message.format(100, api_calls_month_max_100)}"
                                f"\n\nNO MORE REKOGNITION API CALLS WILL BE ALLOWED DURING CURRENT BILLING PERIOD",
                        Subject=alert_subject.format(100))
                    
            elif api_calls_month_max_100 < api_calls_month_current + 1:
                # do NOT validate
                validate = False
                validate_cause = f"rekognition api calls threshold 100% exceeded ({api_calls_month_max_100})!" \
                                 f" NOT validating rekognition calls!"
                logger.info(validate_cause)
                
        if return_metadata:
            return validate, (validate_cause, api_calls_month_current, api_calls_month_max_100)
        else:
            return validate
