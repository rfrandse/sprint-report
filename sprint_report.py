#!/usr/bin/python


import argparse
import json
import config
import requests
import datetime
import csv
import sys
import re
import time
from datetime import timedelta
import dateutil.parser
import pytz

from slacker import Slacker
slack = Slacker(config.token)


OPENBMC_REPO_ID = '42542702'
ZENHUB_API = 'https://api.zenhub.io/p1/repositories/%s/' % OPENBMC_REPO_ID
ZENHUB_API_ISSUES = ZENHUB_API + 'issues/'
ZENHUB_API_EPICS = ZENHUB_API + 'epics/'
GITHUB_AUTH = (config.GITHUB_USER, config.GITHUB_PASSWORD)
REPO_ID = '42542702'
GITHUB_API_ISSUES = 'https://api.github.com/repos/openbmc/openbmc/issues/'

option_csv = None
option_pipe = None
#current_date = datetime.datetime.now()
current_date = (datetime.datetime.now()).date()

day_late =  (dateutil.parser.parse(str(current_date + timedelta(days=-1)))).replace(tzinfo=pytz.UTC)
two_day_late = (dateutil.parser.parse(str(current_date + timedelta(days=-2)))).replace(tzinfo=pytz.UTC)
really_late = (dateutil.parser.parse(str(current_date + timedelta(days=-3)))).replace(tzinfo=pytz.UTC)

if current_date.weekday() == 0:
    day_late =  (dateutil.parser.parse(str(current_date + timedelta(days=-3)))).replace(tzinfo=pytz.UTC)
    two_day_late = (dateutil.parser.parse(str(current_date + timedelta(days=-4)))).replace(tzinfo=pytz.UTC)
    really_late = (dateutil.parser.parse(str(current_date + timedelta(days=-5)))).replace(tzinfo=pytz.UTC)
if current_date.weekday() == 1:
    two_day_late = (dateutil.parser.parse(str(current_date + timedelta(days=-4)))).replace(tzinfo=pytz.UTC)
    really_late = (dateutil.parser.parse(str(current_date + timedelta(days=-5)))).replace(tzinfo=pytz.UTC)
if current_date.weekday() == 2:
    really_late = (dateutil.parser.parse(str(current_date + timedelta(days=-5)))).replace(tzinfo=pytz.UTC)


phase_list = ['Phase 3',
            'Phase 4',
            'Phase 5',
            'Phase 5.1',
            'Phase 6',
            'Phase 7']

def do_team_report(args):
    issueNumberList = []
    if not isinstance(args.e, list):
            issueNumberList.append(str(args.e))
    else:
        issueNumberList = args.e
    for issueNumber in issueNumberList:
        process_team_report(issueNumber)

def process_team_report(issueNumber):
    owner_list = {}
    stat_list = {}
    
    issue_api_url = GITHUB_API_ISSUES + issueNumber

    github_data =  requests.get(issue_api_url, auth=GITHUB_AUTH).json()

    issue_zen_api_url = ZENHUB_API_ISSUES + issueNumber
    zenhub_data = requests.get(issue_zen_api_url, headers=config.zen_auth, verify=False).json()

    slack_message = ("team report:%s") % CTM
    slack_message += "\n----\n"
    slack_message += "_<https://github.com/openbmc/openbmc/issues/%s|#%s> %s_\n" % (issueNumber, issueNumber, github_data['title'])
    slack_message += "\n"


    if zenhub_data['is_epic']:
        issue_zen_api_epic_url = ZENHUB_API_EPICS + issueNumber
        zen_epic =  requests.get(issue_zen_api_epic_url, headers=config.zen_auth, verify=False).json()

        pt_total = 0
        for story in zen_epic['issues']:
            print ("processing %s") % story['issue_number']
            issue_api_url = GITHUB_API_ISSUES + str(story['issue_number'])
            github_story_data =  requests.get(issue_api_url, auth=GITHUB_AUTH).json()
