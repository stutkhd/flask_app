from flask import Flask, render_template, request
from config import CONFIG
from janome.tokenizer import Tokenizer
from janome.analyzer import Analyzer
from janome.tokenfilter import *
from requests_oauthlib import OAuth1Session
import json
import re
import neologdn
from bs4 import BeautifulSoup
import requests

#TwitterAPIの認証情報
consumer_key = CONFIG["CONSUMER_KEY"]
consumer_secret = CONFIG["CONSUMER_SECRET"]
access_token = CONFIG["ACCESS_TOKEN"]
access_token_secret = CONFIG["ACCESS_TOKEN_SECRET"]

twitter = OAuth1Session(consumer_key, consumer_secret, access_token, access_token_secret)

#最新のタイムラインを取得する
url = "https://api.twitter.com/1.1/statuses/user_timeline.json"


app = Flask(__name__)
@app.route("/", methods=["GET", "POST"])
def index():
    mg=[]
    if request.method=="POST":
        user_id = request.form["user_id"]
        print("user_id: ",user_id)

        twts = tweet(user_id)
        #存在しないアカウント
        if twts == 404:
            message = "このアカウントは存在しません"
            return render_template("index.html",message=message)
        #鍵垢
        elif twts == 401:
            message = "アカウントの鍵を外してから試してください"
            return render_template("index.html",message=message)
        #IDの入れ忘れ
        elif not user_id or " " in user_id :
            message = "IDが入力されていません"
            return render_template("index.html",message=message)
        else:
            #単語リスト
            t_words = nlp(twts)
            n = 0
            #一番多い単語
            most_word = t_words[n]
            lnkData = scraping(most_word)
            imglnk = img(lnkData)
            ttl = title(lnkData)
            #lnkDataが7個の時、検索画像がない
            while len(imglnk) == 7:
                n += 1
                most_word = t_words[n]
                lnkData = scraping(most_word)
                imglnk = img(lnkData)
                ttl = title(lnkData)
            print("t_words: ",t_words)
            #存在しないアカウント
            message = ""
            return render_template("index.html",imageLink=imglnk[0],top_1=most_word,message=message,user_id=user_id,title=ttl[0])
    else:
        mg.append("入力内容が間違っています")
        return render_template("index.html")

#user_idを取得しツイートを取得
def tweet(user_id):
    tweets=[]
    params = {"screen_name":user_id,"count":50,"include_rts":False}
    req = twitter.get(url, params=params)
    #tweetを初期化
    if tweets:
        tweets = []
    else:
        tweets = []

    if req.status_code == 200:
        timeline = json.loads(req.text)
        for tweet in timeline:
            tweets.append(tweet["text"])
        return tweets
    else:
         print("ERROR: %d" % req.status_code)
         return req.status_code

def nlp(tweets):
    string = "\n".join(tweets)

    def format_text(text):
        text=re.sub(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-…]+', "", text)#URL
        text=re.sub(r'[!-~]', "", text)
        text=re.sub(r'[︰-＠]', "", text)

        text = neologdn.normalize(text)

        text = text.lower()

        hira_stop = ["の","こと","ん","さ","そ","これ","こ","ろ"]
        for x in hira_stop:
            text = re.sub(x,"",text)
        return text

    normalized_string = format_text(string)
    token_filters = [POSKeepFilter('名詞'), TokenCountFilter()]
    a = Analyzer(token_filters=token_filters)
    words = list(a.analyze(normalized_string)) 
    top_pairs = sorted(words,key=lambda x:x[1], reverse=True)[:5] #dict
    top_words = list(map(lambda x:x[0], top_pairs))
    return top_words

#tp_wordを受け取りサイトのリンクデータを格納する関数
def scraping(tp_word):
    linkData = []
    url = "https://www.irasutoya.com/search?q="
    #tp_wordで検索したURL
    response = requests.get(url+tp_word)
    soup = BeautifulSoup(response.text, "lxml")
    links = soup.select("a")
    for link in links:
        href = link.get("href")
        #取得したリンクが画像リンクかどうか
        if re.search('irasutoya.*blog-post.*html$',href):
            #取得したリンクがlinkData[]にないか確認
            if not href in linkData:
                linkData.append(href)
    return linkData

def img(linkData):
    imageLinks = []
    for link in linkData:
        res = requests.get(link)
        soup = BeautifulSoup(res.text, "lxml")
        links = soup.select(".separator > a")
        for a in links:
            imageLink = a.get('href')
            imageLinks.append(imageLink)
    return imageLinks


def title(linkData):
    titles = []
    for link in linkData:
        res = requests.get(link)
        soup = BeautifulSoup(res.text, "lxml")
        h2_links = soup.select("#post > div.title > h2")
        for link in h2_links:
            title = link.text
            title = re.sub("\n", "", title)
            titles.append(title)
    return titles

app.run(port=12344, debug=True)
