

import threading
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pickle, os, sys, platform

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
logger.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

from AuthenticationInfo import *

# how much to wait between database updates
UPDATE_FREQUENCY = 1 #in minutes

#if the league contains this word, it will be added to database (does not have to be a league name, can be a team name)
TEAM_LIST = ['manchester', 'liverpool', 'leicester', 'chelsea', 'wolve', 'arsenal', 'tottenham', 'burnley',
             'sheffield', 'everton', 'crystal palace', 'newcastle', 'southampton', 'brighton', 'west ham',
             'watford', 'aston villa', 'bournemouth', 'norwich',
             'bayern', 'borussia', 'leipzig', 'dortmund',
             'milan', 'inter', 'juventus', 'napoli', 'roma',
             'psg', 'paris', 'monaco', 'lyon',
             'barcelona', 'madrid', 'sevilla',
             ]
OS = platform.system()




class StreamFinder:

    def __init__(self, game_list = []):
        self.game_list = game_list
        self.hits = 0

        if OS == 'Windows':
            self.chromeoptions = webdriver.ChromeOptions()
            #self.chromeoptions.add_argument("headless")
            self.chromeoptions.add_argument("--window-size=1920,1080")
            self.chromeoptions.add_argument('--no-proxy-server')
            self.chromeoptions.add_argument("--proxy-server='direct://'")
            self.chromeoptions.add_argument('--proxy-bypass-list=*')
            self.chromeoptions.add_argument("user-data-dir=./cookies/")
            #self.driver = webdriver.Chrome('./chromedriver.exe', chrome_options=self.chromeoptions)

        if OS == 'Linux':
            self.chromeoptions = webdriver.ChromeOptions()
            self.chromeoptions.add_argument('--no-sandbox')
            self.chromeoptions.add_argument('headless')
            self.chromeoptions.add_argument('--disable-dev-shm-usage')
            self.chromeoptions.add_argument("--window-size=1920,1080")
            self.chromeoptions.add_argument('--no-proxy-server')
            self.chromeoptions.add_argument("--proxy-server='direct://'")
            self.chromeoptions.add_argument('--proxy-bypass-list=*')
            self.chromeoptions.add_argument("user-data-dir=./cookies/")
            #self.driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', chrome_options=self.chromeoptions)

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

        # #for windows, need chromedriver.exe in same directory
        # if OS == 'Windows':
        #     options = webdriver.ChromeOptions()
        #     options.add_argument('headless')
        #     driver2 = webdriver.Chrome('./chromedriver.exe', chrome_options=options)
        #
        # if OS == 'Linux':
        #     options = webdriver.ChromeOptions()
        #     options.add_argument('--no-sandbox')
        #     options.add_argument('headless')
        #     options.add_argument('--disable-dev-shm-usage')
        #     driver2 = webdriver.Chrome(executable_path='/usr/bin/chromedriver', chrome_options=options)

        try:
            logger.debug("Trying to open URL for one match")
            self.driver.get(url)
            logger.debug("Opened URL for one match")
            links = []
            #print(driver2.find_elements_by_class_name("stream-info"))
            i = 0
            for row in self.driver.find_elements_by_class_name("stream-info"):
                #limit to 10 links per message
                if i < 12:
                    link = (row.get_attribute("href"))
                    link_name = row.find_element_by_class_name("first").text
                    links.append({"name": link_name, "link": link})
                    i += 1
            #driver2.close()

            if links == []:
                links.append({"name": "Highlights link", "link" : url})
        except Exception as e:
            logger.error("Could not get info from URL of one match")
            logger.error(e)
            links.append({"name": "You can find links here", "link" : url})
            #driver2.close()
        return links



    def get_stream_info(self):
        if OS == 'Windows':
            self.driver = webdriver.Chrome(executable_path='./chromedriver.exe', chrome_options=self.chromeoptions)
        if OS == 'Linux':
            self.driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', chrome_options=self.chromeoptions)
        self.driver.implicitly_wait(5)
        logger.debug("Chrome opened")
        url = "https://reddits.soccerstreams.net/home"
        streams = []
        self.driver.get(url)
        logger.debug("Main URL loaded")

        # COMMENTED CODE BELOW HAS BEEN DEPRECATED
        #find all leagues
        # leagues = driver.find_elements_by_class_name("top-tournament")
        # for league in leagues:
        #     #only select leagues in our list
        #     if any(word in league.text.lower() for word in LEAGUE_LIST):
        #         games = league.find_elements_by_class_name('competition')
        #         logger.debug("Went through main page")


        games = self.driver.find_elements_by_class_name('competition')

        for single_game in games:
            #Check if the team is in the team list
            if any(word in single_game.text.lower() for word in TEAM_LIST):
            #check is there are current streams available from the main page itself, only proceed if there are
                status = single_game.find_element_by_class_name("competition-cell-status-name")
                if status.text:

                    names = single_game.find_elements_by_class_name("name")
                    name1, name2 = names[0].text, names[1].text
                    game_time = single_game.find_element_by_class_name("competition-cell-status").text

                    link = status.find_element_by_tag_name('a').get_attribute('href')
                    #if game_time not in ("CANCELED", "CANCELLED", "FULL TIME") and self.calculate_time_difference(game_time) < 2:
                    #above if statement is no longer needed as we only browse for matches with links
                    streams.append({'game': name1 + " vs " + name2,
                                    'time': game_time,
                                    'links': link})
                    logger.debug("Got info for one match")

        #driver.close()

        for row in streams:
            try:
                row['links'] = self.get_links_from_site(row['links'])
            except Exception as e:
                row['links'] = [{'name':'List of Links', 'link': row['links']}]
                logger.error("Could not add stream links to stream list.")
                logger.error(e)

        self.driver.close()

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
                    output += 'No streaming links found for this match.\n\n'

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
                    saved_dict = {}

                    saved_dict['day'] = datetime.now()
                    saved_dict['day_hits'] = 0

                    saved_dict['week'] = datetime.now()
                    saved_dict['week_hits'] = 0

                    saved_dict['month'] = datetime.now()
                    saved_dict['month_hits'] = 0



                with open("stats.pickle", 'wb') as f:

                    if datetime.now() - saved_dict['week']  > timedelta(days=7):
                        saved_dict['week_hits'] = self.hits
                    else:
                        saved_dict['week_hits'] += self.hits
                    if datetime.now() - saved_dict['month'] > timedelta(days=30):
                        saved_dict['month_hits'] = self.hits
                    else:
                        saved_dict['month_hits'] += self.hits
                    if datetime.now() - saved_dict['day'] > timedelta(days=1):
                        saved_dict['day_hits'] = self.hits
                    else:
                        saved_dict['day_hits'] += self.hits
                    self.hits = 0

                    pickle.dump(saved_dict, f)

            except Exception as e:
                logger.error("Could not update stats.")
                logger.error(e)

            try:
                logger.debug("Attempting Database Update")
                start_time = time.time()
                self.game_list = finder.get_stream_info()
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





