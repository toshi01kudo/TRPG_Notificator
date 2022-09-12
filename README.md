# TRPG_Notificator
TRPG 関連情報を LINE に通知するための bot

## 仕組み
* 各カレンダーサイトへアクセスし、 Beautifulsoup にて解析。
* 必要情報を抜き出し、辞書型の変数を束ねたリストへ保存。
* 興味ある文言を含むイベントのみを抽出。
* LINE API へ送信。

## 使い方
本リポジトリから除外されている parameters.py に LINE の Token を指定する必要あり。
同じく同ファイルの `search_words`に興味ある文言をリストにして記載すると、GM、もしくは、タイトルから抽出してくれる。

## cron
下記のような `crontab.txt` を作成し、`crontab crontab.txt`で設定反映。\
環境に合わせて、Pathの修正が必要。`crontab -l`で現状の設定を確認可能。\
サーバ移管等でcrontabを削除する場合には、`crontab -e`で編集、もしくは、全て削除して問題無い場合は`crontab -r`で削除可能。
```
$ crontab -l
PYTHONPATH=/home/to-kudo/.local/lib/python3.8/site-packages

# Every morning
0 7 * * * python3 /home/to-kudo/TRPG_Notificator/TRPG_notificator.py
```

もし、タイムゾーンを変更した場合、cronの再起動が必要。
```
sudo timedatectl set-timezone Asia/Tokyo
sudo service cron restart
```

### 備忘録 - cronの実行タイミングメモ
下記の意味
```
# .---------------- minute (0 - 59)
# |  .------------- hour (0 - 23)
# |  |  .---------- day of month (1 - 31)
# |  |  |  .------- month (1 - 12) OR jan,feb,mar,apr ...
# |  |  |  |  .---- day of week (0 - 6) (Sunday=0 or 7) OR sun,mon,tue,wed,thu,fri,sat
  0  7  *  *  * python3 /home/to-kudo/TRPG_Notificator/TRPG_notificator.py
```

## Google spreadsheet連携
イベントリストをデータベースとしてGoogle spreadsheetに登録。
参加できないイベントについては通知不要 = Yes として登録可能。

## 細やかな備忘録
### LINE API Key
ここらへんに記載あり。
https://qiita.com/moriita/items/5b199ac6b14ceaa4f7c9#%E3%82%A2%E3%82%AF%E3%82%BB%E3%82%B9%E3%83%88%E3%83%BC%E3%82%AF%E3%83%B3%E3%81%AE%E7%99%BA%E8%A1%8C

LINE Notifyとのグループを作成し、そのグループ毎のトークンを発行する仕組み。
