import logging
from telegram.utils.helpers import escape_markdown
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler, InlineQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineQueryResultArticle, InputTextMessageContent, ChatAction
from functools import wraps
import random
import os
from uuid import uuid4
import time
import datetime
from linktoairtable import *
from threading import Event
import re
from configure import TOKEN, DOMAIN

# 本地缓存，避免每次都要从Airtable拉取名单
LIST_OF_ADMINS = getadminlist()
LIST_OF_SZENL = get_agent_dic()[0]
LIST_OF_CORE = getuserid_bylevel('Core')

AGENT_DIC = get_agent_dic()[1] # {userid: recordid}
AGENT_DIC2 = get_agent_dic()[2] # {recordid: userid}


def admin(func):
    @wraps(func)
    def wrapped(bot, update, chat_data):
        user_id = update.effective_user["id"]
        if user_id not in LIST_OF_ADMINS:
            bot.send_message(chat_id=update.effective_user["id"], text="Unauthorized access denied.")
            return
        return func(bot, update, chat_data)
    return wrapped

def szenl(func):
    @wraps(func)
    def wrapped(bot, update, chat_data):
        user_id = update.effective_user["id"]
        if user_id not in LIST_OF_SZENL:
            bot.send_message(chat_id=update.effective_user["id"], text="Unauthorized access denied.")
            return
        return func(bot, update, chat_data)
    return wrapped

def core(func):
    @wraps(func)
    def wrapped(bot, update, chat_data):
        user_id = update.effective_user["id"]
        if user_id not in LIST_OF_CORE:
            bot.send_message(chat_id=update.effective_user["id"], text="Unauthorized access denied.")
            return
        return func(bot, update, chat_data)
    return wrapped

def privatechat(func):
    @wraps(func)
    def wrapped(bot, update, chat_data):
        if not update['message']['chat']['type']=='private': # group区分group和supergroup
            update.message.reply_text('请私聊bot进行操作')
            bot.send_message(chat_id=update.effective_user["id"], text="ping")
            return
        return func(bot, update, chat_data)
    return wrapped

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("szenlbot.log"),
        logging.StreamHandler()])

logger = logging.getLogger(__name__)

# Conversation setting
BROADCASTBUTTON, BROADCASTCONTENT = range(2)
MULTICASTBUTTON, MULTICASTCONTENT = range(2)

# Send action while handling command (decorator)
def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        def command_func(*args, **kwargs):
            bot, update = args
            bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return func(bot, update, **kwargs)
        return command_func
    
    return decorator

def start(bot, update):
    """Send a message when the command /start is issued."""
    logger.info("User {} started bot".format(update.effective_user["username"]))
    bot.send_message(chat_id=update.message.chat_id, text='欢迎使用深绿草丛小助手！如果你是深绿，请输入*"/register 你的agent名（不带@）"*以登记使用该bot（注意指令和agent名中间要有空格）。\n其他功能陆续完善中，敬请期待。', parse_mode=ParseMode.MARKDOWN)

