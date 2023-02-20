# ebs-snapman

Snapshot management and rotation for AWS EBS volumes.

## Installation
Install the requirements:
```
pip install -r requirements.txt
```

## Usage
Adjust config.py as required. Note that snapshots will only be performed on volumes which have the specified tag, by default this is "MakeSnapshot: True".

Review the order in which credentials will be selected and provide them accordingly:
https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html

Create a daily cron job to run snapshots. For example, at 3am each day:
```
0 3 * * * root python3 /root/scripts/ebs-snapman/ebs-snapman.py
```
And an optional cron job for the summary. For example, a weekly summary:
```
15 3 * * 1 root python3 /root/scripts/ebs-snapman/ebs-snapman.py --summmary
```
Be sure to have your cron environemt configured to send emails.