#            print json.dumps(github_story_data, indent=4)
            issue_owner = 'unknown'
            if github_story_data['assignee'] is not None:
                issue_owner = (github_story_data['assignee']['login'])


            estimate = story.get('estimate')
            estimate_value = ''
            if estimate is not None:
                estimate_value = estimate.get('value')

            pipeline_name = ''
            pipeline_state = story.get('pipeline')
            if pipeline_state is not None:
                pipeline_name = pipeline_state['name']
            if github_story_data['state'] == 'closed':
                pipeline_name = 'Closed'
            bug_icon = ""
            phase_label = ""
            for label in github_story_data['labels']:
                if label['name'] == "bug":
                    bug_icon = ":bug:"
                if label['name'] in phase_list:
                    phase_label += label['name']

            comment_message = ''
            stat_message = "*<https://github.com/openbmc/openbmc/issues/%s|#%s> estimate:%s owner:%s state:%s* " % (
                    story['issue_number'], story['issue_number'], estimate_value,issue_owner, pipeline_name)

            no_status_message = "No STATUS :interrobang:"

            if github_story_data['state'] == 'closed':
                comment_message = "> -- Closed-- :fireworks:\n"
                no_status_message = ""
                stat_message += ":fireworks:"
            elif github_story_data['comments'] > 0:
                story_comments = requests.get(github_story_data['comments_url'], auth=GITHUB_AUTH).json()

                for comment in story_comments:                    
                    if "**STATUS**" in comment['body']:
                        no_status_message = ""
                        comment_date = dateutil.parser.parse(comment['updated_at'])

                        icon = ":fire::fire::fire:"
                        if comment_date > day_late:
                            icon =":white_check_mark:"
                        elif comment_date > two_day_late:
                            icon = ":warning:"
                        elif comment_date > really_late:
                            icon = ":fire::fire:"


                        stat_message += icon

                        comment_message += "Last updated: %s %s\n"  % (comment['updated_at'], icon)
                        comment_message += comment['body']
                        comment_message += "\n\n\n"

            comment_message += no_status_message
            comment_message += "\n"
            stat_message += no_status_message
            stat_message += phase_label
            message =  "*<https://github.com/openbmc/openbmc/issues/%s|#%s> %s* %s\n" % (
                    story['issue_number'], story['issue_number'], github_story_data['title'].encode('utf-8'),bug_icon)
            message += "owner:%s estimate:%s %s state:%s\n" % (issue_owner, estimate_value, phase_label, pipeline_name)
            message += comment_message

            owner_list.setdefault(issue_owner, []).append(message)            
            stat_list.setdefault(issue_owner, []).append(stat_message)

        slack_channel = '#openbmc_sprint_report'
        slack_channel = '@rfrandse'
        slack.chat.post_message(slack_channel, slack_message)


        sorted_owner_list =  sorted(owner_list.items(), key=lambda x: (x[0],x[1]))

        for owner_name, payload_message in sorted_owner_list:
            slack_message = "\n********\n%s\n~~~~\n>>>" % owner_name
            for data in payload_message:
                slack_message += data
                slack_message + "\n"
            slack_message += "\n"
            slack.chat.post_message(slack_channel, slack_message)

        slack_message = "Status Key\n"
        slack_message +=":white_check_mark: = Update Status Current\n"
        slack_message += ":warning:= last updated 1 day\n"
        slack_message += ":fire::fire:= last updated 2 days\n"
        slack_message += ":fire::fire::fire: = updated 3+ days ago\n\n"
            
        sorted_stat_list =  sorted(stat_list.items(), key=lambda x: (x[0],x[1]))
        for owner_name, payload_stat_message in sorted_stat_list:
            for data in payload_stat_message:
                slack_message += data
                slack_message += "\n"
        slack.chat.post_message(slack_channel, slack_message)

    else:
        print "ERROR: <%s> %s is NOT an epic" % ( issueNumber, github_data['title'])



def do_epic_report(args):
    issueNumber = str(args.e)
    issue_api_url = GITHUB_API_ISSUES + issueNumber

    github_data =  requests.get(issue_api_url, auth=GITHUB_AUTH).json()

    issue_zen_api_url = ZENHUB_API_ISSUES + issueNumber
    zenhub_data = requests.get(issue_zen_api_url, headers=config.zen_auth, verify=False).json()

    print("epic report:%s") % CTM
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



report_epic = subparsers.add_parser('report', help='Generate report')
report_epic.set_defaults(func=do_epic_report)

report_team = subparsers.add_parser('team', help='Generate team report')
report_team.set_defaults(func=do_team_report)

args = parser.parse_args()

print args

CTM =  (datetime.datetime.now().strftime("%y-%m-%d-%H%M%S"))
if args.csv:
    csvfile = 'epic-%s-issue-list-%s.csv' % (str(args.e), CTM)
    csvout = csv.writer(open(csvfile, 'wb'))
    option_csv = 'True'


if args.e is None:
    if hasattr(config, 'epic_list'):
        args.e = config.epic_list
    else:
        parser.print_help()
        sys.exit()

    
if args.pipe:
    option_pipe = 'True'

if 'func' in args:
    args.func(args)
else:
    parser.print_help()