# 按钮反馈
def button(bot, update, chat_data):
    query = update.callback_query
    global AGENT_DIC, AGENT_DIC2
    if re.match('join', query.data): # 加入活动
        event = query.data.lstrip('join')
        
        if joinevent(AGENT_DIC[update.effective_user["id"]], event):
            bot.answer_callback_query(query.id, text = 'Success')
            bot.send_message(chat_id=update.effective_user["id"], text = '成功加入活动*{}*'.format(event), parse_mode=ParseMode.MARKDOWN)
            logger.info("User {} joined event {}".format(update.effective_user["username"], event))

            recordidlist = getorganizerid(event) # 给组织者发消息提醒
            for record_id in recordidlist:
                chat_id = AGENT_DIC2[record_id]
                keyboard = [[InlineKeyboardButton('发送活动群组邀请链接', callback_data='sendlink_{}_{}'.format(update.effective_user["id"], event))]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                bot.send_message(chat_id=chat_id, text = '@{} 参加了活动{}'.format(update.effective_user["username"], event), reply_markup = reply_markup)

        else:
            bot.answer_callback_query(query.id, text = '您已经登记参加了{}'.format(event))

    elif re.match('exit', query.data): # 退出活动
        event = query.data.lstrip('exit')

        if exitevent(AGENT_DIC[update.effective_user["id"]], event):
            bot.send_message(chat_id=update.effective_user["id"], text="成功退出活动*{}*".format(event), parse_mode=ParseMode.MARKDOWN)
            logger.info("User {} exited event {}".format(update.effective_user['username'], event))
            bot.answer_callback_query(query.id, text = 'Success')

            recordidlist = getorganizerid(event) # 给组织者发消息提醒
            for record_id in recordidlist:
                chat_id = AGENT_DIC2[record_id]
                bot.send_message(chat_id=chat_id, text = '@{} 退出了活动{}'.format(update.effective_user["username"], event))

        else:
            bot.answer_callback_query(query.id, text='您未登记参与该活动')

    elif re.match('view', query.data):
        event = query.data.lstrip('view')
        count, attendee, codename = getattendee(event)
        if count == 0:
            bot.send_message(chat_id=update.effective_user["id"], text="目前还没有agent报名参加{}".format(event))
        else:
            bot.send_message(chat_id=update.effective_user["id"], text="共有{}名agent报名参加了{}，他们是：\n{}\n\n游戏内ping：{}".format(count, event, attendee, codename))

    elif re.match('Register', query.data):
        levelandagent = query.data.lstrip('Register')
        
        if re.match('Core', levelandagent):
            level = 'Core'
            agent_userid = levelandagent.lstrip('Core')
        else:
            level = 'General'
            agent_userid = levelandagent.lstrip('General')
        
        if insert_level(agent_userid, level):
            query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(('Granted access level: {}').format(level), callback_data='temp')]])) 
            
            LIST_OF_ADMINS = getadminlist()
            LIST_OF_SZENL = get_agent_dic()[0]
            LIST_OF_CORE = getuserid_bylevel('Core')
            AGENT_DIC = get_agent_dic()[1] # {userid: recordid}
            AGENT_DIC2 = get_agent_dic()[2] # {recordid: userid}
            bot.send_message(chat_id = agent_userid, text = '审核成功')
        else:
            query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Access granted by other admin', callback_data='temp')]]))                                               

    elif re.match('sendlink', query.data): # 邀请进群
        agentid = query.data.split("_")[1]
        event = query.data.split("_")[2]
        try:
            link = get_group_link(event)
            bot.send_message(chat_id = agentid, text = '{}活动群：{}'.format(event, link))    
            bot.answer_callback_query(query.id, text = '发送成功')    
        except:
            bot.answer_callback_query(query.id, text = '找不到相关链接')    
            
# 快捷查询user id
def id(bot, update):
    update.message.reply_text(update.message.chat_id)

