

import threading
import time
from datetime import datetime, timedelta
from selenium import webdriver

import pickle, os, sys, platform
import requests, json
from bs4 import BeautifulSoup
#to make sure aux files end up in the same directory
os.chdir(sys.path[0])


from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, InlineQueryHandler
import telegram.ext
from telegram import InlineQueryResultArticle, InputTextMessageContent

#Rotating File Handler to keep size down
import logging
from logging.handlers import RotatingFileHandler
logger=logging.getLogger(__name__)
handler=RotatingFileHandler('BotLog.log', maxBytes=100000, backupCount=1)
logger.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

from AuthenticationInfo import *

# how much to wait between database updates
UPDATE_FREQUENCY = 5 #in minutes

#if the league contains this word, it will be added to database (does not have to be a league name, can be a team name)
TEAM_LIST = ['manchester', 'liverpool', 'leicester', 'chelsea', 'wolve', 'arsenal', 'tottenham', 'burnley',
             'sheffield', 'everton', 'crystal palace', 'newcastle', 'southampton', 'brighton', 'west ham',
             'watford', 'aston villa', 'bournemouth', 'norwich',
             'bayern', 'borussia', 'leipzig', 'dortmund',
             'milan', 'inter', 'juventus', 'napoli', 'roma',
             'psg', 'paris', 'monaco', 'lyon',
             'barcelona', 'madrid', 'sevilla', 'brentford'
             ]
OS = platform.system()




class StreamFinder:

    def __init__(self, game_list = []):
        self.game_list = game_list
        self.hits = 0


    def calculate_time_difference(self, game_time, current_time = str(datetime.now().hour) + ":" + str(datetime.now().minute)):
        try:
            format = "%H:%M"
            game_time = datetime.strptime(game_time, format)
            current_time = datetime.strptime(current_time, format)
            dif = game_time - current_time
            hours = (dif.total_seconds() / 3600) % 24
            return hours
        except Exception as e:
            return 0



    #returns list of streams from individual match page
    def get_links_from_site(self, url):
        logger.debug("get_links_from_site started")
        links = []
        #try a max of 5 times if fail
        for i in range(5):
            try:
                r = requests.get(url, timeout = 15)
                logger.debug("Loaded links site for single game")
                links = []
                soup = BeautifulSoup(r.content, 'html.parser')
                logger.debug("loaded single game contents in beautifulsoup")
                break

            except Exception as e:
                logger.error("Could not get links for single game. Try number: " + str(i+1))
                logger.error(e)
                time.sleep(10)

        raw_stream_list = soup.findAll('div',
                                       attrs={'class': 'stream-item'})
        len_raw_stream_list = len(raw_stream_list)
        logger.debug("got stream list from beautiful soup object")

        # retrieve a maximum of 10 links
        for i in range(len_raw_stream_list if (len_raw_stream_list < 10) else 10):
            stream = raw_stream_list[i]
            link = stream.a['href']
            stream_name = stream.find('span', attrs={'class': 'first'}).text
            links.append({'name': stream_name,
                          'link': link})

        return links




    def get_stream_info(self, day = "{:02d}".format(datetime.now().day), month = "{:02d}".format(datetime.now().month)):
        streams = []
        url = "https://darsh.sportsvideo.net/new-api/matches?timeZone=-330&date=2020-" + month + "-" + day
        #try a max of 4 times
        for i in range(5):
            try:
                re = requests.get(url, timeout = 15)
                logger.debug('Loaded main page')
                raw_dict = json.loads(re.text)
                logger.debug('Loaded dict from main page json')
                break
            except Exception as e:
                logger.error("Could not parse main mage. Try: " + str(i+1))
                logger.error(e)
                time.sleep(10)
                if i == 4:
                    raise Exception("Max values reached. requests.get failed")

        for league in raw_dict:
            for single_game in league['events']:

                game_name = single_game['homeTeam']['name'] + " vs " + single_game['awayTeam']['name']
                game_id = str(single_game['id'])
                links_link = "https://101placeonline.com/streams-table/" + game_id + "/soccer"
                # Check if game has team in our list
                if any(word in game_name.lower() for word in TEAM_LIST):
                    logger.debug("Found game: " + game_name)
                    #print(game_name)

                    # check if highlights are available
                    if single_game['status']['type'] == 'finished':
                        logger.debug("Game is finished, getting highlights")
                        if single_game['hasHighlights']:
                            streams.append({'game': game_name,
                                            'time': "FULL TIME",
                                            'links': [{'link': single_game['eventLink'],
                                                       'name': 'HIGHLIGHTS'}]})
                    #check if stream is available, and set the time accordingly
                    elif single_game['hasStreams']:
                        logger.debug("Game has streams, appending list")
                        if single_game['status']['type'] == 'inprogress':
                            game_time = str(single_game['minute']) + "'"
                        else:
                            game_time = datetime.fromtimestamp(single_game['startTimestamp']).strftime("%H:%M")

                        streams.append({'links': self.get_links_from_site(links_link),
                                        'game': game_name,
                                        'time': game_time})

        return streams

