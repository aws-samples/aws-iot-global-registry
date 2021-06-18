# Replicating AWS IoT Registry from multiple regions to a DynamoDB global table

AWS customers can use [AWS IoT Device Management](https://aws.amazon.com/iot-device-management/) to securely register, organize, monitor, and remotely manage IoT devices at scale. You can use AWS IoT console, AWS IoT API, or the AWS CLI to interact with the registry in an individual AWS region. This sample provides an example on how to create an aggregated read replica of IoT device data based on AWS IoT registy data from multiple regions. An aggregated replica data will be stored in DynamoDB global tables. For example, by using this sample you could perform a DynamoDB scan operation to list all IoT Things from AWS regions us-east-1 and eu-west-1. You also can easily add further AWS regions. 

Please note that the following constraints: 
- Replicas in DynamoDB implemented in this sample are read-only, i.e. the modification in the DynamoDB table will not result in any change of AWS IoT registry.
- Replicas will only contain information on IoT Things. IoT Thing Groups and IoT Types are not covered in this sample.

This sample can be also used to ceate a read replica of IoT registry from an single region to a DynamoDB table. This allows highly scalable read operations on IoT registry data. It enables customers to offload the access to AWS IoT registry APIs and to reduce consumption of [AWS IoT Device Management quotas](https://docs.aws.amazon.com/general/latest/gr/iot_device_management.html).

## Quick start

Below you will find instructions  to create a read replica for IoT registry items in regions us-east-1 and eu-west 1. The read repilca will be implemented with [DynamoDB global table](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html). The following explanations assume that you are familiar with the concept of DynamoDB global tables.  Please note that for deployment in the AWS region us-east-1 the parameter CreateGlobalTable is set to **true**. By setting the parameter CreateGlobalTable to true, you will trigger a creation of a [DynamoDB global table](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html) in that specific region. If you set CreateGlobalTable to true, you shall also specifiy a value of SecondaryRegionName. The parameter SecondaryRegionName defines the AWS region to create a replica of a global table.


## Step 1 : Enable IoT Registry events
First, please enable IoT registry events for event type "THING". After performing that configuration step, AWS IoT Core will publish a mesage to the topics `$aws/events/thing/thingName/created`, `$aws/events/thing/thingName/updated` , `$aws/events/thing/thingName/deleted` each time an IoT Thing is created/updated/deleted. Please refer to the [documentation](https://docs.aws.amazon.com/iot/latest/developerguide/registry-events.html) for details.

```shell
aws iot update-event-configurations --region us-east-1 --event-configurations "{\"THING\": {\"Enabled\": true}}"
aws iot update-event-configurations --region eu-west-1 --event-configurations "{\"THING\": {\"Enabled\": true}}"
```
## Step 2: Build the template
```shell
sam build
```

## Step 3: Deploy stack in region us-east-1. 
By setting CreateGlobalTable parameter to true, us-east-1 will be a region where the [DynamoDB global table](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)  "GlobalIoTDeviceRegistyTable" will be created. The region eu-west-1 will be specified as a replica for the global table.

```shell
sam deploy  --region us-east-1  \
--config-env us-east-1-config \
--stack-name globaliotregistryreplica \
--parameter-overrides CreateGlobalTable=true SecondaryRegionName=eu-west-1 \
--guided
```

## Step 4: Deploy stack in region eu-west-1. 
By setting CreateGlobalTable to false, we indicate that no DynamoDB table needs to be created in eu-west-1, because it way already created as a replica of us-east-1 in Step 3.

```shell
sam deploy  --region eu-west-1 \
--config-env eu-west-1-config \
--stack-name globaliotregistryreplica \
--parameter-overrides CreateGlobalTable=false \
--guided
```

The steps 5 and 6 are for testing this sample.

## Step 5: Create sample IoT things
In this step we will create two IoT Things in regions us-east-1 and eu-west-1 respectively.

```shell
aws iot create-thing \
    --region us-east-1 \
    --thing-name "MyLightBulb5" \
    --attribute-payload '{"attributes": {"wattage":"75", "model":"123"}}'

aws iot create-thing \
    --region eu-west-1 \
    --thing-name "MyLightBulb6" \
    --attribute-payload '{"attributes": {"wattage":"85", "model":"321"}}'
```

## Step 6: View global IoT Registy

```shell
aws dynamodb scan \
    --region us-east-1 \
    --projection-expression "ThingName","AWSRegion" \
    --table-name GlobalIoTDeviceRegistyTable \
    --filter-expression 'begins_with(ThingName,:beginsWith)' \
    --expression-attribute-values  '{ 
                      ":beginsWith":{"S":"MyLightBulb"} 
      }'

```

The expected output is :

```json
{
    "Items": [
        {
            "AWSRegion": {
                "S": "us-east-1"
            },
            "ThingName": {
                "S": "MyLightBulb5"
            }
        },
        {
            "AWSRegion": {
                "S": "eu-west-1"
            },
            "ThingName": {
                "S": "MyLightBulb6"
            }
        }
    ],
    "Count": 2,
    "ScannedCount": 2,
    "ConsumedCapacity": null
}
```

### Resources that this sample will create in your AWS account

Below you will find an overview of resources created:

1. Amazon DynamoDB global table "GlobalIoTDeviceRegistyTable". This table will contain a replica of IoT registry entries from all participating regions. You can view a sample entry in this table [below](#sample_entry).
2. AWS IoT Rule <Stack name>ProcessIoTRegisryEventsRule and related IAM resources. This IoT Rule will subscribe to [IoT registry events](https://docs.aws.amazon.com/iot/latest/developerguide/registry-events.html). For each IoT registry event, a Lambda function **WriteRegistryPresenceEventToDDBFunction** will be invoked with event data as an input payload.
3. AWS Lambda function <Stack name>_WriteRegistryPresenceEventToDDBFunction. This Lambda function will evaluate the Iot registry event payload and create/update the appropriate record in the DynamoDB table.


### Sample entry
The JSON document below represents a sample entry in the global table "GlobalIoTDeviceRegistyTable".
```json
{
 "ThingName": "TestThing1",
 "Region": "us-east-1",
 "accountId": "1234567890",
 "timestamp_create": 1622129627073,
 "lifecycle_stage": "ACTIVE",
 "attributes": {
  "serial": "123"
 }
}
```
