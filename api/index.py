import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Poll, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext, PollHandler, PollAnswerHandler, Dispatcher, MessageHandler, Filters, CallbackQueryHandler
from deta import Deta
import random
from typing import Union
from pydantic import BaseModel
import httpx
import logging
from fastapi import FastAPI
import time
import os

logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TOKEN')
DETA_TOKEN = os.environ.get('DETA_TOKEN')
app = FastAPI()
deta = Deta(DETA_TOKEN)
quiz_db = deta.Base("quiz")
quiz_user = deta.Base("quiz_user")
quiz_group = deta.Base("quiz_group")
quiz_private = deta.Base("quiz_private")

QUIZ_ENDED_MESSAGE = '''
The quiz has ended, you can send /quiz_stats to get the statistics for the quiz :)
'''

QUIZ_STATS_USERS = '''
{user_name} --- {user_answer} / {total_questions} </br>
'''

WELCOME_MESSAGE = '''Welcome <a href="tg://user?id={user_id}">{user_name}</a> to Quiz/Motivational Bot

To use this bot 
    - send /quiz to get a random quiz
    - send /motivation to get a random motivational quote

By default, the bot will send you a quiz and a motivational quote every day at 8:00 AM GMT+3.

For more info send /help

btw am an open source bot, you can find the source code here https://github.com/chapimenge3/quiz-motivational-bot/

Follow me on twitter <a href="https://twitter.com/chapimenge3">@chapimenge3</a>
Follow me on github <a href="https://github.com/chapimenge3">@chapimenge3</a>
Follow me on instagram <a href="https://instagram.com/chapimenge3">@chapimenge3</a>
Follow me on LinkedIn <a href="https://linkedin.com/in/chapimenge">@chapimenge</a>

Read my blog https://blog.chapimenge.com/
My website https://chapimenge.com/

Join My Telegram Channel https://t.me/codewizme
'''
# BUTTONS FOR THE QUIZ
BUTTON_TYPES_GLOBAL = [{"text": "Art and Literature", "callback_data": "arts_and_literature"},{"text": "Film and TV", "callback_data": "film_and_tv"},{"text": "Food and Drink", "callback_data": "food_and_drink"},{"text": "General Knowledge", "callback_data": "general_knowledge"},{"text": "Geography", "callback_data": "geography"},{"text": "History", "callback_data": "history"},{"text": "Music", "callback_data": "music"},{"text": "Science", "callback_data": "science"},{"text": "Society and Culture", "callback_data": "society_and_culture"},{"text": "Sport and Leisure", "callback_data": "sport_and_leisure"}]

# QUIZ_URL = "https://opentdb.com/api.php?amount=1&category=9&difficulty=easy&type=multiple"
MOTIVATIONAL_URL = 'https://zenquotes.io/api/quotes'

# OPTIONS FOR QUIZ API
EFFECTIVE_CHAT_ID = {}
CATEGORY_LIST = []
CATEGORIES = ''
LIMIT = 5
DIFFICULTY = 'easy'

# QUIZ LIST FROM API
QUIZZES = []

# QUIZ STATS
STAT_USERS = [] # THE USERS WHO ANSWERED THE QUIZ (username and score)
STAT_QUIZ = [] # THE QUIZ STATS(poll_id and answers)

# GETS UPDATED BUTTONS
def get_buttons(BUTTON_TYPES=BUTTON_TYPES_GLOBAL):
    BUTTONS = [[InlineKeyboardButton(BUTTON_TYPES[0]['text'], callback_data=BUTTON_TYPES[0]['callback_data']), InlineKeyboardButton(BUTTON_TYPES[1]['text'], callback_data=BUTTON_TYPES[1]['callback_data'])],
           [InlineKeyboardButton(BUTTON_TYPES[2]['text'], callback_data=BUTTON_TYPES[2]['callback_data']), InlineKeyboardButton(BUTTON_TYPES[3]['text'], callback_data=BUTTON_TYPES[3]['callback_data'])],
           [InlineKeyboardButton(BUTTON_TYPES[4]['text'], callback_data=BUTTON_TYPES[4]['callback_data']), InlineKeyboardButton(BUTTON_TYPES[5]['text'], callback_data=BUTTON_TYPES[5]['callback_data'])],
           [InlineKeyboardButton(BUTTON_TYPES[6]['text'], callback_data=BUTTON_TYPES[6]['callback_data']), InlineKeyboardButton(BUTTON_TYPES[7]['text'], callback_data=BUTTON_TYPES[7]['callback_data'])],
           [InlineKeyboardButton(BUTTON_TYPES[8]['text'], callback_data=BUTTON_TYPES[8]['callback_data']), InlineKeyboardButton(BUTTON_TYPES[9]['text'], callback_data=BUTTON_TYPES[9]['callback_data'])],
           [InlineKeyboardButton("Done", callback_data='done')]
            ]
    return BUTTONS

