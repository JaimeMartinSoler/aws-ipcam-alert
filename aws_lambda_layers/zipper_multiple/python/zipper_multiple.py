import boto3
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta as rd
from io import BytesIO
import os
import re
import zipfile

import logging
logger = logging.getLogger()


class ZipperMultiple:

    TAG_YEAR = '__ZIPPER-MULTIPLE_YEAR__'
    TAG_MONTH = '__ZIPPER-MULTIPLE_MONTH__'
    TAG_DAY = '__ZIPPER-MULTIPLE_DAY__'
    TAG_HOUR = '__ZIPPER-MULTIPLE_HOUR__'
    TAG_MINUTE = '__ZIPPER-MULTIPLE_MINUTE__'
    TAG_SECOND = '__ZIPPER-MULTIPLE_SECOND__'

    def __init__(self, bucket_name_with_tags, prefix_with_tags, filename_regex_with_tags, file_zip_with_tags):
        # with tags
        self.bucket_name_with_tags = bucket_name_with_tags
        self.prefix_with_tags = prefix_with_tags
        self.filename_regex_with_tags = filename_regex_with_tags
        self.file_zip_with_tags = file_zip_with_tags
        # without tags
        self.bucket_name = bucket_name_with_tags
        self.prefix = prefix_with_tags
        self.filename_regex = filename_regex_with_tags
        self.file_zip = file_zip_with_tags
        # tags_replaced
        self.tags_replaced = False

    def replace_tags(self, dt_tags):
        # restore tags
        self.tags_replaced = False
        self.bucket_name = self.bucket_name_with_tags
        self.prefix = self.prefix_with_tags
        self.filename_regex = self.filename_regex_with_tags
        self.file_zip = self.file_zip_with_tags
        # replace tags
        self._replace_tag(dt_tags, ZipperMultiple.TAG_YEAR, "%Y")
        self._replace_tag(dt_tags, ZipperMultiple.TAG_MONTH, "%m")
        self._replace_tag(dt_tags, ZipperMultiple.TAG_DAY, "%d")
        self._replace_tag(dt_tags, ZipperMultiple.TAG_HOUR, "%H")
        self._replace_tag(dt_tags, ZipperMultiple.TAG_MINUTE, "%M")
        self._replace_tag(dt_tags, ZipperMultiple.TAG_SECOND, "%S")
        self.tags_replaced = True
        logger.info(f"ZipperMultiple tags replaced for date '{dt_tags}' (self.tags_replaced={self.tags_replaced})")

    def _replace_tag(self, dt_tags, tag, dt_format):
        tag_replace = dt_tags.strftime(dt_format)
        self.bucket_name = self.bucket_name.replace(tag, tag_replace)
        self.prefix = self.prefix.replace(tag, tag_replace)
        self.filename_regex = self.filename_regex.replace(tag, tag_replace)
        self.file_zip = self.file_zip.replace(tag, tag_replace)

    def zip_files(self, delete_files=False):

        logger.info("ZipperMultiple.zip_files, starting...")
        logger.info(f"bucket_name   : '{self.bucket_name}'")
        logger.info(f"prefix        : '{self.prefix}'")
        logger.info(f"filename_regex: '{self.filename_regex}'")
        logger.info(f"file_zip      : '{self.file_zip}'")
        logger.info(f"delete_files  : '{delete_files}'")

        if not self.tags_replaced:
            logger.warning(
                f"self.tags_replaced: '{self.tags_replaced}', you may call replace_tags before zipping files")

        s3 = boto3.resource('s3')
        bucket = s3.Bucket(self.bucket_name)
        files_collection = bucket.objects.filter(Prefix=self.prefix).all()

        # build zip

        file_key_match_list = []
        stream = BytesIO()
        filename_pattern = None if self.filename_regex is None else re.compile(self.filename_regex)
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as zip_archive:

            for file in files_collection:
                filename = os.path.basename(file.key)
                if filename_pattern is None or filename_pattern.match(filename):
                    file_key_match_list.append(file.key)
                    with zip_archive.open(filename, 'w') as f:
                        f.write(file.get()['Body'].read())

        stream.seek(0)

        logger.info(f"files to zip (#)   : {len(file_key_match_list)}")
        logger.info(f"files to zip (list): {', '.join([os.path.basename(fk) for fk in file_key_match_list])}")

        # upload zip
        if len(file_key_match_list) > 0:
            s3.Object(self.bucket_name, self.file_zip).upload_fileobj(stream)
            logger.info(f"uploaded file_zip '{self.file_zip}' to bucket '{self.bucket_name}'")
        else:
            logger.info("file_zip NOT uploaded")

        stream.close()

        # delete_files
        if len(file_key_match_list) > 0 and delete_files:
            for file in files_collection:
                if file.key in file_key_match_list:
                    file.delete()
            logger.warning("files deleted")
        else:
            logger.info("files NOT deleted")

        logger.info(f"ZipperMultiple.zip_files, done!")

    def zip_files_month_ago(self, month_ago=1, delete_files=False):

        dt_now = dt.now()
        dt_month_previous = dt_now - rd(months=month_ago)

        self.replace_tags(dt_month_previous)
        self.zip_files(delete_files)

    def zip_files_months_ago(self, months_ago, delete_files=False):
        for month_ago in months_ago:
            self.zip_files_month_ago(month_ago, delete_files)
