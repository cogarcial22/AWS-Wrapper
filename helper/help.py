import csv
from prettytable import PrettyTable
from awrapperlib import resource


def get_instance_type():
    """
    Print instance available types from AWS
    """
    file_name = resource.get_resource('Extra/Amazon EC2 Instance Comparison.csv')
    t = PrettyTable(['Name', 'Description', 'Memory', 'CPU'])
    with open(file_name, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                line_count += 1
            t.add_row([row['API Name'], row['Name'], row['Memory'], row['vCPUs']])
            line_count += 1
        print(t)


def get_regions():
    """
    Print available AWS regions
    """
    file_name = resource.get_resource('Extra/regions.csv')
    t = PrettyTable(['Name', 'Description'])
    with open(file_name, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                line_count += 1
            t.add_row([row['Name'], row['Description']])
            line_count += 1
        print(t)


def get_help():
    """
    Print help menu, TBD
    """
    print('help')
