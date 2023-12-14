import requests
import logging
import datetime
import re
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from connect_gspread import connect_gspread
load_dotenv()

# Global parameter
mono_url = 'https://calendar.monodraco.com'
day_url = 'http://trpgtime.sakura.ne.jp/first/calendar/webcal.cgi'
day_short_url = 'http://trpgtime.sakura.ne.jp/first/calendar/'
SEARCH_WORDS = os.getenv('SEARCH_WORDS').split(',')


def main():
    # Logging 設定
    logging.basicConfig(level=logging.INFO,
                        format=' %(asctime)s - %(levelname)s - %(message)s')
    logging.info('#=== Start program ===#')

    # DayDreamやモノドラコから卓一覧をjson形式 or 辞書型で取得
    candidate_monod_event_list = get_info_from_monodraco()
    candidate_dayd_event_list = get_info_from_daydream()

    # 条件に合うものをリストアップ。
    event_list = search_event(candidate_monod_event_list) \
        + search_event(candidate_dayd_event_list)
    # 日付に合わせてsort
    sorted_list = sorted(event_list, key=lambda x: x['date'])

    # Google spreadsheetのこれまでの通知リストを取得
    jsonf = os.getenv('jsonfile')
    spread_sheet_key = os.getenv('spread_sheet_key')
    ws = connect_gspread(jsonf, spread_sheet_key, 'TRPG_event_list')
    updated_event_list = get_notified_list_gsheet(ws, sorted_list)

    # LINEに送信
    note_text = make_text(updated_event_list)  # リストは日付順に並べ替え
    for send_text in note_text:  # 送信文字数上限に合わせて分割して送信
        send_line_notify(send_text)
    gs_text = 'TRPGイベントリスト: https://docs.google.com/spreadsheets/d/' + \
        spread_sheet_key + '/edit?usp=sharing'
    send_line_notify(gs_text)

    logging.info('#=== Finish program ===#')


def get_notified_list_gsheet(ws, e_list):
    # 全ID取得
    # !!! 列数を6で計算してるため注意 !!! #
    logging.info('#=== Get list from gsheet ===#')
    logging.info('#=== NOTE: Number of columns are configured as 6. ===#')
    exist_gspread_array = ws.get_all_values()
    exist_gspread_cell_list = ws.range('A1:F' + str(len(exist_gspread_array)))

    # 新しい通知リストを作成
    new_gspread_array = []
    new_gspread_array.append(exist_gspread_array[0])
    for event in e_list:
        new_gspread_array.append([
            'No',
            event['date'],
            event['time'],
            event['title'] + event['GM'],
            event['rest_member'],
            event['url']
        ])

    # 今回の通知と新しい通知を比較
    for exist_event in exist_gspread_array:
        if exist_event[5] == '':
            break
        for new_event in new_gspread_array:
            if exist_event[5] == new_event[5]:
                new_event[0] = exist_event[0]
    # 新しいイベントリストの空白を埋める。
    new_blank_array = [['No']]
    new_blank_array[0].extend([''] * (len(new_gspread_array[0]) - 1))
    new_blank_array = new_blank_array * (len(exist_gspread_array) - len(new_gspread_array))
    new_gspread_array.extend(new_blank_array)

    # Google spreadsheetの通知リストを更新
    for i, cell in enumerate(exist_gspread_cell_list):
        cell.value = new_gspread_array[int(i / len(new_gspread_array[0]))][int(i % len(new_gspread_array[0]))]
    ws.update_cells(exist_gspread_cell_list)

    # 通知OFFを除いたリストを作成
    updated_all_event_list = ws.get_all_records()
    updated_event_list = []
    for event in updated_all_event_list:
        if event['不要'] == 'Yes':
            continue
        if event['date'] == '':
            break
        updated_event_list.append({
            'date': event['date'],  # 開催日
            'time': event['time'],  # 時間帯
            'GM': '',  # GM名は空白
            'title': event['title'],  # イベントタイトル, システム名等
            'rest_member': event['rest_member'],  # 残り募集人数
            'url': event['url']  # イベントURL
        })

    return updated_event_list


