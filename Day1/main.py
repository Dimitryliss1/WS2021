import bot_creator
import pymorphy2
import pandas as pd
import re
import difflib
import os
import enchant

# Чтобы не палить ключ API. Вместо этой строки напишите bot = telebot.TeleBot("APIKEY", parse_mode=None)
# А сверху -- import telebot
bot = bot_creator.bot_creator()
started = 0 # Запущен ли бот
file_to_search = 0 # Датасет, по которому будет производиться поиск
state = 0 # Состояние бота
morph = pymorphy2.MorphAnalyzer() # Анализатор для перевода в именительный падеж
res = 0 # Результат, чтобы можно было использовать в различных функциях одно значение

categories = {
    'пол': ['ламинат', 'паркет', 'линолеум', 'коврик', 'ковёр', 'пол', 'карпет', 'ковролин', 'палас', 'плинтус'],
}

members = { # Членами каких категорий являются те или иные слова
    'ламинат': 'пол',
    'паркет': 'пол',
    'линолеум': 'пол',
    'коврик': 'пол',
    'ковёр': 'пол',
    'карпет': 'пол',
    'ковролин': 'пол',
    'палас': 'пол',
    'плинтус': 'пол',
}


def correctWord(w: str): # Коррекция ошибок
    dictionary = enchant.Dict("ru_RU")
    sim = dict()
    if not dictionary.check(w): # Если слова нет в словаре, то проверяем на ошибки
        suggestions = set(dictionary.suggest(w)) # Предложения по исправлению вместе с вероятностями

        for word in suggestions:
            measure = difflib.SequenceMatcher(None, w, word).ratio()
            sim[measure] = word

        word = sim[max(sim.keys())] # Получение самого вероятного исправленного слова
        return word
    else:
        return w


def search_thru_dataset(searchPlace: pd.DataFrame, query: str): # Поиск по датасету
    global morph
    query = re.split(r'\W', query) # Делим по всем небуквенным элементам
    keywords = []
    for i in range(0, len(query)):
        query[i] = morph.parse(query[i])[0]
        if 'NOUN' in query[i].tag:
            tmp = query[i].normal_form # Переводим в Именительный падеж и проверяем на орфографию
            tmp = correctWord(tmp)
            keywords.append(tmp)
    res = []
    print(keywords)
    a = set(keywords)
    for k in set(keywords): # Расширение сета, если слово -- название категории
        if k in categories.keys():
            for t in categories[k]:
                a.add(t)
    print(a)

    for i in range(0, len(searchPlace.values)): # итерации по датасету
        broken = False
        tmp = searchPlace.iloc[i]
        tmp_names = re.split(r'\W', searchPlace.Name[i]) # Разделение имени по небуквенным символам
        for word in range(0, len(tmp_names)):
            tmp_names[word] = morph.parse(tmp_names[word])[0].normal_form  #Перевод каждого слова в начальную форму
        for word in a:
            for word_tmp in tmp_names:
                if word in word_tmp:
                    res.append(tmp) # Если слово из поискового запроса входит в имя, то добавить в выдачу, выход во избежание повторов
                    broken = True
                    break
            if broken:
                break
    return res


@bot.message_handler(commands=['start']) # Запуск бота
def run(message):
    global started, file_to_search
    if not started:
        bot.reply_to(message, "Привет! Я могу помочь найти подходящие материалы в магазине.\n"
                              "Чтобы найти товар, напишите /find\n")
        file_to_search = pd.read_csv("PickedKBestNonLabeled.csv")
        started = 1
    else:
        bot.reply_to(message, "Бот уже запущен!")


@bot.message_handler(commands=['find']) # Запуск режима поиска
def start_search(message):
    global state, started
    if started == 1:
        if state == 0:
            bot.reply_to(message, "Что бы Вы хотели найти?\n"
                                  "Все слова, кроме существительных не будут участвовать в выдаче\n"
                                  "Чтобы остановить режим поиска, напишите /back")
            state = 1
        elif state == 1:
            bot.reply_to(message, "Поиск уже запущен\n"
                                  "Если надо остановить, напишите /back")
    else:
        bot.reply_to(message, "Я еще не запущен. Запустите с помощью команды /start")


