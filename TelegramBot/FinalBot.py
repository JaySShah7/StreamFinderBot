import re,praw, pprint, time, importlib, threading, os, sys
from telegram.ext import Updater 
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, InlineQueryHandler
import telegram.ext
from telegram import InlineQueryResultArticle, InputTextMessageContent
import Matches #Matches.Matches is list of matches, filename=Matches.py
from AuthenticationInfo import *
#change cwd


os.chdir(sys.path[0])




import logging
from logging.handlers import RotatingFileHandler
#logging.basicConfig(filename='TelegramBotLog.log',
#                    level=logging.INFO,
 #                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger=logging.getLogger(__name__)
handler=RotatingFileHandler('TelegramBotLog.log', maxBytes=100000, backupCount=1)
logger.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

logger.info("Program started.")

def FindMatchInfo(title):                           #Regex search for post title
                                                    #regex groups: timewithbrackets, time, team1 , vs, team2
    #TeamNameRegex=re.compile(r'''(\[(.* \w\w\w)\] )(.*)( vs. | vs )(.*)''', re.I)
    TeamNameRegex=re.compile(r'''(\[(.* \w\w\w)\]\s?)(.*)( vs. | vs | - )(.*)''', re.I)
    TeamRegexValue=TeamNameRegex.findall(title)
    
    lista=[TeamRegexValue[0][2],TeamRegexValue[0][4],TeamRegexValue[0][1]]
    return lista




def LogIn():
    rdt=praw.Reddit(username=username, client_id=client_ID, client_secret=secret, user_agent='Test Bot')
    #print('\nReddit logged in via: '+username)
    logger.info('Reddit logged in.')
    return rdt
    
def GetStreamLinks(submission):                               #Returns stream Names and Links
    submission.comment_sort="hot"
    rawcomments=list(submission.comments)
    links=[]
    LinkRegex=re.compile(r'(\[(.*?)](\s)?\((.*?)\))')               #finds total, name, space, link
    
    for rawcomment in rawcomments:
        data=LinkRegex.findall(rawcomment.body)
        for stream in data:
            links.append({'Name':stream[1], 'Link':stream[3]})
            break
            

    return links
        


def GetMatches():                                       #returns matches list with Teams, Time, MatchName, Links 
    reddit=LogIn()
    subreddit=reddit.subreddit('soccerstreams')
    matches=[]
    for submission in subreddit.hot(limit=20):           
        try:
            matchinfo=FindMatchInfo(str(submission.title))   #matchinfo 0,1,2 will be team1, team2, time
            #print(submission.title)
            logger.info(submission.title)
            matchlinks=GetStreamLinks(submission)
          
            matchname=matchinfo[0]+' vs '+matchinfo[1]
            matches.append({'Teams':[matchinfo[0], matchinfo[1]], 'Time':matchinfo[2], 'Links':matchlinks, 'MatchName':matchname})




        except Exception as e:
            pass
        
    file=open('Matches.py', 'w', encoding='utf-8')                            #save to Matches.py
    file.write('Matches= '+pprint.pformat(matches)+'\n')
    file.close()
    #print("Stream Database updated.")
    logger.info('Stream database updated.')
    
    return(matches)



def printMatchLinks(match,number=5):                         #prints match links, for command line only
    for i in range(0, min(len(match['Links']),number-1)):
                   print("Stream Name: "+match['Links'][i]['Name'])
                   print("Stream Link: "+match['Links'][i]['Link']+'\n')

                   
                   
def AskForMatch():                                          #search for links via command line
    teamwanted=input("\nLinks for which team's game?")
    for match in Matches.Matches:
        if teamwanted.lower() in match['Teams'].lower():
            print("\n\nMatch:"+match['Teams'][0]+' vs '+match['Teams'][1])
            print("Time: "+match['Time'])
            printMatchLinks(match)


#---------------------------- END OF DATABASE FUNCTIONS ---------------------------------------------------

            
def echo(bot,update, args):
    userinput=' '.join(args)
    bot.send_message(chat_id=update.message.chat_id, text=userinput)
    
def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='I find football streams.\n\nSend the name of a team or game to find a stream!')
    logger.info("/start command invoked.")


