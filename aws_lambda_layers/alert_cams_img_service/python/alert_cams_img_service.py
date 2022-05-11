from datetime import datetime as dt

from alert_cams_img_dao import AlertCamsImgDAO


class AlertCamsImgService:

    def __init__(self):
        self.alert_dao = AlertCamsImgDAO()
    
    def get_period(self):
        return self.alert_dao.get_period()

    def get_last_date(self):
        return self.alert_dao.get_last_date()

    def update_last_date(self):
        return self.alert_dao.update_last_date()

    def validate_period(self, return_metadata=False):
        
        alert_period = self.alert_dao.get_period()
        alert_last_date = self.alert_dao.get_last_date()
        dt_now = dt.now()
        alert_second_since_last = int((dt_now - alert_last_date).total_seconds())
        
        if alert_second_since_last < alert_period:
            alert_validate = False
        else:
            alert_validate = True
        
        if return_metadata:
            return alert_validate, (alert_period, alert_last_date, alert_second_since_last)
        else:
            return alert_validate
            
