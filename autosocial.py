from __future__ import print_function
import httplib2
import os
from apiclient import discovery
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import tweepy
import pickle
import pandas as pd
import facebook
import requests
from time import sleep
import datetime as dt
import json
import urllib2
import time
import datetime



#TWITTER
auth = tweepy.OAuthHandler('61Na8Rux5ctU8vq7CTT3tpmoq', 'stUwgMMLeaY1PHCmnH3LtcC4tKOmRtohsMYXcdhUNdT6Fncfjh')
auth.set_access_token('987585836-a0v50E80sjArhFu4wFAXTYW3WpEyL0VN9KsKUcvs', 'LA0n9vW6SeR62I1ZUJJkmwyfPAEx5I07C8ZPJp0UKeQUG')
api = tweepy.API(auth)

#collect recent timeline pages
pgs = []
for page in tweepy.Cursor(api.user_timeline, screen_name='PacificStand', include_rts=False).pages(20):
    pgs.append(page)

#empty lists for dataframe
rts = []
favs = []
dtime = []
text = []
ids = []

#collect tweet info
for i in pgs:
    for j in i:
        rts.append(j._json['retweet_count'])
        favs.append(j.favorite_count)
        dtime.append(j._json['created_at'])
        text.append(j.text)
        ids.append(j.id)

#Get follower count
tuser = api.get_user('PacificStand')
follow_count = tuser.followers_count

#build dataframe
df = pd.DataFrame()
df['retweets'] = rts
df['favs'] = favs
df['datetime'] = dtime
df['text'] = text
df['ids'] = ids
df['datetime'] = pd.to_datetime(df['datetime'])
df['date'] = df['datetime'].apply(pd.datetools.normalize_date)
df['total engagement'] = df['retweets'] + df['favs']
df['week'] = df['date'].dt.week
thisweek = dt.datetime.today().isocalendar()[1]

#limit to last week's tweets
df = df[df['week'] == thisweek-1]

#output data
alltweets = df['text'].count()
allretweets = df['retweets'].sum()
allfavs = df['favs'].sum()
topt = pd.DataFrame({'url' : list(df.sort_values('total engagement', ascending=False)['ids'])[0:5],
                   'retweets' : list(df.sort_values('total engagement', ascending=False)['retweets'])[0:5],
                   'favs' : list(df.sort_values('total engagement', ascending=False)['favs'])[0:5]})
topt['url'] = ['http://twitter.com/pacificstand/status/' + str(i) for i in topt['url']]


#FACEBOOK
graph = facebook.GraphAPI(access_token='EAAQSQ4ZCXLwgBAM8JmPRPBEPXgQF8ZAPJ6W4l9Fsq2wwr0ilroczIaZCdI4b5IWPkdHKBPGEEV2FyWrBe7Yu9SwahTIx6c8K4ogAtXLbRnXpW6hPWUt6ZAoMZCl4kNEu9nsVmKBIYlUZAtEysUCZB2BX6u8mDblODZAZAYq9h2BZBaQmxCFHdTm5jN')
feed = graph.get_object('345450075476606')
page_id = '345450075476606'
access_token='EAAQSQ4ZCXLwgBAM8JmPRPBEPXgQF8ZAPJ6W4l9Fsq2wwr0ilroczIaZCdI4b5IWPkdHKBPGEEV2FyWrBe7Yu9SwahTIx6c8K4ogAtXLbRnXpW6hPWUt6ZAoMZCl4kNEu9nsVmKBIYlUZAtEysUCZB2BX6u8mDblODZAZAYq9h2BZBaQmxCFHdTm5jN'

#URL request just for shares
def request_until_succeed(url):
    req = urllib2.Request(url)
    success = False
    while success is False:
        try:
            response = urllib2.urlopen(req)
            if response.getcode() == 200:
                success = True
        except Exception, e:
            print(e)
            time.sleep(5)

            print("Error for URL %s: %s" % (url, datetime.datetime.now()))

    return response.read()

#Get fan count
fbase = "https://graph.facebook.com"
fnode = "/PacificStand"
fparameters = "?fields=fan_count&limit=%s&access_token=%s" % (10, access_token) # changed
fgurl = fbase + fnode + fparameters
fgdata = json.loads(request_until_succeed(fgurl))

fan_count = fgdata['fan_count']

#Get Pacific Standard's posts
posts = graph.get_connections(feed['id'], 'posts')

#Collect ids
allids = []
k = 0

while k <= 3:
    try:
        for post in posts['data']:
            allids.append(post['id'])
        posts=requests.get(posts['paging']['next']).json()
        k += 1
    except KeyError:
        break

textf = []
datetimef = []
reactionsf = []
sharesf = []

