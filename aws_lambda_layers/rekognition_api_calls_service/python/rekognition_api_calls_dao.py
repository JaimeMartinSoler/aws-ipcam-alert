from datetime import datetime as dt
import boto3
from botocore.exceptions import ClientError

from config import TABLE_NAME, DATE_SUFFIX_FORMAT,\
    ID_CALLS_MONTH_PREFIX, ID_CALLS_MONTH_MAX_50, ID_CALLS_MONTH_MAX_100, ID_DISABLE_UNTIL_ALERT_PERIOD


class RekognitionApiCallsDAO:

    def __init__(self, do_create_month_current_if_not_exists=True):
        self.client = boto3.client('dynamodb')
        self.id_api_calls_month_current = RekognitionApiCallsDAO._build_id_api_calls_month_current()
        if do_create_month_current_if_not_exists:
            self.create_api_calls_month_current_if_not_exists()
    
    @staticmethod
    def _build_id_api_calls_month_current():
        _id = f"{ID_CALLS_MONTH_PREFIX}" \
              f"{dt.now().strftime(DATE_SUFFIX_FORMAT)}"
        return _id
    
    def create_api_calls_month_current_if_not_exists(self):
        _id = self.id_api_calls_month_current
        item = {'id': {'S': _id}, 'value': {'N': str(0)}}
        try:
            response = self.client.put_item(TableName=TABLE_NAME, Item=item,
                                            ConditionExpression='attribute_not_exists(id)')
        except ClientError as e:  
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                pass  # ok, expected (attribute already exists)
            else:
                raise e
            return e
        return response
    
    def get_api_calls_month_current(self):
        _id = self.id_api_calls_month_current
        response = self.client.get_item(TableName=TABLE_NAME, Key={'id': {'S': _id}})
        value = response['Item']['value']['N']
        api_calls_month_current = int(value)
        return api_calls_month_current
        
    def increment_api_calls_month_current(self, api_calls_month_current=None):
        if api_calls_month_current is None:
            api_calls_month_current = self.get_api_calls_month_current()
        _id = self.id_api_calls_month_current
        item = {'id': {'S': _id}, 'value': {'N': str(api_calls_month_current + 1)}}
        response = self.client.put_item(TableName=TABLE_NAME, Item=item)
        return response
    
    def get_api_calls_month_max_50(self):
        _id = ID_CALLS_MONTH_MAX_50
        response = self.client.get_item(TableName=TABLE_NAME, Key={'id': {'S': _id}})
        value = response['Item']['value']['N']
        api_calls_max_50 = int(value)
        return api_calls_max_50
    
    def get_api_calls_month_max_100(self):
        _id = ID_CALLS_MONTH_MAX_100
        response = self.client.get_item(TableName=TABLE_NAME, Key={'id': {'S': _id}})
        value = response['Item']['value']['N']
        api_calls_max_100 = int(value)
        return api_calls_max_100

    def get_api_calls_disable_until_alert_period(self):
        _id = ID_DISABLE_UNTIL_ALERT_PERIOD
        response = self.client.get_item(TableName=TABLE_NAME, Key={'id': {'S': _id}})
        value = response['Item']['value']['BOOL']
        api_calls_disable_until_alert_period = bool(value)
        return api_calls_disable_until_alert_period
