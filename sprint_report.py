#!/usr/bin/python


import argparse
import json
import config
import requests
import datetime
import csv
import sys


OPENBMC_REPO_ID = '42542702'
ZENHUB_API = 'https://api.zenhub.io/p1/repositories/%s/' % OPENBMC_REPO_ID
ZENHUB_API_ISSUES = ZENHUB_API + 'issues/'
ZENHUB_API_EPICS = ZENHUB_API + 'epics/'
GITHUB_AUTH = (config.GITHUB_USER, config.GITHUB_PASSWORD)
REPO_ID = '42542702'
GITHUB_API_ISSUES = 'https://api.github.com/repos/openbmc/openbmc/issues/'

option_csv = None
option_pipe = None


def do_report(args):
    issueNumber = str(args.e)
    issue_api_url = GITHUB_API_ISSUES + issueNumber

    github_data =  requests.get(issue_api_url, auth=GITHUB_AUTH).json()

    issue_zen_api_url = ZENHUB_API_ISSUES + issueNumber
    zenhub_data = requests.get(issue_zen_api_url, headers=config.zen_auth, verify=False).json()

    print("report:%s") % CTM
    print("----")
    print github_data['title']
    if zenhub_data['is_epic']:
        issue_zen_api_epic_url = ZENHUB_API_EPICS + issueNumber
        zen_epic =  requests.get(issue_zen_api_epic_url, headers=config.zen_auth, verify=False).json()

        pt_total = 0
        for story in zen_epic['issues']:
            issue_api_url = GITHUB_API_ISSUES + str(story['issue_number'])
            github_story_data =  requests.get(issue_api_url, auth=GITHUB_AUTH).json()
            
            estimate = story.get('estimate')
            estimate_value = ''
            if estimate is not None:
                estimate_value = estimate.get('value')
                pt_total += estimate_value
            issue_owner = ''
            if github_story_data['assignee'] is not None:
                issue_owner = (github_story_data['assignee']['login'])
                
            pipeline_name = ''
            if option_pipe:               
                pipeline_state = story.get('pipeline')
                if pipeline_state is not None:
                    pipeline_name = pipeline_state['name']
                if github_story_data['state'] == 'closed':
                    pipeline_name = 'Closed'

            print ("%s %s %s %s %s %s") % (story['issue_number'], github_story_data['title'].encode('utf-8'), issue_owner, github_story_data['state'], estimate_value, pipeline_name)
            if option_csv:
                GITHUB_LINK='=HYPERLINK("https://github.com/openbmc/openbmc/issues/%s", "%s")' % (story['issue_number'], story['issue_number'])
                csvout.writerow([GITHUB_LINK, github_story_data['title'].encode('utf-8'), issue_owner, github_story_data['state'], estimate_value, pipeline_name])

        print ("Total: %s") % pt_total
        if option_csv:
            SUM = '=SUM(E1:E%s)' % len(zen_epic['issues'])
            csvout.writerow(["----","Total","----","----",SUM])
    else:
        print "ERROR: <%s> %s is NOT an epic" % ( issueNumber, github_data['title'])



parser = argparse.ArgumentParser()
parser.add_argument('-e', help='Enter epic number', type=int)

parser.add_argument('-csv', action='store_true',help='create csv file')
parser.add_argument('-pipe', action='store_true',help='add pipeline information')

subparsers = parser.add_subparsers()



report = subparsers.add_parser('report', help='Generate report')
report.set_defaults(func=do_report)

args = parser.parse_args()
CTM =  (datetime.datetime.now().strftime("%y-%m-%d-%H%M%S"))
if args.csv:
    csvfile = 'epic-%s-issue-list-%s.csv' % (str(args.e), CTM)
    csvout = csv.writer(open(csvfile, 'wb'))
    option_csv = 'True'

if args.e is None:
    parser.print_help()
    sys.exit()
    
if args.pipe:
    option_pipe = 'True'

if 'func' in args:
    args.func(args)
else:
    parser.print_help()
