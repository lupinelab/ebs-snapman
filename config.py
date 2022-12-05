config = {
    # Tag of the EBS volume(s) you want to take the snapshots of
    'tag_name': 'MakeSnapshot',
    'tag_value': 'True',

    # day of the month to run monthly snapshots
    'month_start': 1,

    # day of the week to run weekly snapshots
    'week_start': 'Sun',

    # Number of snapshots to retain
    'keep_day': 7,
    'keep_week': 5,
    'keep_month': 5,

    # Path to the log for this script
    'log_file': 'ebs-snapman.log',
}
