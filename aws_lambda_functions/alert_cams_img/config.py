# configuration alert
LABELS_ALERT = ['Person']

# configuration ses
AWS_SES_REGION = "aws-region-1"
#CONFIGURATION_SET = "ConfigSet"

# configuration email
SENDER = "AWS Alerts <example-sender@email.es>"
RECIPIENT_LIST = ["example1@email.com", "example2@email.com"]
SUBJECT = "AWS Alert Cam Detected Person"
CHARSET = "utf-8"

# configuration email text
BODY_TEXT_TEMPLATE = "ALERT - Possible Intruder!!!" \
    "\r\n" \
    "\r\nThis ALERT has been triggered because some labels have been detected:" \
    "\r\n  - Labels Alert: __labels_found__" \
    "\r\n  - Time (UTC): __time__" \
    "\r\nPlease, see the attached file with the capture of the possible intrusion." \
    "\r\n" \
    "\r\nThis email has been generated automatically using AWS services by me"
BODY_HTML_TEMPLATE = """\
<html>
<head></head>
<body>
<h1><span style="color: #ff0000;">ALERT - Possible Intruder!!!</span></h1>
<p>This ALERT has been triggered because some labels have been detected:</p>
<ul>
<li>Labels Alert: <strong>__labels_alert_found__</strong></li>
<li>Time (UTC): <strong>__eventTime__</strong></li>
</ul>
<p>Please, see the <strong>attached file</strong> with the capture of the possible intrusion.</p>
<p>&nbsp;</p>
<p><em>This email has been generated automatically using <strong><span style="color: #ff9900;">AWS services</span></strong> by <strong><span style="color: #800080;">me</span></strong></em></p>
</body>
</html>
"""