#Get post data
for i in allids:
    try:
        post = graph.get_object(i)
        textf.append(post['message'])
        datetimef.append(post['created_time'])
        rs = []
        reacts = graph.get_connections(i, 'reactions')
        #Page through all reactions
        while(True):
            try:
                for r in reacts['data']:
                    rs.append(r)
                reacts = requests.get(reacts['paging']['next']).json()
            except KeyError:
                break
        reactionsf.append(rs)
        #Get share count
        base = "https://graph.facebook.com"
        node = "/" + i
        parameters = "?fields=shares&limit=%s&access_token=%s" % (10, access_token) # changed
        gurl = base + node + parameters
        gdata = json.loads(request_until_succeed(gurl))
        try:
            sharesf.append(gdata['shares']['count'])
        except:
            sharesf.append(0)
    except:
        pass

allids = [i.split('_')[1] for i in allids]
#Build dataframe
dff = pd.DataFrame()
dff['text'] = textf
dff['datetime'] = datetimef
dff['reactions'] = reactionsf
dff['ids'] = allids
dff['shares'] = sharesf

#Clean dataframe
dff['reactinfo'] = dff['reactions']
for i, row in dff.iterrows():
    dff.set_value(i, 'reactions', len(row['reactions']))
dff['datetime'] = pd.to_datetime(dff['datetime'])
dff['date'] = dff['datetime'].apply(pd.datetools.normalize_date)
dff['total engagement'] = dff['reactions'] + dff['shares']

#Time constrain
dff['week'] = dff['date'].dt.week
thisweek = dt.datetime.today().isocalendar()[1]
dff = dff[dff['week'] == thisweek-1]

#Output
allreacts = dff['reactions'].sum()
allposts = dff['text'].count()
allshares = dff['shares'].sum()

topf = pd.DataFrame({'url' : list(dff.sort_values('total engagement', ascending=False)['ids'])[0:5],
                   'reactions' : list(dff.sort_values('total engagement', ascending=False)['reactions'])[0:5],
                    'shares' : list(dff.sort_values('total engagement', ascending=False)['shares'])[0:5]})
topf['url'] = ['https://www.facebook.com/PacificStand/posts/' + str(i) for i in topf['url']]


#SITE ANALYTICS
ASCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
AKEY_FILE_LOCATION = 'client_secrets.json'
AVIEW_ID = '122434448'


def initialize_analyticsreporting():
  """Initializes an Analytics Reporting API V4 service object.

  Returns:
    An authorized Analytics Reporting API V4 service object.
  """
  credentials = ServiceAccountCredentials.from_json_keyfile_name(
      AKEY_FILE_LOCATION, ASCOPES)

  # Build the service object.
  analytics = build('analytics', 'v4', credentials=credentials)

  return analytics

def get_report(analytics):
  """Queries the Analytics Reporting API V4.

  Args:
    analytics: An authorized Analytics Reporting API V4 service object.
  Returns:
    The Analytics Reporting API V4 response.
  """
  return analytics.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': AVIEW_ID,
          'dateRanges': [{'startDate': '7daysAgo', 'endDate': 'yesterday'}],
          'metrics': [{'expression': 'ga:pageviews'}]
        }]
      }
  ).execute()

def print_response(response):
  """Parses and prints the Analytics Reporting API V4 response.

  Args:
    response: An Analytics Reporting API V4 response.
  """
  for report in response.get('reports', []):
    columnHeader = report.get('columnHeader', {})
    dimensionHeaders = columnHeader.get('dimensions', [])
    metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])

    for row in report.get('data', {}).get('rows', []):
      dimensions = row.get('dimensions', [])
      dateRangeValues = row.get('metrics', [])

      for i, values in enumerate(dateRangeValues):
        for metricHeader, value in zip(metricHeaders, values.get('values')):
            pvs = value
  return pvs

#TOP POSTS
def get_report_posts(analytics):
  """Queries the Analytics Reporting API V4.

  Args:
    analytics: An authorized Analytics Reporting API V4 service object.
  Returns:
    The Analytics Reporting API V4 response.
  """
  return analytics.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': AVIEW_ID,
          'dateRanges': [{'startDate': '7daysAgo', 'endDate': 'yesterday'}],
          'dimensions': [{'name': 'ga:pagePath'}],
          'metrics': [{'expression': 'ga:pageviews'}],
          'orderBys': [{'fieldName': 'ga:pageviews', 'sortOrder': 'DESCENDING'}]
        }]
      }
  ).execute()

