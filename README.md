# AWS IP-CAM Human Intrusion Alert

## Introduction

This project describes an affordable and reliable system for almost real-time human intrusion detection and automatic
cloud storage of the video

## Requirements

- Almost any IP-cam (from 30€/ip-cam).
- Synology NAS or any middleware able to capture video and an image stream from IP-cams and upload it to AWS S3 buckets.
  Note that there is a Synology one-time pay licence cost (around 60€) for each IP-cam, but first 2 IP-cams are free.
- An AWS account.
- Estimated monthly budget regarding AWS costs is 0.00€-0.05€ and up to 0.40€ per month (0.10€ per week) IP-cam
  if you have a pet, triggering the detection movement and the human intrusion detection pipeline.

## Pipeline Diagram

<img src="img/aws-ipcam-alert.jpg">

### Pipeline Diagram Description

<ul type="none">
    <li><b>1.</b> <b>IP-cams video streams</b>.</li>
    <li><b>2.</b> <b>Synology Surveillance</b> triggers some actions according to its configuration:
    <ul type="none">
        <li><b>S.</b> <b>SNAPSHOTS</b>: Motion Detection and Snapshots Action Rule ON:</li>
        <ul type="none">
            <li><b>S.1.</b> <b>Synology Surveillance</b> captures an IP-cam stream of snapshots (images) and stores them in /surveillance/@Snapshots.</li>
            <li><b>S.2.</b> <b>Synology CloudSync</b> uploads the images to S3 input_bucket (direction: upload, deletes: ignore).</li>
            <li><b>S.3.</b> <b>S3 input_bucket</b> ObjectCreated action triggers Lambda function class_cam_img.</li>
            <li><b>S.4.</b> <b>Lambda function class_cam_img</b>.</li>
            <ul type="none">
                <li><b>S.4.1.</b> class_cam_img checks some <b>DynamoDB PARAMS table</b> items about thresholds configuration and state.</li>
                <li>IF thresholds and state are OK:</li>
                <ul type="none">
                  <li><b>S.4.OK.1.</b> class_cam_img calls the <b>API Rekognition to detect_labels</b> (Person, Cat, ...) on S3 input_bucket created image.</li>
                  <li><b>S.4.OK.2.</b> class_cam_img stores the API Rekognition metadata into S3 processed_bucket.</li>
                  <li><b>S.4.OK.3.</b> <b>S3 processed_bucket</b> ObjectCreated action triggers Lambda function alert_cams_img.</li>
                  <li><b>S.4.OK.4.</b> <b>Lambda function alert_cams_img</b>.</li>
                  <ul type="none">
                      <li><b>S.4.OK.4.1</b> alert_cams_img checks some <b>DynamoDB PARAMS table</b> items about thresholds configuration and state.</li>
                      <li>IF thresholds and state are OK:</li>
                      <ul type="none">
                        <li><b>S.4.OK.4.OK.1</b> alert_cams_img sends a <b>SES email message</b> informing of the intrusion, with he S3 input_bucket image attached to users from <b>Alert group</b>.</li>
                  </ul>
                </ul>
            </ul>
                <li>IF thresholds are NOT OK:</li>
                <ul type="none">
                  <li><b>S.4.KO.1.</b> class_cam_img sends a message to <b>SNS aws_rek_usage</b> topic if usage thresholds have been reached.</li>
                  <li><b>S.4.KO.2.</b> SNS aws_rek_usage topic notifies to users from <b>Admins group</b>.</li>
                </ul>
            </ul>
        </ul>
        <li><b>V.</b> <b>VIDEO</b>: Motion Detection and Home Mode OFF:</li>
        <ul type="none">
            <li><b>V.1.</b> <b>Synology Surveillance</b> captures IP-cam video and stores them in /surveillance/video</li>
            <li><b>V.2.</b> <b>Synology CloudSync</b> uploads the video to S3 backup_bucket (direction: upload, deletes: ignore).</li>
        </ul>
    </ul>
</ul>

## DynamoDB table PARAMS

The following DynamoDB table PARAMS items serve the Lambda Functions to execute the business logic describe in the column description.

Note that handling the monthly Rekognition API calls with Lambda functions is not a perfect solution,
other services could call the Rekognition API without the Lambda functions noticing it and, therefore,
without the DynamoDB PARAMS being updated (`rekognition_api_calls_<YEAR>_<MONTH>`, `alert_cams_img_last`).
How ever, I couldn't find a better solution to approach exactly this problem. Any word of advice would be appreciated.

