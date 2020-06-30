
import requests
import threading
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pprint,logging, pickle, os, sys, platform

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

UPDATE_FREQUENCY = 1 #in minutes
OS = platform.system()
from AuthenticationInfo import *


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

        #for windows, need chromedriver.exe in same directory
        if OS == 'Windows':
            driver2 = webdriver.Chrome('./chromedriver.exe')

        #for linux
        #options = Options
        #options.headless = True
        #for linux, have to use deprecated method for some reason
        if OS == 'Linux':
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            driver2 = webdriver.Chrome(executable_path='/usr/bin/chromedriver', chrome_options=options)

        driver2.get(url)
        time.sleep(5)
        links = []
        #print(driver2.find_elements_by_class_name("stream-info"))
        i = 0
        for row in driver2.find_elements_by_class_name("stream-info"):
            #limit to 10 links per message
            if i < 10:
                link = (row.get_attribute("href"))
                link_name = row.find_element_by_class_name("first").text
                links.append({"name": link_name, "link": link})
                i += 1
        driver2.close()
        return links



    def get_stream_info(self):
        # for windows
        if OS == 'Windows':

            driver = webdriver.Chrome('./chromedriver.exe')

        #for linux:
        #options = Options
        #options.headless = True
        if OS == 'Linux':

            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            driver = webdriver.Chrome(executable_path='/usr/bin/chromedriver', chrome_options=options)

        url = "https://reddits.soccerstreams.net/home"

        driver.get(url)
        time.sleep(3)
        content = driver.find_elements_by_class_name('competition')
        
        streams = []
        for row in content:
            #print(row.find_element_by_class_name("name").text)
            names = row.find_elements_by_class_name("name")
            name1, name2 = names[0].text, names[1].text
            game_time = row.find_element_by_class_name("competition-cell-status").text
            #print(name1 + " vs " + name2 + " at " + game_time)

            link = row.find_element_by_tag_name('a').get_attribute('href')
            #print(link)
            if game_time not in ("CANCELED", "CANCELLED", "FULL TIME") and self.calculate_time_difference(game_time) < 2:

                streams.append({'game': name1 + " vs " + name2,
                                'time': game_time,
                                'links': self.get_links_from_site(link)})

        driver.close()

        return streams

#---------------------------------- NOW BOT FUNCTIONS ---------------------------------------------------------------------


    def start(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text='I find football streams.\n\nSend the name of a team or game to find a stream!')

       # logger.info("/start command invoked.")


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

    #displays list of streams as menu
    def display_streams(self, update, context):
        self.hits += 1
        MatchNames = []
        context.bot.send_message(chat_id=update.effective_chat.id, text='Loading...')
        if self.game_list == []:
            context.bot.send_message(chat_id=update.effective_chat.id,
                             text='There are currently no matches being broadcasted.\n\nLinks usually start to appear 30 minutes before the match.')
            return
        for match in self.game_list:
            button = telegram.KeyboardButton(text=match['game'])

            MatchNames.append([button])

        MatchKeyboard = MatchNames
        reply_markup = telegram.ReplyKeyboardMarkup(MatchKeyboard, True, one_time_keyboard=True)
        context.bot.send_message(chat_id=update.effective_chat.id, text='Select a match: ', reply_markup=reply_markup)

    def in_line_query(self, update, context):
        self.hits += 1
        query = update.inline_query.query
        logger.info('Inline mode activated.')
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

                self.game_list = finder.get_stream_info()



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
                            'time': '34"',
                            'links': [{'name': 'google', 'link': 'www.google.com'},
                                      {'name': 'google2', 'link': 'www.google.com'}]},
                           {'game': "Bot is loading matches",
                            'time': '67"',
                            'links': [{'name': 'test', 'link': 'www.gmail.com'},
                                      {'name': 'test2', 'link': 'www.gmail.com'}]}
                           ])
    finder.start_telegram_bot()
    finder.start_database_updater()