def get_mono_event_list(soup, event_list):
    # モノドラコのイベントをリストで返す関数

    # 構造はだいたいこんな感じだった。
    # date_lines = soup.select('.date_line')
    # date_lines: each date
    # date_lines[0].select('.card'): each event
    # date_lines[0].select('.card')[0].select('p')[0].text = '募集終了' or '中止' or '募集中'
    # date_lines[0].select('.card')[0].select('a')[0].select('.user h3')[0].text.replace('\n',''): GM
    # date_lines[0].select('.card')[0].select('a')[1].select('.game h4')[0].text.replace('\n',''): タイトル

    # cards = soup.select('.card')
    # cards: each event
    # cards[0].select('p')[0].text = '募集終了' or '中止' or '募集中'
    # cards[0].select('a')[0].select('.user h3')[0].text.replace('\n',''): GM
    # cards[0].select('a')[1].select('.game h4')[0].text.replace('\n',''): タイトル
    # cards[0].select('a')[1].select('.game ul li')[0].text: time '昼の部(11時〜17時)' or ...
    # cards[0].select('a')[1].select('.game ul li')[1].text: date '2021/12/01'

    for event in soup.select('.card'):
        temp_event = {
            'status': event.select('p')[0].text,
            'date': event.select('.game ul li')[1].text,  # 開催日
            'time': event.select('.game ul li')[0].text,  # 時間帯
            'GM': event.select('h3')[0].text.replace('\n', ''),  # GM名
            'title': event.select('h4')[0].text.replace('\n', ''),  # イベントタイトル, システム名等
            'rest_member': event.select('.game ul li')[5].text.replace('\n', ''),  # 残り募集人数
            'url': mono_url + event.select('a')[0].get('href')  # イベントURL
        }
        # logging.info('イベント: '+str(temp_event))
        Event_date = datetime.datetime.strptime(temp_event['date'], '%Y/%m/%d')
        if not temp_event['status'] == '募集中' or \
                Event_date.date() - datetime.date.today() < datetime.timedelta(days=0):
            # 募集中でない卓、過去日の卓なら処理しない。
            continue
        elif Event_date.date() - datetime.date.today() > datetime.timedelta(days=30):
            # 30日より先の日程なら検索を終了する。
            break
        temp_event['date'] = Event_date.strftime('%Y/%m/%d (%a)')
        event_list.append(temp_event)
    return event_list


def get_info_from_monodraco():
    # モノドラコから卓一覧をjson形式 or 辞書型で取得
    # logging.info('#=== Start monodraco function ===#')
    logging.info('#=== Get data from monodraco ===#')
    event_list = []

    # 今月の処理
    this_month_url = mono_url + '/schedules'
    soup = BeautifulSoup(requests.get(this_month_url).content, 'html.parser')
    # logging.info('今月: '+month)
    event_list = get_mono_event_list(soup, event_list)

    # 来月の処理
    next_month = (datetime.date.today().replace(day=1) + datetime.timedelta(days=31)).replace(day=1)
    # logging.info('来月: '+next_month.strftime('%Y-%m-%d'))
    next_month_url = this_month_url + '?month=' + next_month.strftime('%Y-%m-%d') + '-01+00%3A00%3A00+%2B0900'
    # logging.info('来月のURL: '+next_month_url)
    soup = BeautifulSoup(requests.get(next_month_url).content, 'html.parser')
    event_list = get_mono_event_list(soup, event_list)

    # logging.info('イベントリスト: '+str(event_list))
    return event_list