def print_response_posts(response_posts):
  """Parses and prints the Analytics Reporting API V4 response.

  Args:
    response: An Analytics Reporting API V4 response.
  """
  pages = []
  for report in response_posts.get('reports', []):
    columnHeader = report.get('columnHeader', {})
    dimensionHeaders = columnHeader.get('dimensions', [])
    metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])
    for row in report.get('data', {}).get('rows', []):
      dimensions = row.get('dimensions', [])
      dateRangeValues = row.get('metrics', [])

      for header, dimension in zip(dimensionHeaders, dimensions):
        url = 'www.psmag.com' + dimension

      for i, values in enumerate(dateRangeValues):
        for metricHeader, value in zip(metricHeaders, values.get('values')):
          pvs = value
          pages.append((url, int(pvs)))
    for i in pages[0:10]:
        if '/amp/' in i[0] or i[0] == 'www.psmag.com/':
            pages.remove(i)
    return pages[0:5]

def analytics_main():
    analytics = initialize_analyticsreporting()
    response = get_report(analytics)
    pageviews = print_response(response)
    return int(pageviews)

def analytics_main_posts():
    analytics = initialize_analyticsreporting()
    response_posts = get_report_posts(analytics)
    top_posts = print_response_posts(response_posts)
    return top_posts

#GOOGLE SHEETS
try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Sheets API Python Quickstart'

#get credentials
def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

#save values
def main():
    """Shows basic usage of the Sheets API.

    Creates a Sheets API service object and prints the names and majors of
    students in a sample spreadsheet:
    https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    spreadsheetId = '1NQt7wa9XSvtswcdy_uZ0Dg-Y-kIQ4dLwEPcffTMla-M'
    range_name='A6:A7'
    value_input_option='RAW'

    values = [[str(df['date'].min())[:-8] + ' - ' + str(df['date'].max())[:-8],
    allretweets / alltweets, allfavs / alltweets, alltweets/7, allreacts / allposts, allposts/7, allshares / allposts, analytics_main() / 7, '',
    str(df['date'].min())[:-8] + ' - ' + str(df['date'].max())[:-8], allretweets, allfavs,
    alltweets, follow_count, allreacts, allposts, allshares, fan_count, analytics_main(), '']]
    body = {'values' : values}
    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheetId, range=range_name,
        valueInputOption=value_input_option, body=body).execute()

def main2():
    """Shows basic usage of the Sheets API.

    Creates a Sheets API service object and prints the names and majors of
    students in a sample spreadsheet:
    https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    spreadsheetId = '1NQt7wa9XSvtswcdy_uZ0Dg-Y-kIQ4dLwEPcffTMla-M'
    range_name='V23:W23'
    value_input_option='RAW'

    values = [[str(df['date'].min())[:-8] + ' - ' + str(df['date'].max())[:-8], topt.iloc[0].values.tolist()[2],
    topt.iloc[0].values.tolist()[1], topt.iloc[0].values.tolist()[0], topf.iloc[0].values.tolist()[2], topf.iloc[0].values.tolist()[0], topf.iloc[0].values.tolist()[1],
    analytics_main_posts()[0][0], analytics_main_posts()[0][1]],
    ['^', topt.iloc[1].values.tolist()[2], topt.iloc[1].values.tolist()[1], topt.iloc[1].values.tolist()[0],
    topf.iloc[1].values.tolist()[2], topf.iloc[1].values.tolist()[0], topf.iloc[1].values.tolist()[1],
    analytics_main_posts()[1][0], analytics_main_posts()[1][1]],
    ['^', topt.iloc[2].values.tolist()[2], topt.iloc[2].values.tolist()[1], topt.iloc[2].values.tolist()[0],
    topf.iloc[2].values.tolist()[2], topf.iloc[2].values.tolist()[0], topf.iloc[2].values.tolist()[1],
    analytics_main_posts()[2][0], analytics_main_posts()[2][1]],
    ['^', topt.iloc[3].values.tolist()[2], topt.iloc[3].values.tolist()[1], topt.iloc[3].values.tolist()[0],
    topf.iloc[3].values.tolist()[2], topf.iloc[3].values.tolist()[0], topf.iloc[3].values.tolist()[1],
    analytics_main_posts()[3][0], analytics_main_posts()[3][1]],
    ['^', topt.iloc[4].values.tolist()[2], topt.iloc[4].values.tolist()[1], topt.iloc[4].values.tolist()[0],
    topf.iloc[4].values.tolist()[2], topf.iloc[4].values.tolist()[0], topf.iloc[4].values.tolist()[1],
    analytics_main_posts()[4][0], analytics_main_posts()[4][1]]]
    body = {'values' : values}
    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheetId, range=range_name,
        valueInputOption=value_input_option, body=body).execute()

main()
main2()