def FindStream(bot, update):                                                    #Gives custom keyboard of streams
    #print("FindStream started by: "+ update.message.from_user['first_name']+' '+update.message.from_user['last_name']+' @'+update.message.from_user['username'])
    MatchNames=[]
    bot.send_message(chat_id=update.message.chat_id, text='Loading...')
    if Matches.Matches==[]:
        bot.send_message(chat_id=update.message.chat_id, text='There are currently no matches being broadcasted.\n\nLinks usually start to appear 30 minutes before the match.')
        return
    for match in Matches.Matches:
        button = telegram.KeyboardButton(text=match['MatchName'])
        
        MatchNames.append([button])
        
    MatchKeyboard=MatchNames
    reply_markup=telegram.ReplyKeyboardMarkup(MatchKeyboard, True, one_time_keyboard=True)
    bot.send_message(chat_id=update.message.chat_id, text='Select a match: ', reply_markup=reply_markup)
    #print('Match Option Keyboard sent to: '+ update.message.from_user['first_name']+' '+update.message.from_user['last_name']+' @'+update.message.from_user['username'])
    
def DisplayLinks(bot, update):                                                      #displays links after keyboard selection
    #print('DisplayLinks started by: '+ update.message.from_user['first_name']+' '+update.message.from_user['last_name']+' @'+update.message.from_user['username'])
    text=update.message.text
    output=''
    
    for match in Matches.Matches:
        
        if text.lower() in match['MatchName'].lower(): #compares input with matchname or team name
            
            output+=("\n\nMatch: "+match['Teams'][0]+' vs '+match['Teams'][1]+'\n')
            
            output+=("Time: "+match['Time']+'\n\n\n')
            
            for i in range(0, min(len(match['Links']),8)):
                
                output+=("Stream Name: "+match['Links'][i]['Name'] +'\n')
                output+=("Stream Link: "+match['Links'][i]['Link']+'\n\n')
        
            if(len(match['Links']))==0:
                   output+='No streaming links found for this match.\n\n'
        
                
    if output=='':
        bot.send_message(chat_id=update.message.chat_id, text="Can't find a stream for that match/team.\nHere are the currently broadcasted matches:")
        FindStream(bot,update)
    else:
        
        bot.send_message(chat_id=update.message.chat_id, text=output)
    #print("Links sent to: "+ update.message.from_user['first_name']+' '+update.message.from_user['last_name']+' @'+update.message.from_user['username'])

def InlineQuery(bot, update):
    
    query=update.inline_query.query
    logger.info('Inline mode activated.')
    results=[]
    x=0 #counter, unique id
    for match in Matches.Matches:
        output=''
           
        if query.lower() in match['MatchName'].lower(): #compares input with matchname or team name
            
            output+=("\n\nMatch: "+match['Teams'][0]+' vs '+match['Teams'][1]+'\n')
            
            output+=("Time: "+match['Time']+'\n\n\n')
            
            for i in range(0, min(len(match['Links']),8)):
                
                output+=("Stream Name: "+match['Links'][i]['Name'] +'\n')
                output+=("Stream Link: "+match['Links'][i]['Link']+'\n\n')
        
            if(len(match['Links']))==0:
                   output+='No streaming links found for this match.\n\n'
            
            results.append(InlineQueryResultArticle(id=x,
                                                    title=(match['Teams'][0]+' vs '+match['Teams'][1]),
                                                    input_message_content=InputTextMessageContent(output)))
            x+=1
    if results==[]:
        output=''
        for match in Matches.Matches:
            output+=(match['MatchName']+'\n')
        if output=='':
            output+=('No matches are currently being broadcasted.')
        output+=('\nStreaming links usually appear 30 minutes before a game.')
        results.append(InlineQueryResultArticle(id=x,
                                                title=('Team not found. Click for list of matches.'),
                                                input_message_content=InputTextMessageContent(output)))
                    
    
    update.inline_query.answer(results)
    
def UpdateDatabase():
    while True:
        try:
            GetMatches()
            importlib.reload(Matches)
            logger.info('Database reloaded.')
            #print("Stream Database reloaded at: "+time.ctime()+'\n')
        except Exception as e:
            logger.error("Error retrieving matches. Could not reload database.")
        time.sleep(900) #every 15 min

        
#GetMatches()          #Update or create database, now done in thread                               


updater=Updater(token=TelegramToken)
dispatcher=updater.dispatcher
#print("Telegram bot connected.")
logger.info('Telegram bot connected.')

start_handler=CommandHandler('start', start)                                 #for /Start
dispatcher.add_handler(start_handler)

echo_handler = CommandHandler('echo', echo, pass_args=True)                  #test echo function
dispatcher.add_handler(echo_handler)

findstream_handler=CommandHandler('findstream', FindStream)                  
dispatcher.add_handler(findstream_handler)

displaylink_handler=MessageHandler(telegram.ext.Filters.text, DisplayLinks)  
dispatcher.add_handler(displaylink_handler)

inline_handler=InlineQueryHandler(InlineQuery)
dispatcher.add_handler(inline_handler)

updater.start_polling()
t1=threading.Thread(target=UpdateDatabase)               #thread to update every 10 min
t1.daemon=True
t1.start()