def get_day_event_list(soup, event_list, date):
    # daydreamのイベントをリストで返す関数
    # DayDreamカレンダーの日付・曜日抽出 正規表現
    day_date_regex = re.compile(r'(\d+)(\(.\))')

    # 構造はだいたいこんな感じだった。
    # each_event = soup.select('.color_normal_r')
    # 日付があるイベントの長さは7, 無いものは5か6。リストは基本的に後ろから参照する。
    # 長さが7 => 開催日: temp_date = each_event[0].select('td')[0].text.replace('\n', '')
    # 時間帯: each_event[0].select('td')[-4].text
    # イベントタイトル: each_event[0].select('td')[-1].text
    # 残り募集人数: each_event[0].select('td')[-2].textが空欄なら募集終了。

    for event in soup.select('.color_normal_r, .color_sat_r, .color_sun_r'):
        if len(event) == 15:
            regex_date = day_date_regex.search(event.select('td')[0].text.replace('\n', '')).group(1)
            Event_date = date.replace(day=int(regex_date))  # 日付のdate型変数
        if event.select('td')[-2].text == '':
            # 募集中でない卓なら処理しない。
            continue
        if Event_date - datetime.date.today() < datetime.timedelta(days=0):
            # 過去日の卓なら処理しない。
            continue
        elif Event_date - datetime.date.today() > datetime.timedelta(days=30):
            # 30日より先の日程なら検索を終了する。
            break
        temp_event = {
            'status': '募集中',
            'date': Event_date.strftime('%Y/%m/%d (%a)'),  # 開催日
            'time': event.select('td')[-4].text,  # 時間帯
            'GM': '',  # GM名は空欄とする
            'title': event.select('td')[-1].text.replace('\n', ''),  # イベントタイトル, システム名等
            'rest_member': '募集人数' + event.select('td')[-2].text,  # 残り募集人数
            'url': day_short_url + event.select('a')[-1].get('href')  # イベントURL
        }
        # logging.info('イベント: '+str(temp_event))
        event_list.append(temp_event)
    return event_list


def get_info_from_daydream():
    # DayDreamから卓一覧をjson形式 or 辞書型で取得
    # logging.info('#=== Start daydream function ===#')
    logging.info('#=== Get data from daydream ===#')
    event_list = []

    # 今月の処理
    this_month_url = day_url
    soup = BeautifulSoup(requests.get(this_month_url).content, 'html.parser')
    # logging.info('今月: '+month)
    event_list = get_day_event_list(soup, event_list, datetime.date.today())

    # 来月の処理
    next_month = (datetime.date.today().replace(day=1) + datetime.timedelta(days=31)).replace(day=1)
    # logging.info('来月: '+next_month.strftime('%Y-%m-%d'))
    next_month_url = day_url + '?year=' + str(next_month.year) + '&mon=' + str(next_month.month)
    # logging.info('来月のURL: '+next_month_url)
    soup = BeautifulSoup(requests.get(next_month_url).content, 'html.parser')
    event_list = get_day_event_list(soup, event_list, next_month)

    # logging.info('イベントリスト: '+str(event_list))
    return event_list


def search_event(candidate_event_list):
    # イベント候補からSEARCH_WORDSに該当するイベントを抽出する関数
    event_list = []
    for event in candidate_event_list:
        for search_word in SEARCH_WORDS:
            if search_word in event['title'] or search_word in event['GM']:
                event_list.append(event)
                break
    return event_list


def make_text(event_list):
    # LINE通知文を作る関数
    # 送信文字数上限が1000文字なので、800文字あたりで分割する。
    note_text = []
    note_text.append('おすすめのTRPG情報が' + str(len(event_list)) + '件あります。\n')
    n = 0
    for event in event_list:
        new_text = '--------\n'\
            + event['date'] + '\n' + event['time'] + '\n'\
            + event['title'] + event['GM'] + '\n'\
            + event['rest_member'] + '\n'\
            + event['url'] + '\n'
        if len(note_text[n]) < 800:
            note_text[n] = note_text[n] + new_text
        else:
            note_text.append(new_text)
            n = n + 1
    return note_text


def send_line_notify(notification_message):
    """
    LINEに通知する
    """
    line_notify_token = os.getenv('Token_key')
    line_notify_api = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {line_notify_token}'}
    data = {'message': f'message: {notification_message}'}
    requests.post(line_notify_api, headers=headers, data=data)


if __name__ == "__main__":
    main()