| id                                       | value               | description                                                                                                                                                                                   |
|------------------------------------------|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| class_cam_img_disable_until_alert_period | true                | Enable warm-up period for alerts to be triggered<br/>- true: trigger alarms only if now() - alert_cams_img_last > alert_cams_img_period<br/>- false: no warm-up period, trigger alerts always |
| alert_cams_img_period                    | 3600                | Warm-up period to wait until next alert, to avoid flooding with consecutive alerts.                                                                                                           |
| alert_cams_img_last                      | 2022-05-24 21:03:12 | Date of last alert triggered, for the warm-up alert logic.                                                                                                                                    |
| rekognition_api_calls_month_max_100      | 5000                | Threshold of 100% of Rekognition API calls per month. Once reached, SNS is sent and no more calls are done.                                                                                   |
| rekognition_api_calls_month_max_50       | 2500                | Threshold of 50% of Rekognition API calls per month. Once reached, SNS is sent.                                                                                                               |
| rekognition_api_calls_2022_05            | 1271                | Rekognition API calls for the year-month 2022-05                                                                                                                                              |
| rekognition_api_calls_2022_04            | 56                  | Rekognition API calls for the year-month 2022-04                                                                                                                                              |

## Lambda Functions Summary

The following functions are the Lambda Functions `class_cam_img`, `alert_cams_img` and some other relevant functions.
Note that they are represented as pseudocode, so they may lack some deeper detail that can be found in the code itself.

### class_cam_img

```python
  class_cam_img:
  """
  From an input image in input_bucket, detects its labels (Rekognition) and stores the results in processed_bucket.
  Its also handles warm-up and threshold parameters (DynamoDB PARAMS) and SNS notifications.
  """

    # validate alert warm-up period and thresholds (DynamoDB PARAMS) and send notifications (SNS)
    if RekognitionApiCallsService.validate_and_alert():
      
      # call Rekognition API to detect labels present in the obj image (Person, Cat, ...)
      json_labels = client_rekognition.detect_labels(bucket, obj)
      
      # update (increment +1) DynamoDB PARAMS.rekognition_api_calls_<YEAR>_<MONTH>
      RekognitionApiCallsService.increment_api_calls_month_current()
        
      # save json with labels data in processed_bucket
      save_json_dict(json_labels)
```

### alert_cams_img

```python
  alert_cams_img:
  """
  From an input json in processed_bucket, checks the detected labels and sends a SES email with an image attached.
  Its also handles warm-up parameters (DynamoDB PARAMS).
  """

    # validate alert warm-up period (DynamoDB PARAMS)
    if AlertCamsImgService.validate_period():
      
      # check the detected labels worth alerting
      if labels_detected in LABELS_ALERT:
        
        # build and send SES message (email with image attached)
        msg = build_ses_msg()
        send_ses_msg(msg)
  
        # update DynamoDB PARAMS.alert_cams_img_last
        AlertCamsImgService.update_last_date()
```

### RekognitionApiCallsService, AlertCamsImgService

It is worth mentioning the business logic of the main validation functions:
  - `RekognitionApiCallsService.validate_and_alert()`
  - `AlertCamsImgService.validate_period()`

```python
  RekognitionApiCallsService.validate_and_alert():
    # validate alert warm-up period and thresholds (DynamoDB PARAMS) and send notifications (SNS)

    # validate warm-up period
    AlertCamsImgService.validate_period():
      # class_cam_img_disable_until_alert_period param handles the activation of the following logic:
      # if the time passed since the last alert is greater than a given warm-up period (and only then) validate alert,
      # this is done in order to not flood with many consecutive alerts.
      if PARAMS.class_cam_img_disable_until_alert_period:
          if datetime.now() - PARAMS.alert_cams_img_last > PARAMS.alert_cams_img_period:
              validate = True  # warm-up period has been passed already
          else:
              validate = False  # still waiting warm-up period to avoid flooding consecutive alerts
      else:    
          validate = True  # with this configuration we don't care about warm-up period, so it is validated

    # validate thresholds and SNS
    # rekognition_api_calls_month_max thresholds set limits for Rekognition API calls and inform (SNS) when the limits
    # are reached (50% and 100%), this is done ir order to avoid excessive costs of Rekognition API calls.
    if PARAMS.rekognition_api_calls_<YEAR>_<MONTH> < PARAMS.rekognition_api_calls_month_max_50:
        validate = True  # do nothing, OK
    elif PARAMS.rekognition_api_calls_<YEAR>_<MONTH> == PARAMS.rekognition_api_calls_month_max_50:
        validate = True  # validate but inform of 50% threshold reached
        sns.publish('aws_rek_usage', 'rekognition api calls threshold 50% reached just now')
    elif PARAMS.rekognition_api_calls_<YEAR>_<MONTH> < PARAMS.rekognition_api_calls_month_max_100:
        validate = True # do nothing, OK
    elif PARAMS.rekognition_api_calls_<YEAR>_<MONTH> >= PARAMS.rekognition_api_calls_month_max_100:
        validate = False  # do NOT validate but inform of 100% threshold reached
        sns.publish('aws_rek_usage', 'rekognition api calls threshold 100% reached just now')

    # note that, internally, all PARAMS required are being updated with every call. This concers to:
    #   PARAMS.rekognition_api_calls_<YEAR>_<MONTH>  (created and set to 0 for current year-month if it does not exist)
    #   PARAMS.alert_cams_img_last
        
    return validate
```
