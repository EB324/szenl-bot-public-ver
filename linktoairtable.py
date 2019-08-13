from airtable import Airtable
import random
import datetime
import time
import re
from configure import BASE_KEY, API_KEY

# 获取所有已登记agent的user id, 以及他们的record id
def get_agent_dic():
    airtable = Airtable(BASE_KEY, 'member', api_key=API_KEY)

    records = airtable.get_all()
    agentlist = [record['fields']['User id'] for record in records if 'Classification level' in record['fields']]
    recordidlist = [record['id'] for record in records if 'Classification level' in record['fields']]
    agent_dic = dict(zip(agentlist, recordidlist))
    agent_dic2 = dict(zip(recordidlist, agentlist))
    return agentlist, agent_dic, agent_dic2

# 获得admin的user id
def getadminlist():
    airtable = Airtable(BASE_KEY, 'member', api_key=API_KEY)

    records = airtable.get_all()
    agentlist = [record['fields']['User id'] for record in records if 'Admin' in record['fields']]
    return agentlist

# 查询近五个NIA活动
def getactivity():
    airtable = Airtable(BASE_KEY, 'activity', api_key=API_KEY)

    records = airtable.get_all(maxRecords=5, sort=[('Start date', 'asc'), ('End date', 'asc')], filterByFormula="DATETIME_DIFF({End date}, NOW(), 'hours')>=8")
    activityList = [record['fields'] for record in records]
    return activityList

# 特工登记
def registeragent(agent, username, userid):
    airtable = Airtable(BASE_KEY, 'member', api_key=API_KEY)

    if airtable.match('Agent', agent): # 查重
        return False
    else:
        record = {'Agent': agent, 'User name': username, 'User id': userid}
        airtable.insert(record)
        return True

# Admin 审核
def insert_level(agent_userid, level):
    airtable = Airtable(BASE_KEY, 'member', api_key=API_KEY)
    record = airtable.match('User id', agent_userid)
    
    if 'Classification level' in record['fields']: 
        return False
    else:
        airtable.update_by_field('User id', agent_userid, {'Classification level': level})
        return True
    
# 根据加密等级返回User id list
def getuserid_bylevel(level):
    airtable = Airtable(BASE_KEY, 'member', api_key=API_KEY)

    records = airtable.search('Classification level', level)
    idlist = [record['fields']['User id'] for record in records if 'Unsubscribe' not in record['fields']]
    return idlist

# 查询社群活动
def getevent():
    airtable = Airtable(BASE_KEY, 'events', api_key=API_KEY)

    records = airtable.get_all(sort=[('Date', 'asc')], filterByFormula="DATETIME_DIFF({Date}, NOW(), 'hours')>=8")
    eventList = [record['fields'] for record in records]
    return eventList

# 输入活动名称 返回组织者 record id list
def getorganizerid(event):
    airtable = Airtable(BASE_KEY, 'events', api_key=API_KEY)

    record = airtable.match('Event', event)
    recordidlist = record['fields']['Organizer']
    return recordidlist   

# 输入活动名称 返回参与者User id list
def getattendeeid(event):
    airtable = Airtable(BASE_KEY, 'events', api_key=API_KEY)

    record = airtable.match('Event', event)
    recordidlist = record['fields']['Attendee']
    return recordidlist

# 输入活动名称 返回参与者数目及名称(string with @)
def getattendee(event):
    airtable = Airtable(BASE_KEY, 'events', api_key=API_KEY)
    
    record = airtable.match('Event', event)['fields']
    if 'Attendee' in record:
        attendeelist = record['Attendee']
        count = len(attendeelist)
        agents = getagentinfo_byrecordid(attendeelist)
        attendee = ('\n').join(agents[5]) # combine (codename + @username)
        agentcodename = agents[1] # codename with @
    else:
        count = 0
        attendee = ''
        agentcodename = ''
        
    return count, attendee, agentcodename

# 输入User id 返回参与的活动名称
def getmyevent(userid):
    airtable = Airtable(BASE_KEY, 'member', api_key=API_KEY)

    record = airtable.match('User id', userid)
    if 'Events attended' in record['fields']:
        eventidlist = record['fields']['Events attended']
        eventrecordlist = [getevent_byrecordid(i)[2] for i in eventidlist]
        pasteventlist = [eventrecord['fields']['Event'] for eventrecord in eventrecordlist if eventrecord['fields']['Countdown']<0]
        futureeventlist = [eventrecord['fields']['Event'] for eventrecord in eventrecordlist if eventrecord['fields']['Countdown']>=0]
    else:
        pasteventlist = []
        futureeventlist = []
    return pasteventlist, futureeventlist

