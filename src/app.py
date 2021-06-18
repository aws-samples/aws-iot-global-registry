# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import json
import boto3
from botocore.exceptions import ClientError
import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Set config variables
DDB_TABLE_NAME = os.environ.get("DDB_TABLE_NAME")
RUNTIME_REGION = os.environ['AWS_REGION']

# This is required for local testing using 'sam local invoke'. Please update the value manuall to the
# name of the global table previously created
if DDB_TABLE_NAME == "MyGlobalIoTDeviceRegistyTable":
    DDB_TABLE_NAME = "GlobalIoTDeviceRegistyTableName"


logging.info(f"Region is {RUNTIME_REGION}")
dynamodb = boto3.resource('dynamodb',region_name=RUNTIME_REGION)
ddb_table = dynamodb.Table(DDB_TABLE_NAME)

def lambda_handler(event, context):
    logging.info("Received event: {}".format(event))
    logging.info(f"Using DynamoDB table {DDB_TABLE_NAME}")

    if event.get("eventType") == "THING_EVENT":
        
        # New thing created
        if event.get("operation") == "CREATED":
            
            logging.info("Processing THING_EVENT/CREATED")
            response = ddb_table.put_item(Item={
                    'AWSRegion': RUNTIME_REGION,
                    'ThingName':  event.get("thingName"),
                    'state': 'ACTIVE',
                    'accountId': event.get("accountId"),
                    'attributes': event.get("attributes"),
                    'eventoriginal_THING_EVENT_CREATED': event,
                    'timestamp_create': event.get("timestamp")

                }
            )    
        # Thing updated
        if event.get("operation") == "UPDATED":
            logging.info("Processing THING_EVENT/UPDATED")
            

            try:
                response = ddb_table.get_item(Key={'AWSRegion': RUNTIME_REGION,
                    'ThingName':  event.get("thingName")})
            except ClientError as e:
                logging.info(e.response['Error']['Message'])
                raise Exception(e)
            else:
                item = response.get('Item')
                logging.info(f"Found {item}")

            
            if (item == None):
                logging.info(f"Thing with name {event.get('thingName')} is being updated, by does not exist in global registry yet. Adding it." )
                item =  {
                    'AWSRegion': RUNTIME_REGION,
                    'ThingName':  event.get("thingName"),
                    'state': 'ACTIVE',
                    'accountId': event.get("accountId"),
                    'attributes': event.get("attributes"),
                    'eventoriginal_THING_EVENT_CREATED': event,
                    'timestamp_create': event.get("timestamp")
                }
            else:
                logging.info(f"Thing with name {event.get('thingName')} is being updated, and was found in global registry. Will update it." )
                item['state'] = "ACTIVE"
                item['attributes'] = event.get("attributes")
                item['eventoriginal_THING_EVENT_UPDATED'] = event
                item['timestamp_lastupdate'] =  event.get("timestamp")

            response = ddb_table.put_item(Item=item)    

        # Thing deleted
        if event.get("operation") == "DELETED":
            logging.info("Processing THING_EVENT/DELETED")

            try:
                response = ddb_table.get_item(Key={'AWSRegion': RUNTIME_REGION,
                    'ThingName':  event.get("thingName")})
            except ClientError as e:
                logging.info(e.response['Error']['Message'])
                raise Exception(e)
            else:
                item = response.get('Item')
                logging.info(f"Found {item}")

            
            if (item == None):
                logging.info(f"Thing with name {event.get('thingName')} is being deleted, by does not exist in global registry yet. Adding it in DELETED state." )
                item =  {
                    'AWSRegion': RUNTIME_REGION,
                    'ThingName':  event.get("thingName"),
                    'state': 'DELETED',
                    'accountId': event.get("accountId"),
                    'attributes': event.get("attributes"),
                    'eventoriginal_THING_EVENT_DELETED': event,
                    'timestamp_delete': event.get("timestamp")
                }
            else:
                logging.info(f"Thing with name {event.get('thingName')} is being deleted, and was found in global registry. Will deleted it." )
                item['state'] = "DELETED"
                item['eventoriginal_THING_EVENT_DELETED'] = event
                item['timestamp_delete'] =  event.get("timestamp")

            response = ddb_table.put_item(Item=item)    

    else:
        event_type = event.get('eventType')
        logging.info(f"Invalid event type {event_type}")
        raise Exception(f"Invalid event type {event_type}")
    
    
    return {"code":200}