def get_quiz():
    '''
    This will get a list of quizzes from the API
    '''
    global QUIZZES
    QUIZ_URL_NEW = 'https://the-trivia-api.com/api/questions?'+'categories=' + CATEGORIES + '&limit=' + str(LIMIT) + '&difficulty=' + DIFFICULTY
    try:
        response = httpx.get(QUIZ_URL_NEW)
        if response.status_code == 200:
            QUIZZES = response.json()
            print(QUIZZES)
        return None
    except Exception as e:
        logger.error(e)


def get_motivational():
    '''
    This will get a random motivational quote from the API
    '''
    try:
        response = httpx.get(MOTIVATIONAL_URL)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logger.error(e)


class TelegramWebhook(BaseModel):
    update_id: int
    message: Union[dict, None] = None
    edited_message: Union[dict, None] = None
    channel_post: Union[dict, None] = None
    edited_channel_post: Union[dict, None] = None
    inline_query: Union[dict, None] = None
    chosen_inline_result: Union[dict, None] = None
    callback_query: Union[dict, None] = None
    shipping_query: Union[dict, None] = None
    pre_checkout_query: Union[dict, None] = None
    poll: Union[dict, None] = None
    poll_answer: Union[dict, None] = None
    my_chat_member: Union[dict, None] = None
    chat_member: Union[dict, None] = None
    chat_join_request: Union[dict, None] = None

    def to_json(self):
        '''
        Returns a JSON representation of the model
        '''
        data = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if value is None:
                continue
            data[key] = value

        return data


def waiter_wrapper(func):
    def wrapper(update: Update, context: CallbackContext):
        try:
            user = update.effective_chat or EFFECTIVE_CHAT_ID or update.effective_user or update.message.from_user
            msg = context.bot.send_message(
                chat_id=user.id,
                text="Please wait...",
            )
            func(update, context)
            context.bot.delete_message(
                chat_id=user.id,
                message_id=msg.message_id
            )
        except Exception as e:
            logger.error('Error happened in a Wrapper %s', e)
    return wrapper


@waiter_wrapper
def start(update: Update, context: CallbackContext):
    user = update.effective_chat or update.effective_user or update.message.from_user
    update.message.reply_html(WELCOME_MESSAGE.format(
        user_id=user.id, user_name=user.first_name))
    user = update.message.from_user.to_dict()
    user['key'] = str(user.get('id') or user.get('user_id'))
    if not quiz_user.get(user['key']):
        quiz_user.put(user)


def quiz_init(update: Update, context: CallbackContext):
    '''
    This function will initialize the quiz params
    '''
    global EFFECTIVE_CHAT_ID
    QUIZZES.clear()
    STAT_QUIZ.clear()
    STAT_USERS.clear()
    EFFECTIVE_CHAT_ID = update.effective_chat
    print("<<<----------")
    print(EFFECTIVE_CHAT_ID)
    print("<<<----------")
    user = EFFECTIVE_CHAT_ID.to_dict()
    print("<<<----------")
    print(update.message.from_user)
    user['key'] = str(user.get('id') or user.get('user_id'))
    user['data'] = []
    if user['type'] == 'group':
        if not quiz_group.get(user['key']):
            quiz_group.put(user)
        else:
            quiz_group.put(user)
    elif user['type'] == 'private':
        if not quiz_private.get(user['key']):
            quiz_private.put(user)
        else:
            quiz_private.put(user)
    else:
        pass
    # if type is group, stoe it in quiz group if not store it in private
    # change the key to the user id or group id
    #
    # user = update.message.from_user.to_dict()
    # user['key'] = str(user.get('id') or user.get('user_id'))
    # if not quiz_user.get(user['key']):
    #    quiz_user.put(user)

    context.bot.send_message(chat_id=user.get('id'), reply_markup=InlineKeyboardMarkup(
        get_buttons(BUTTON_TYPES_GLOBAL)), text='Please choose quiz type')