#---------------------------------- NOW BOT FUNCTIONS ---------------------------------------------------------------------


    def start(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text='I find football streams.\n\nSend the name of a team or game to find a stream!')


    def display_links(self, update, context):  # displays links after keyboard selection
        # print('DisplayLinks started by: '+ update.message.from_user['first_name']+' '+update.message.from_user['last_name']+' @'+update.message.from_user['username'])
        self.hits += 1
        text = update.message.text
        output = ''
        for match in self.game_list:

            if text.lower() in match['game'].lower():  # compares input with matchname or team name
                output += ("\n\nMatch: " + match['game'] + '\n')
                output += ("Time: " + match['time'] + '\n\n\n')
                #print stream info in message
                for i in range(0, min(len(match['links']), 8)):
                    output += ("Stream Name: " + match['links'][i]['name'] + '\n')
                    output += ("Stream Link: " + match['links'][i]['link'] + '\n\n')
                #In case no streams found
                if (len(match['links'])) == 0:
                    output += 'No streaming links found for this match.\n\nMatch links usually appear 30 minutes before a match.'

        if output == '':
            context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Can't find a stream for that match/team.\nHere are the currently broadcasted matches:")
            self.display_streams(update, context)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text=output)
        # print("Links sent to: "+ update.message.from_user['first_name']+' '+update.message.from_user['last_name']+' @'+update.message.from_user['username'])

     # displays list of streams as menu
    def display_streams(self, update, context):
        self.hits += 1
        match_names = []
        context.bot.send_message(chat_id=update.effective_chat.id, text='Loading...')
        if self.game_list == []:
            context.bot.send_message(chat_id=update.effective_chat.id,
                             text='There are currently no matches being broadcasted.\n\nLinks usually start to appear 30 minutes before the match.')
            return
        for match in self.game_list:
            button = telegram.KeyboardButton(text=match['game'])

            match_names.append([button])

        MatchKeyboard = match_names
        reply_markup = telegram.ReplyKeyboardMarkup(MatchKeyboard, True, one_time_keyboard=True)
        context.bot.send_message(chat_id=update.effective_chat.id, text='Select a match: ', reply_markup=reply_markup)

    def in_line_query(self, update, context):
        self.hits += 1
        query = update.inline_query.query
        logger.debug('Inline mode activated.')
        results = []
        x = 0  # counter, unique id
        for match in self.game_list:
            output = ''

            if query.lower() in match['game'].lower():  # compares input with matchname or team name

                output += ("\n\nMatch: " + match['game'] + '\n')

                output += ("Time: " + match['time'] + '\n\n\n')

                for i in range(0, min(len(match['links']), 8)):
                    output += ("Stream Name: " + match['links'][i]['name'] + '\n')
                    output += ("Stream Link: " + match['links'][i]['link'] + '\n\n')

                if (len(match['links'])) == 0:
                    output += 'No streaming links found for this match.\n\n'

                results.append(InlineQueryResultArticle(id=x,
                                                        title=(match['game']),
                                                        input_message_content=InputTextMessageContent(output)))
                x += 1

        if results == []:
            for match in self.game_list:
                output = ''
                output += ("\n\nMatch: " + match['game'] + '\n')

                output += ("Time: " + match['time'] + '\n\n\n')

                for i in range(0, min(len(match['links']), 8)):
                    output += ("Stream Name: " + match['links'][i]['name'] + '\n')
                    output += ("Stream Link: " + match['links'][i]['link'] + '\n\n')

                if (len(match['links'])) == 0:
                    output += 'No streaming links found for this match.\n\n'

                results.append(InlineQueryResultArticle(id=x,
                                                        title=(match['game']),
                                                        input_message_content=InputTextMessageContent(output)))
                x += 1
        if results == []:
            output = ''
            output += ('No matches are currently being broadcasted.')
            output += ('\nStreaming links usually appear 30 minutes before a game.')
            results.append(InlineQueryResultArticle(id=x,
                                                    title=('No matches are currently being broadcasted.'),
                                                    input_message_content=InputTextMessageContent(output)))

        update.inline_query.answer(results)


    def update_database(self, frequency):

        while True:
            try:

                #SAVE AND LOAD STATISTICS
                try:
                    with open("stats.pickle", 'rb') as f:
                        saved_dict = pickle.load(f)
                except Exception as e:
                    logger.error("Could not read from stats.pickle.")
                    logger.error(e)
                    saved_dict = {}

                    saved_dict['day'] = datetime.now().day
                    saved_dict['day_hits'] = 0

                    saved_dict['week'] = datetime.now()
                    saved_dict['week_hits'] = 0

                    saved_dict['month'] = datetime.now()
                    saved_dict['month_hits'] = 0


                with open("stats.pickle", 'wb') as f:

                    if datetime.now() - saved_dict['week'] >= timedelta(days=7):
                        saved_dict['week_hits'] = self.hits
                        saved_dict['week'] = datetime.now()
                    else:
                        saved_dict['week_hits'] += self.hits

                    if datetime.now() - saved_dict['month'] > timedelta(days=30):
                        saved_dict['month_hits'] = self.hits
                        saved_dict['month'] = datetime.now()
                    else:
                        saved_dict['month_hits'] += self.hits

                    if datetime.now().day != saved_dict['day']:
                        saved_dict['day_hits'] = self.hits
                        saved_dict['day'] = datetime.now().day
                    else:
                        saved_dict['day_hits'] += self.hits
                    self.hits = 0

                    pickle.dump(saved_dict, f)

            except Exception as e:
                logger.error("Could not update stats.")
                logger.error(e)

            try:
                logger.debug("Attempting Database Update")
                tomorrow = datetime.now() + timedelta(hours=5)
                yesterday = datetime.now() - timedelta(hours=5)
                start_time = time.time()
                self.game_list = finder.get_stream_info()
                #self.game_list+= finder.get_stream_info(day="{:02d}".format(tomorrow.day),
                #                                             month="{:02d}".format(tomorrow.month))
                #self.game_list += finder.get_stream_info(day="{:02d}".format(yesterday.day),
                #                                         month="{:02d}".format(yesterday.month))
                for game in (finder.get_stream_info(day="{:02d}".format(tomorrow.day),
                                       month="{:02d}".format(tomorrow.month))) + finder.get_stream_info(day="{:02d}".format(yesterday.day),
                                                         month="{:02d}".format(yesterday.month)):
                    if game['game'] not in (existing_game['game'] for existing_game in self.game_list):
                        self.game_list.append(game)


                temp_list = []
                [temp_list.append(x) for x in self.game_list if x not in temp_list]
                self.game_list = temp_list
                logger.info("Time taken to update database: " + str((time.time() - start_time)/60))
                logger.info("Database updated.")
            except Exception as e:
                logger.error("Could not update database.")
                logger.error(e)

            time.sleep(frequency * 60)



    def start_database_updater(self):
        updater_thread = threading.Thread(target = self.update_database, args = ( UPDATE_FREQUENCY, ))
        updater_thread.start()


    def start_telegram_bot(self):
        #intialize updater
        updater = Updater(token=token, use_context=True)
        dispatcher = updater.dispatcher

        #start handler
        start_handler = CommandHandler('start', self.start)
        dispatcher.add_handler(start_handler)

        #find_stream handler for list of all games
        display_streams_handler = CommandHandler('findstream', self.display_streams)
        dispatcher.add_handler(display_streams_handler)

        #handler to display links for single game
        display_links_handler = MessageHandler(telegram.ext.Filters.text, self.display_links)
        dispatcher.add_handler(display_links_handler)
        updater.start_polling()

        #inline query handler
        in_line_query_handler = InlineQueryHandler(self.in_line_query)
        dispatcher.add_handler(in_line_query_handler)


'''
{'game': ,
'time': game_time,
'links': [{'name': , 'link': }]
}

'''
if __name__ == '__main__':
    logger.info("Program started.")
    #temporary game_list to check
    finder = StreamFinder([{'game': "Please Wait",
                            'time': '00"',
                            'links': [{'name': 'Bot is', 'link': 'starting up'}
                                      ]}])
    finder.start_telegram_bot()
    finder.start_database_updater()





