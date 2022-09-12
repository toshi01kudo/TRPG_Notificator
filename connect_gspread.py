import gspread

#ServiceAccountCredentials：Googleの各サービスへアクセスできるservice変数を生成します。
from oauth2client.service_account import ServiceAccountCredentials 

def connect_gspread(jsonf,key,sheet):
    #2つのAPIを記述しないとリフレッシュトークンを3600秒毎に発行し続けなければならない
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    #ダウンロードしたjsonファイル名をクレデンシャル変数に設定（秘密鍵、Pythonファイルから読み込みしやすい位置に置く）
    credentials = ServiceAccountCredentials.from_json_keyfile_name(jsonf, scope)
    #OAuth2の資格情報を使用してGoogle APIにログインします。
    gc = gspread.authorize(credentials)
    #共有設定したスプレッドシートキーを変数[SPREADSHEET_KEY]に格納する。
    SPREADSHEET_KEY = key
    #共有設定したスプレッドシートのシート3を開く
    worksheet = gc.open_by_key(SPREADSHEET_KEY).worksheet(sheet)
    return worksheet