# 特工登记
def register(bot, update):
    agent = update.message.text.lstrip('/register').lstrip(' ')
    username = update.effective_user["username"]
    userid = update.effective_user["id"]
    
    if agent:
        if registeragent(agent, username, userid):
            update.message.reply_text('注册成功，用户权限审核中')
            logger.info("User {} has registered".format(update.effective_user["username"]))
            for admin_chat_id in LIST_OF_ADMINS:
                keyboard = [[InlineKeyboardButton('Core', callback_data='RegisterCore{}'.format(update.effective_user["id"]))], [InlineKeyboardButton('General', callback_data='RegisterGeneral{}'.format(update.effective_user["id"]))]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                bot.send_message(chat_id=admin_chat_id, text="Agent {} (@{}) has registered".format(agent, update.effective_user["username"]), reply_markup = reply_markup)
        else:
            update.message.reply_text('Agent already in the system.')
    else:
        update.message.reply_text('请检查输入格式是否正确')

# 广播消息（根据密级）
@privatechat
@admin
def broadcast(bot, update, chat_data):
    keyboard = [[InlineKeyboardButton('Core', callback_data='Core')], [InlineKeyboardButton('General', callback_data='General')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('请选择消息加密等级\n如欲终止操作，请输入 /cancel', reply_markup=reply_markup)

    return BROADCASTBUTTON

def broadcastbutton(bot, update, chat_data):
    query = update.callback_query
    query.edit_message_text(text="您已选择 *{}*\n请确认无误后在对话框中输入要广播的消息。如欲终止操作，请输入 /cancel".format(query.data), parse_mode=ParseMode.MARKDOWN)
    chat_data['level'] = query.data

    return BROADCASTCONTENT

def broadcastcontent(bot, update, chat_data):
    content = update.message.text
    idlist = getuserid_bylevel(chat_data['level'])
    for chat_id in idlist:
        bot.send_message(chat_id=chat_id, text='Message from {}: {}'.format(update.effective_user["username"], content))
    bot.send_message(chat_id=update.message.chat_id, text="Broadcast successful.")
    logger.info("User {} broadcasted message {}".format(update.effective_user["username"], content))

    return ConversationHandler.END 

# 广播消息（根据活动）
@privatechat
def multicast(bot, update, chat_data):
    try:
        eventlist = getevent_byorganizer(update.message.chat_id)
        keyboard = [[InlineKeyboardButton('{}参与者'.format(event), callback_data=event)] for event in eventlist]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('请选择消息接收对象\n如欲终止操作，请输入 /cancel', reply_markup=reply_markup)

        return MULTICASTBUTTON
    
    except:
        update.message.reply_text('您目前没有组织任何活动')
        return ConversationHandler.END 

def multicastbutton(bot, update, chat_data):
    query = update.callback_query
    query.edit_message_text(text="您已选择 *{}*\n请确认无误后在对话框中输入要广播的消息（目前只支持文字消息）。如欲终止操作，请输入 /cancel".format(query.data), parse_mode=ParseMode.MARKDOWN)
    chat_data['event'] = query.data

    return MULTICASTCONTENT

def multicastcontent(bot, update, chat_data):
    global AGENT_DIC2
    content = update.message.text
    recordidlist = getattendeeid(chat_data['event'])
    for record_id in recordidlist:
        chat_id = AGENT_DIC2[record_id]
        bot.send_message(chat_id=chat_id, text='Message from {}: {}'.format(update.effective_user["username"], content))
    bot.send_message(chat_id=update.message.chat_id, text="Multicast successful.")
    logger.info("User {} multicasted '{}' for event {}".format(update.effective_user["username"], content, chat_data['event']))

    return ConversationHandler.END 

# 查看社群活动
@szenl
def event(bot, update, chat_data):
    eventlist = getevent()
    eventtextlist = ['*{}*\n组织者：{}\n日期：{}\n{}\n\n-------------'.format(event['Event'], getagentinfo_byrecordid(event['Organizer'])[4], str(datetime.datetime.strptime(event['Date'], "%Y-%m-%dT%H:%M:%S.%fZ"))[0:16], event['Notes']) for event in eventlist]
    eventtext = ('\n\n').join(eventtextlist)
    text = '{}\n\n请点击下列按钮，或私戳 @SZENLbot 输入/join加入对应活动（请确保您已start bot且登记成功）'.format(eventtext)
    keyboard = [[InlineKeyboardButton('点击加入{}'.format(event['Event']), callback_data='join{}'.format(event['Event']))] for event in eventlist]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id=update.message.chat_id, text=text, reply_markup = reply_markup, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    logger.info("User {} sent command /event".format(update.effective_user["username"]))

# 查看活动参与者
@privatechat
@szenl
def view(bot, update, chat_data):
    logger.info("User {} sent command /view".format(update.effective_user["username"]))
    
    eventlist = getevent()
    keyboard = [[InlineKeyboardButton(event['Event'], callback_data='view{}'.format(event['Event']))] for event in eventlist]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id=update.message.chat_id, text="请选择您要查询的活动", reply_markup=reply_markup)
    
# 加入活动
@privatechat
@szenl
def join(bot, update, chat_data):
    eventlist = getevent()
    keyboard = [[InlineKeyboardButton(event['Event'], callback_data='join{}'.format(event['Event']))] for event in eventlist]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id=update.message.chat_id, text="请选择您要参加的活动", reply_markup=reply_markup)
    chat_data['id'] = update.message.chat_id
    chat_data['username'] = update.effective_user["username"]

# 退出活动
@privatechat
@szenl
def exit(bot, update, chat_data):
    eventlist = getevent()
    keyboard = [[InlineKeyboardButton(event['Event'], callback_data=('exit{}'.format(event['Event'])))] for event in eventlist]
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(chat_id=update.message.chat_id, text="请选择您要退出的活动", reply_markup=reply_markup)
    chat_data['id'] = update.message.chat_id
    chat_data['username'] = update.effective_user["username"]
    
# 取消操作
def cancel(bot, update, chat_data):
    update.message.reply_text('您已中止操作。如需继续操作，请重新输入指令')
    return ConversationHandler.END

# 查看自己参加过的活动
def myevent(bot, update, chat_data):
    logger.info("User {} sent command /myevent".format(update.effective_user["username"]))
    pasteventlist, futureeventlist = getmyevent(update.effective_user["id"])
    if pasteventlist or futureeventlist:
        pastevent = ('\n').join(pasteventlist)
        futureevent = ('\n').join(futureeventlist)
        text = '{} 参加过的活动有：\n\n待进行：\n{}\n\n已完成：\n{}'.format(update.effective_user["username"], futureevent, pastevent)
        bot.send_message(chat_id=update.message.chat_id, text=text)
    else:
        bot.send_message(chat_id=update.message.chat_id, text='您没有参与过任何活动')

# 普通消息回复
@send_action(ChatAction.TYPING)
def echo(bot, update):
    """Echo the user message."""
    logger.info("User {} sent message '{}', message id is {}.".format(update.effective_user["username"], update.message.text, update.message.message_id))
    bot.send_message(chat_id=update.message.chat_id, text=random.choice(['🤔', 'Hello {}'.format(update.effective_user["username"])]))
        
def error(bot, update, error, chat_data):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)
    try:
        cancel(bot, update, chat_data) # 退出正在进行的conversation
    except:
        pass

