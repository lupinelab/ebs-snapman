#!/usr/bin/env python3

import boto3
import argparse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import sys
import logging
from config import config

# Set up logging to both file and stdout
logger = logging.getLogger()
logger.setLevel(logging.INFO)
fileHandler = logging.FileHandler(filename=config['log_file'])
fileHandler.setFormatter(logging.Formatter("[%(asctime)s]:%(levelname)s - %(message)s", datefmt="%d/%m/%Y %H:%M:%S"))
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logging.Formatter('[%(asctime)s] - %(message)s', datefmt="%d/%m/%Y %H:%M:%S"))
logger.addHandler(fileHandler)
logger.addHandler(consoleHandler)

# add arg parser options
parser = argparse.ArgumentParser(description='Create and manage retention of EBS snapshots')
parser.add_argument("-s", "--summary", action='store_true', help="append a summary for all periods to the end of the stdout")
args = parser.parse_args()

# Counters
total_creates = 0
total_deletes = 0
count_errors = 0
count_success = 0
count_total = 0

# Prints a summary of the status of expected snaps and lists any misc snaps
def summary(vol):
    vol_name = vol.id
    for tag in vol.tags:
        if tag['Key'] == 'Name':
            vol_name = tag['Value']
    print(f'\n{vol_name.upper()}')
    print(f'{vol.id}')
    print(f'{"=" * max([len(vol_name), len(vol.id)])}')
    today = datetime.today().date()
    periods = ['day', 'week', 'month']
    # the volume's snapshots
    managed_snaps = {}
    misc_snaps = {}
    for snap in vol.snapshots.all():
        if snap.description.startswith(tuple(periods)):
            for tag in snap.tags:
                if tag['Key'] == 'Name':
                    managed_snaps[tag['Value'].split('_')[-1]] = tag['Value']
        else:
            if snap.tags != None:
                for tag in snap.tags:
                    if tag['Key'] == 'Name':
                        misc_snaps[snap.id] = tag['Value']
            elif snap.description != "":
                misc_snaps[snap.id] = f'{snap.description}: {snap.id}'
            else:
                misc_snaps[snap.id] = snap.id
    print(f'Managed snapshots:')
    print(f'{"-" * 18}')
    for period in periods:
        want_snaps = []
        for i in range(config[f'keep_{period}']):
            if period == 'day':
                d = today - relativedelta(days=i)
                s = d.strftime('%d-%m-%Y') 
                want_snaps.append(s)
            elif period == 'week':
                latest_week_start = today - relativedelta(days=(int(today.strftime('%w'))))
                d = latest_week_start - relativedelta(weeks=i)
                s = d.strftime('%d-%m-%Y')
                want_snaps.append(s)
            elif period == 'month':
                day_num = today.strftime('%d')
                first_of_month = today - timedelta(days=int(day_num) - 1)
                d = first_of_month - relativedelta(months=i)
                s = d.strftime("%d-%m-%Y") 
                want_snaps.append(s)
        # check for the expected snaps
        for w_snap in want_snaps:
            if w_snap in managed_snaps.keys():
                print(f'{w_snap}-{period}: {managed_snaps[w_snap]}')
                # if a snap is a valid snap for another period do not 'pop' it
                if period == 'day' and not datetime.strptime(w_snap, '%d-%m-%Y').strftime('%a') == config['week_start']:
                    managed_snaps.pop(w_snap)
                if period == 'week' and not datetime.strptime(w_snap, '%d-%m-%Y').strftime('%a') == config['month_start']:
                    managed_snaps.pop(w_snap)
                if period == 'month':
                    managed_snaps.pop(w_snap)
            else:
                print(f'{w_snap}-{period}: None')
    # Print remainder of managed_snaps
    print(f'\nOther snapshots:')
    print(f'{"-" * 16}')
    if len(managed_snaps) != 0:
        for snap in managed_snaps:
            print(managed_snaps[snap])
    # Print misc_snaps
    if len(misc_snaps) != 0:
        for snap in misc_snaps:
            print(misc_snaps[snap])

# Build a list of tags to give to our snapshots based on the volume's tags, this will be all tags on the volume except:
#   - 'Name' tags (these will be modified and added to the snapshot) 
#   - 'aws:' tags (these are internal AWS reserved tags)
def get_new_snap_tags(vol):
    resource_tags = []
    if vol:
        tags = vol.tags
        for tag in tags:
            if tag['Key'] == "Name":
                prefix = date_suffix if period != 'week' else f'Week-{date_suffix}'
                name_tag = {'Key': 'Name', 'Value': f'{prefix}_{tag["Value"]}_{datetime.today().strftime("%d-%m-%Y")}'}
                resource_tags.append(name_tag)
            elif not tag['Key'].startswith('aws:'):
                resource_tags.append(tag)
    return resource_tags

