#!/usr/bin/env python3

import boto3
import time

s = boto3.Session()
ec2 = s.client('ec2')
cfn = s.client('cloudformation')
ssm = s.client('ssm')
s3 = s.client('s3')

class Stack:
    def __init__(self, stackData):
        self.arn = stackData['StackId']
        self.name = stackData['StackName']
        self.status = stackData['StackStatus']

    def __repr__(self):
        return '<Stack:{}>'.format(self.arn)

    # Query EC2 and ASG for ami information
    def getCurrentAmis(self):
        pass
    
    def isPatchable(self):
        for resource in self.getResources():
            if resource.patchable:
                return True
        return False
        
    def getResources(self):
        self._resources = []
        r = cfn.describe_stack_resources(StackName=self.arn)
        for resourceDescription in r['StackResources']:
            self._resources.append(Resource.getResource(resourceDescription))
        return self._resources

    @property
    def resources(self):
        try:
            return self._resources
        except AttributeError:
            return self.getResources()

class Resource:
    @staticmethod
    def getResource(resourceData):
        if resourceData['ResourceType'] == 'AWS::EC2::Instance':
            return Instance(resourceData)
        elif resourceData['ResourceType'] == 'AWS::Autoscaling::Autoscaling':
            return ASG(resourceData)
        else:
            return Resource(resourceData)

    def __init__(self, resourceData):
        self.type = resourceData['ResourceType']
        self.status = resourceData['ResourceStatus']
        self.resourceId = resourceData['PhysicalResourceId']
        self.patchable = False # Overridden in subclasses

class Instance(Resource):
    def __init__(self, resourceData):
        super(Instance, self).__init__(resourceData)
        self.patchable = True

    @property
    def description(self):
        try:
            return self.ndescription
            self._amiId = r['Reservations'][0]['Instances'][0]['ImageId']
        except AttributeError:
            r = ec2.describe_instances(InstanceIds=[self.resourceId])
            self._description = r['Reservations'][0]['Instances'][0]
        return self._description

    @property
    def amiId(self):
        try:
            return self._amiId
        except AttributeError:
            self._amiId = self.description['ImageId']
            return self._amiId

    def createPatchedAmi(self):
        patchingAmi = self.createPatchingAmi()
        patchingInstance = createInstance(patchingAmi, self.instanceType)
        patchInstance(patchingInstance)
        patchedAmiName = self.amiId, '_patched_' + str(time.time())
        patchedAmi = createImage(patchingInstance, patchedAmiName)
        destroyPatchingInstance(patchingInstance)
        return patchedAmi

    def createPatchingAmi(self):
        # The use of time.time here gives an epoch timestamp. Maybe not the 
        # correct decision, but it will at least give something unique.
        amiName = self.amiId + '_patching_' + str(time.time())
        return createImage(self.resourceId, amiName)

class ASG(Resource):
    # TODO support this
    def __init__(self, resourceData):
        super(ASG, self).__init__(resourceData)
        self.patchable = True

    def ami(self):
        pass

def createInstance(imageId, instanceType):
    r = ec2.run_instances(
        ImageId=imageId, 
        InstanceType=instanceType,
        #SubnetId=subnetId,
        MinCount=1, 
        MaxCount=1
    )
    return r['Instances'][0]['InstanceId']

def createImage(instanceId, name):
    r = ec2.create_image(InstanceId=instanceId, Name=name, NoReboot=True)
    return r['ImageId']

def patchInstance(instanceId):
    #TODO Windows support
    command = 'yum update -y'
    commandOutput = runCommand(instanceId, command)
    return commandOutput

def terminateInstance(instanceId):
    r = ec2.terminateInstances(InstanceIds=[instanceId])
    return r['TerminatingInstances'][0]['CurrentState']['Name']

def getStacks():
    stacks = []
    r = cfn.list_stacks()
    for stackSummary in r['StackSummaries']:
        stacks.append(Stack(stackSummary))
    return stacks

def runCommand(instanceId, command):
    # TODO support Windows
    # TODO don't hardcode all the bucket stuff
    # TODO error handling
    bucket = 'mudbungie-ssm-output'
    region = 'us-west-2'
    document = 'AWS-RunShellScript'
    folder = 'testing'
    invocation = ssm.send_command(
        InstanceIds=[instanceId], 
        DocumentName=document, 
        OutputS3Region=region,
        OutputS3BucketName=bucket,
        OutputS3KeyPrefix=folder,
        Parameters={'commands': command}
    )['Command']

    commandStatus = 'InProgress'
    tries = 0
    while commandStatus == 'InProgress' and tries < 5:
        tries += 1
        time.sleep(2**tries)
        command = ssm.get_command_invocation(
            CommandId = invocation['CommandId'],
            InstanceId = instanceId
        )
        commandStatus = command['Status']
    urlPrefix = 'https://s3-' + region + '.amazonaws.com/' + bucket + '/'
    key = command['StandardOutputUrl'][len(urlPrefix):]
    s3Obj = s3.get_object(Bucket=bucket, Key=key)
    output = s3Obj['Body'].read().decode()
    return output

def parseYumReport(commandOutput):
    outputLines = commandOutput.split('\n')
    for line in outputLines:
        print(line)

def reportAllAvailablePatches():
    for stack in getStacks():
        if stack.isPatchable():
            pass

def createPatchedAmisForStack(stack):
    for resource in resources:
        pass

def createPatchedAmisforAllStacks():
    for stack in getStacks():
        pass

def patchStack(stackId):
    pass


#TODO DELETE
def do_stuff():
    a = getStacks()
    b = a[0]
    c = b.resources[0]
    d = c.createPatchingAmi()
    return d

def lambda_handler(*args, **kwargs):
    stacks = getStacks()
    for stack in stacks:
        print(stack.isPatchable())

if __name__ == '__main__':
    lambda_handler()
    