@bot.message_handler(commands=['back']) # Возврат в меню
def revert(message):
    global state
    if state == 0:
        bot.reply_to(message, "Некуда возвращаться")
    elif state == 1:
        bot.reply_to(message, "Отмена поиска")
        state = 0
    elif state == 2:
        bot.reply_to(message, "Возвращаемся в главное меню.\n"
                              "/find, чтобы что-то найти")
        state = 0
    elif started == 0:
        bot.reply_to(message, 'Я не готов к работе. Запустите с помощью /start')


@bot.message_handler(commands=['give']) # Выдача сводки поискового запроса
def send_result(message):
    global state
    global res
    if state == 2:
        tmp = pd.DataFrame(columns=res[0].index)
        for i in res:
            tmp = tmp.append(i)
        tmp.to_excel('result.xlsx')
        if os.path.getsize('result.xlsx') < 49*(1024**2):
            f = open("result.xlsx", "rb")
            bot.send_document(message.chat.id, f)
            f.close()
        else:
            bot.send_message(message.chat.id, "Невозможно получить всю выборку, результат больше 50 МБ.")
        os.remove('result.xlsx')
        bot.send_message(message.chat.id, "/find, чтобы начать новый поисковой запрос")
        state = 0
    elif started == 0:
        bot.reply_to(message, 'Я не готов к работе. Запустите с помощью /start')
    elif state != 2:
        bot.send_message(message.chat.id, "Эта команда используется только после поиска.")


@bot.message_handler(commands=['help']) # Помощь
def showHelp(message):
    bot.send_message(message.chat.id, "Список доступных команд\n"
                                      "/help -- Вывод помощи\n"
                                      "/start -- Начало работы с ботом\n"
                                      "/find -- Запуск режима поиска\n"
                                      "/back -- Возврат в главное меню\n"
                                      "/give -- Получить всю поисковую выдачу\n"
                                      "(/give работает только после выдачи поискового запроса)")


@bot.message_handler(content_types='text') # Если сообщение без команд
def handle_text(message):
    global state
    if state == 1: # Ожидается поисковой запрос
        bot.reply_to(message, f"Выполняется поиск")
        global res
        res = search_thru_dataset(file_to_search, message.text.lower())
        if len(res) == 0:
            bot.send_message(message.chat.id, "Ничего не найдено. Попробуйте изменить запрос\n"
                                              "Или напишите /back")
        else:
            bot.send_message(message.chat.id, f"Найдено {len(res)} результатов. Показаны "
                                              f"{'первые 10' if len(res) > 10 else f'все {len(res)}'} результатов "
                                              f"по возрастанию цены")
            res.sort(key= lambda x: x.Price)
            for i in res[:10]:
                bot.send_message(message.chat.id, f"{i['Name'].strip()}, цена: {i['Price']} руб.")
            res_categories = []
            for i in re.split(r'\W', message.text.lower()):
                i = morph.parse(i)[0]
                if 'NOUN' in i.tag:
                    tmp = i.normal_form
                    tmp = correctWord(tmp)
                    if tmp in members.keys():
                        res_categories.append(members[tmp])
            if len(res_categories) != 0:
                bot.send_message(message.chat.id, "Некоторые слова из Вашего запроса принадлежат к категориям ниже. "
                                                  "Если хотите произвести поиск по всей категории, вбейте название этой"
                                                  " категории в поисковой запрос.")
                for i in res_categories:
                    bot.send_message(message.chat.id, i)
            bot.send_message(message.chat.id, "Для получения всех результатов запроса "
                                              "с подробными характеристиками напишите '/give'.\n"
                                              "Или /back, чтобы вернуться.")
            state = 2
    elif started == 0:
        bot.reply_to(message, 'Я не готов к работе. Запустите с помощью /start')
    elif state == 2:
        bot.send_message(message.chat.id, 'Напишите /back, чтобы вернуться в главное меню')
    else:
        bot.reply_to(message, "Не понимаю Вас.\nВойдите в режим поиска с помощью /find")


bot.polling(none_stop=True)