# Check which snapshot period to run for and set the date_suffix to use in tags and descriptions
if datetime.today().day == config['month_start']:
    period = 'month'
    date_suffix = datetime.today().strftime('%b')
elif datetime.today().strftime('%a') == config['week_start']:
    period = 'week'
    date_suffix = datetime.today().strftime("%U")
else:
    period = 'day'
    date_suffix = datetime.today().strftime('%a')

logger.info(f'Started taking \'{period}\' snapshots')

# If no credentials are specified boto3 will look for credentials in the default locations
# It is up to the user of this script to configure the connection ("conn") for themselves if they wish to override this behaviour
# For details see: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
logger.info('Connecting to AWS')
try:
    conn = boto3.resource('ec2')
except Exception as e:
    logger.error(f'Could not connect to AWS:{e}')
    quit()

# Find volumes to snapshot
logger.info(f'Finding volumes that match the requested tag ({config["tag_name"].replace("tag:", "")}: {config["tag_value"]})')
vols = conn.volumes.filter(Filters=[{'Name': f'tag:{config["tag_name"]}', 'Values': [config['tag_value']]}])

# For each volume: 
#   - make a new snapshot for the period
#   - try to delete the snapshot for the period which falls 1 iteration outside of the retention window 
if not args.summary:
    for vol in vols:
        try:
            count_total += 1
            # make a new snapshot
            vol_name = vol.id
            for tag in vol.tags:
                if tag['Key'] == 'Name':
                    vol_name = tag['Value']
            logger.info(f'{vol_name.upper()}: {vol.id}')
            new_snap_tags = get_new_snap_tags(vol)
            new_snap_desc = f'{period}_snapshot {vol.id}_{period}_{date_suffix} by snapshot script at {datetime.today().strftime("%d-%m-%Y %H:%M:%S")}'
            try:
                # # Needs testing!
                # new_snap = vol.create_snapshot(Description=new_snap_desc, TagSpecifications=[{'Tags': new_snap_tags}])
                logger.info(f'Created \'{period}\' snapshot with description: {new_snap_desc} and tags: {({tag["Key"]: tag["Value"] for tag in new_snap_tags})}')
                total_creates += 1
            except Exception as e:
                logger.error(e)
                count_errors += 1
                continue
            # calculate which snapshot should be deleted
            today = datetime.today().date()
            if period == 'day':
                d = today - relativedelta(days=(config['keep_day']))
                s = d.strftime("%d-%m-%Y") 
                delete_target = s
            elif period == 'week':
                d = today - relativedelta(weeks=(config['keep_week']))
                s = d.strftime("%d-%m-%Y")
                delete_target = s
            elif period == 'month':
                day_num = today.strftime("%d")
                first_of_month = today - timedelta(days=int(day_num) - 1)
                d = first_of_month - relativedelta(months=(config['keep_month']))
                s = d.strftime("%d-%m-%Y") 
                delete_target = s
            deleted = False
            # do not try to delete snapshots which cover another period, while without this check the there is
            # no risk of deleting a snapshot that is still required, without it a warning message would be produced
            # where no matching snapshot it found.
            if (period == 'day'\
                and (\
                    (datetime.strptime(delete_target, '%d-%m-%Y') - relativedelta(days=1)).strftime('%a') != config['week_start']\
                    or delete_target.split('-')[0] != config['month_start'])\
                )\
            or (period == 'week'\
                and delete_target.split('-')[0] != config['month_start']\
                )\
            or period == 'month':
                # try to delete the superseeded snapshot for the period if it exists   
                for snap in vol.snapshots.all():
                    if snap.description.startswith(period):
                        if delete_target in snap.description:
                            try:
                                deleted_snap_tags = snap.tags
                                # snap.delete()
                                logger.info(f'Deleted \'{period}\' snapshot with description: {snap.description} and tags: {({tag["Key"]: tag["Value"] for tag in deleted_snap_tags})}')
                                total_deletes += 1
                                deleted = True
                                break
                            except Exception as e:
                                logger.error(f'Could not delete \'{period}\' snapshot {snap}: {e}')
                                count_errors += 1
                                break
                if not deleted:
                    # log a warning if the expected snapshot does not exist
                    logger.warning(f'Could not find \'{period}\' snapshot {delete_target} for {vol_name} or the snapshot could not be deleted')
                count_success += 1
        except Exception as e:
            logger.error(e)
            count_errors += 1

    logger.info(f'Finished making snapshots at {datetime.today().strftime("%d-%m-%Y %H:%M:%S")}, {count_success}\\{count_total} volumes snapshotted.')

    logger.info("Total snapshots created: " + str(total_creates))
    logger.info("Total snapshots deleted: " + str(total_deletes))
    logger.info("Total errors: " + str(count_errors))

if args.summary:
    for vol in vols:
        summary(vol)
    logger.info('Printed Summary')