def quiz_difficulty(update: Update, context: CallbackContext):
    '''
    This function will initialize the quiz params for difficulty
    '''
    user = update.effective_chat or update.effective_user or update.message.from_user
    buttons = [[InlineKeyboardButton("Easy", callback_data='easy'), InlineKeyboardButton("Medium", callback_data='medium')],
               [InlineKeyboardButton("Hard", callback_data='hard')]
               ]
    context.bot.send_message(chat_id=user.id, reply_markup=InlineKeyboardMarkup(
        buttons), text='Please choose quiz difficulty')


def quiz_limit(update: Update, context: CallbackContext):
    '''
    This function will initialize the quiz params for limit
    '''
    user = update.effective_chat or update.effective_user or update.message.from_user
    buttons = [[InlineKeyboardButton("5", callback_data='5'), InlineKeyboardButton("10", callback_data='10')],
               [InlineKeyboardButton("15", callback_data='15'), InlineKeyboardButton(
                   "20", callback_data='20')],
               ]
    context.bot.send_message(chat_id=user.id, reply_markup=InlineKeyboardMarkup(
        buttons), text='Please choose the number of questions')


def quiz_selection(update: Update, context: CallbackContext):
    global CATEGORY_LIST, DIFFICULTY, CATEGORIES, LIMIT
    user = EFFECTIVE_CHAT_ID
    query = update.callback_query.data
    selection_message_type = update.callback_query.message.text
    if selection_message_type == 'Please choose quiz type':
        if query == 'done':
            update.callback_query.answer()
            CATEGORIES = (',').join(CATEGORY_LIST)
            context.bot.delete_message(
                chat_id=user.id,
                message_id=update.callback_query.message.message_id
            )
            return quiz_difficulty(update, context)
        elif query in CATEGORY_LIST:
            button = next(
                (button for button in BUTTON_TYPES_GLOBAL if button["callback_data"] == query), None)
            button['text'] = button['text'].replace('✅ ', '')
            update.callback_query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(get_buttons(BUTTON_TYPES_GLOBAL)))
            CATEGORY_LIST.remove(query)
        else:
            button = next(
                (button for button in BUTTON_TYPES_GLOBAL if button["callback_data"] == query), None)
            button['text'] = '✅ ' + button['text']
            update.callback_query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(get_buttons(BUTTON_TYPES_GLOBAL)))
            CATEGORY_LIST.append(query)
        update.callback_query.answer()
    if selection_message_type == 'Please choose quiz difficulty':
        update.callback_query.answer()
        context.bot.delete_message(
            chat_id=user.id,
            message_id=update.callback_query.message.message_id
        )
        DIFFICULTY = query
        return quiz_limit(update, context)
    if selection_message_type == 'Please choose the number of questions':
        update.callback_query.answer()
        context.bot.delete_message(
            chat_id=user.id,
            message_id=update.callback_query.message.message_id
        )
        LIMIT = query
        get_quiz()
        return start_quiz(update, context)


@waiter_wrapper
def start_quiz(update: Update, context: CallbackContext):
    global CATEGORIES, QUIZZES
    if len(QUIZZES) != 0:
        logger.info('Quiz started')
        quiz = QUIZZES
        options = []
        print(quiz[0]['correctAnswer'])
        print('-----------')
        options.append(quiz[0]['correctAnswer'])
        for option in quiz[0]['incorrectAnswers']:
            options.append(option)
        open_time = {
            'hard': 90,
            'medium': 60,
            'easy': 45,
        }
        random.shuffle(options)
        correct = options.index(quiz[0]['correctAnswer'])
        user = EFFECTIVE_CHAT_ID
        stat = context.bot.send_poll(
            chat_id=user.id,
            question=quiz[0]['question'],
            type=Poll.QUIZ,
            allows_multiple_answers=False,
            options=options,
            correct_option_id=correct,
            protect_content=True,
            is_anonymous=False,
            explanation=f'Correct Answer: {quiz[0]["correctAnswer"]}',
            open_period=open_time.get(DIFFICULTY, 60),
        )
        options.clear()
        #quiz_db.delete()
        STAT_QUIZ.append({"poll_id": stat.poll.id, "time": open_time.get(DIFFICULTY, 60), "answer": stat.poll.correct_option_id})
        QUIZZES.pop(0)
        if len(QUIZZES) == 0:
            return context.bot.send_message(chat_id=user.id,text=QUIZ_ENDED_MESSAGE)


