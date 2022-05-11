from datetime import datetime as dt
import boto3

from config import TABLE_NAME, DATE_FORMAT, ID_ALERTS_CAMS_IMG_PERIOD, ID_ALERTS_CAMS_IMG_LAST


class AlertCamsImgDAO:

    def __init__(self):
        self.client = boto3.client('dynamodb')
    
    def get_period(self):
        _id = ID_ALERTS_CAMS_IMG_PERIOD
        response = self.client.get_item(TableName=TABLE_NAME, Key={'id': {'S': _id}})
        value = response['Item']['value']['N']
        period = int(value)
        return period

    def get_last_date(self):
        _id = ID_ALERTS_CAMS_IMG_LAST
        response = self.client.get_item(TableName=TABLE_NAME, Key={'id': {'S': _id}})
        value = response['Item']['value']['S']
        alarm_last_date = dt.strptime(value, DATE_FORMAT)
        return alarm_last_date

    def update_last_date(self):
        _id = ID_ALERTS_CAMS_IMG_LAST
        value = dt.now().strftime(DATE_FORMAT)
        item = {'id': {'S': _id}, 'value': {'S': value}}
        response = self.client.put_item(TableName=TABLE_NAME, Item=item)
        return response