# 输入User id 返回组织的活动名称
def getevent_byorganizer(organizer_userid):
    airtable = Airtable(BASE_KEY, 'member', api_key=API_KEY)
    
    eventrecordlist = airtable.match('User id', organizer_userid, filterByFormula='IS_AFTER({Date}, TODAY())')['fields']['Events organized']
    eventList = [getevent_byrecordid(i)[0] for i in eventrecordlist]

    return eventList

'''recordid <-> username'''
# 输入recordid（int/list） 输出agentname/username
def getagentinfo_byrecordid(recordid):
    airtable = Airtable(BASE_KEY, 'member', api_key=API_KEY)

    if isinstance(recordid, list):
        recordlist = airtable.get_all()
        agentlist = [i['fields']['Agent'] for i in recordlist if i['id'] in recordid]
        agent = (', ').join(agentlist)
        agent_with_at = '@{}'.format((', @').join(agentlist))
        usernamelist = [i['fields']['User name'] for i in recordlist if i['id'] in recordid]
        username = (', ').join(usernamelist)
        username_with_at = '@{}'.format((', @').join(usernamelist))
        combinelist = ['{} (@{})'.format(agentlist[i], usernamelist[i]) for i in range(0, len(agentlist))]
        combine = (', ').join(combinelist)
    else:
        record = airtable.get(recordid)
        agent = record['fields']['Agent']
        agent_with_at = '@{}'.format(agent)
        username = record['fields']['User name']
        username_with_at = '@{}'.format(username)
        combine = '{}({})'.format(agent, username_with_at)

    return agent, agent_with_at, username, username_with_at, combine, combinelist

'''recordid <-> userid'''
# 输入userid 输出recordid
def getagentrecordid_byuserid(userid):
    airtable = Airtable(BASE_KEY, 'member', api_key=API_KEY)

    recordid = airtable.match('User id', userid)['id']
    return recordid

# 输入recordid 输出userid
def getuserid_byrecordid(recordid):
    airtable = Airtable(BASE_KEY, 'member', api_key=API_KEY)

    userid = airtable.get(recordid)['fields']['User id']
    return userid

'''recordid <-> eventname'''
# 输入recordid 输出event
def getevent_byrecordid(recordid):
    airtable = Airtable(BASE_KEY, 'events', api_key=API_KEY)

    record = airtable.get(recordid)

    event = record['fields']['Event']
    if record['fields']['Countdown'] >= 0:
        state = 'not_yet_started'
    else:
        state = 'finished'
    return event, state, record

# 加入社群活动
def joinevent(recordid, event):
    airtable = Airtable(BASE_KEY, 'events', api_key=API_KEY)

    eventrecord = airtable.match('Event', event) 

    if 'Attendee' in eventrecord['fields']:
        if recordid in eventrecord['fields']['Attendee']:
            return False
        else:
            addendeelist = eventrecord['fields']['Attendee']
            addendeelist.append(recordid)
    else:
        addendeelist = [recordid]

    airtable.update_by_field('Event', event, {'Attendee': addendeelist}) 
    return len(addendeelist)

# 退出社群活动
def exitevent(recordid, event):
    airtable = Airtable(BASE_KEY, 'events', api_key=API_KEY)

    eventrecord = airtable.match('Event', event) 

    if 'Attendee' in eventrecord['fields']:
        if recordid in eventrecord['fields']['Attendee']:
            addendeelist = eventrecord['fields']['Attendee']
            addendeelist.remove(recordid)
        else:
            return False
    else:
        return False

    airtable.update_by_field('Event', event, {'Attendee': addendeelist})
    return True

# 检查是否有当日活动，返回list of events
def gettodayevent():
    airtable = Airtable(BASE_KEY, 'events', api_key=API_KEY)

    records = airtable.get_all(filterByFormula="IS_SAME({Date}, TODAY(), 'day')")

    return records

def get_group_link(event):
    airtable = Airtable(BASE_KEY, 'events', api_key=API_KEY)

    eventrecord = airtable.match('Event', event) 
    group_link = eventrecord['fields']['Group link']

    return group_link

if __name__ == '__main__':
    pass