def continue_quiz(update: Update, context: CallbackContext):
    '''
    HANDLER TO CONTINUE A QUIZ THAT HASN'T BEEN FINISHED
    - UPDATES THE SCORE OF USERS AS WELL THAT HAS BEEN PASSED
      THROUGH THE UPDATE
    '''
    # if type is group, stoe it in quiz group if not store it in private
    # change the key to the user id or group id
    #
    # user = update.message.from_user.to_dict()
    # user['key'] = str(user.get('id') or user.get('user_id'))
    # if not quiz_user.get(user['key']):
    #    quiz_user.put(user)
    update_user = update.poll_answer
    user = next((user for user in STAT_USERS if user["username"] == update_user.user.username), None)
    poll = [poll for poll in STAT_QUIZ if poll["poll_id"] == update_user.poll_id][0]

    if user == None:
        score = 0
        if poll['answer'] == update_user.option_ids[0]:
            score = 1
        STAT_USERS.append({"username": update_user.user.username, "score": score})
    else:
        if poll['answer'] == update_user.option_ids[0]:
            user["score"] += 1

    if EFFECTIVE_CHAT_ID['type'] == 'private' and len(QUIZZES) != 0:
        return start_quiz(update, context)
    return 0


@waiter_wrapper
def start_motivation(update: Update, context: CallbackContext):
    logger.info('Motivation started')
    motivation = get_motivational()
    quote = random.choice(motivation)
    user = user = update.effective_chat or update.effective_user or update.message.from_user
    context.bot.send_message(
        chat_id=user.id,
        text=quote['q'] + '\n\n' + quote['a'],
    )
    return 0


@waiter_wrapper
def help(update: Update, context: CallbackContext):
    user = update.effective_chat or update.effective_user or update.message.from_user
    update.message.reply_html(WELCOME_MESSAGE.format(
        user_id=user.id, user_name=user.first_name))


@waiter_wrapper
def stats(update: Update, context: CallbackContext):
    res = quiz_user.fetch()
    all_items = res.items
    while res.last:
        res = quiz_user.fetch(last=res.last)
        all_items += res.items

    text = 'Total users: {}\n\n'.format(len(all_items))
    update.message.reply_text(text)


@waiter_wrapper
def quiz_stats(update: Update, context: CallbackContext):
    '''
    RETURNS THE QUIZ STATS OF THE CURRENT QUIZ, SORTED ON
    THE SCORE OF THE USERS
    '''
    txt = []
    num = 1
    STAT_USERS.sort(key=lambda x: x.get('score'), reverse=True)

    title = f'🏆 Top results in the quiz\n'
    questions = f'🖊 {LIMIT} questions'
    time_for_one = f'⏱ {STAT_QUIZ[0]["time"]} seconds per question'
    num_people_answered_quiz = f'🤓 {len(STAT_USERS)} took the quiz\n'
    txt.extend([title, questions, time_for_one, num_people_answered_quiz])

    for user in STAT_USERS:
        text = f'{num}. @{user["username"]} --- {user["score"]} / {LIMIT}'
        num += 1
        txt.append(text)
    update.message.reply_text(('\n').join(txt))


def register_dispatcher(dispatcher: Dispatcher):
    dispatcher.add_handler(PollAnswerHandler(continue_quiz))
    dispatcher.add_handler(PollHandler(start_quiz))
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("quiz",quiz_init))  # start_quiz
    dispatcher.add_handler(CommandHandler("motivation", start_motivation))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("stats", stats))
    dispatcher.add_handler(CommandHandler("quiz_stats", quiz_stats))
    dispatcher.add_handler(MessageHandler(Filters.text, start))
    dispatcher.add_handler(CallbackQueryHandler(quiz_selection))


def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # register dispatcher
    register_dispatcher(dispatcher)

    updater.start_polling()
    updater.idle()


@app.get("/")
def index():
    return {"message": "Hello World"}


@app.post("/webhook")
def webhook(our_update: TelegramWebhook):
    bot = Bot(TOKEN)
    update = Update.de_json(our_update.to_json(), bot)
    dispatcher = Dispatcher(bot, None)

    register_dispatcher(dispatcher)

    dispatcher.process_update(update)
    return {"message": "ok"}


@app.get('/api/cron')
def send_motivation():
    users = quiz_user.fetch()
    all_users = users.items
    while users.last:
        users = quiz_user.fetch(last=users.last)
        all_users += users.items

    motivation = get_motivational()

    bot = Bot(TOKEN)
    count = 0
    for user in all_users:
        try:

            rand_motivation = random.choice(motivation)
            bot.send_message(
                chat_id=int(user['key']),
                text=rand_motivation['q'],
            )
            count += 1
            if count == 30:
                time.sleep(1)
                count = 0

        except:
            pass

    return {"message": "ok"}


#if __name__ == '__main__':
#    main()