def main():

    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(token=TOKEN)
    # updater.job_queue.run_daily(alarm, datetime.strptime('10:54PM', '%I:%M%p'))

    # Get the dispatcher to register handlers
    dp = updater.dispatcher
    
    # Conversation
    broadcast_handler = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast, pass_chat_data=True)],
        states={
            BROADCASTBUTTON: [CallbackQueryHandler(broadcastbutton, pass_chat_data=True)],
            BROADCASTCONTENT: [MessageHandler(Filters.text, broadcastcontent, pass_chat_data=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel, pass_chat_data=True),
            MessageHandler(Filters.text, broadcast, pass_chat_data=True)],
        conversation_timeout = 300
    )

    multicast_handler = ConversationHandler(
        entry_points=[CommandHandler("multicast", multicast, pass_chat_data=True)],
        states={
            BROADCASTBUTTON: [CallbackQueryHandler(multicastbutton, pass_chat_data=True)],
            BROADCASTCONTENT: [MessageHandler(Filters.text, multicastcontent, pass_chat_data=True)]
        },
        fallbacks=[CommandHandler('cancel', cancel, pass_chat_data=True),
            MessageHandler(Filters.text, multicast, pass_chat_data=True)],
        conversation_timeout = 300
    )

    dp.add_handler(broadcast_handler)
    dp.add_handler(multicast_handler)

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("id", id))
    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("event", event, pass_chat_data=True))
    dp.add_handler(CommandHandler("myevent", myevent, pass_chat_data=True))
    dp.add_handler(CommandHandler("join", join, pass_chat_data=True))
    dp.add_handler(CommandHandler("exit", exit, pass_chat_data=True))
    dp.add_handler(CommandHandler("view", view, pass_chat_data=True))

    dp.add_handler(CallbackQueryHandler(button, pass_chat_data=True))

    # on noncommand 
    dp.add_handler(MessageHandler(Filters.text, echo))
    dp.add_handler(MessageHandler(Filters.sticker, echo))

    # log all errors
    dp.add_error_handler(error)
    
    # set webhook for heroku if you plan to deploy it on heroku
    PORT = int(os.environ.get('PORT', '8443'))
    updater.start_webhook(listen="0.0.0.0",
                    port=PORT,
                    url_path=TOKEN)
    updater.bot.set_webhook(DOMAIN + TOKEN)

    # Start the Bot
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
