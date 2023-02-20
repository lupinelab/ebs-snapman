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

Example summary:
```
SERVER01_ROOT_VOL
vol-1b7dab28
====================
Managed snapshots:
------------------
03-02-2023-day: Fri_server01_root_vol_03-02-2023
02-02-2023-day: Thu_server01_root_vol_02-02-2023
01-02-2023-day: Feb_server01_root_vol_01-02-2023
31-01-2023-day: Tue_server01_root_vol_31-01-2023
30-01-2023-day: Mon_server01_root_vol_30-01-2023
29-01-2023-day: Week-05_server01_root_vol_29-01-2023
28-01-2023-day: Sat_server01_root_vol_28-01-2023
29-01-2023-week: Week-05_server01_root_vol_29-01-2023
22-01-2023-week: Week-04_server01_root_vol_22-01-2023
15-01-2023-week: Week-03_server01_root_vol_15-01-2023
08-01-2023-week: Week-02_server01_root_vol_08-01-2023
01-01-2023-week: Jan_server01_root_vol_01-01-2023
01-02-2023-month: Feb_server01_root_vol_01-02-2023
01-01-2023-month: Jan_server01_root_vol_01-01-2023
01-12-2022-month: Dec_server01_root_vol_01-12-2022
01-11-2022-month: Nov_server01_root_vol_01-11-2022
01-10-2022-month: Oct_server01_root_vol_01-10-2022
```
