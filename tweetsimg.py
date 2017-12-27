# -*- coding:utf-8 -*-
import shutil
import time
import os
import requests
import json
import datetime
import sys
import argparse
from multiprocessing.dummy import Pool


class tweetimg(object):
    def __init__(self):
        self.oauth = "https://api.twitter.com/oauth2/token"
        self.statuses = "https://api.twitter.com/1.1/statuses/user_timeline.json"
        self.lastid = None
        self.flag = 0
        self.count = 1

    def authtoken(self, apifile):
        # get api info
        f = open(apifile, "rb")
        api = json.loads(f.read())
        consumer_key = api["consumer_key"]
        consumer_secret = api["consumer_secret"]
        # auth token
        # https://dev.twitter.com/oauth/application-only
        host = self.oauth
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}
        auth = (consumer_key, consumer_secret)
        data = {'grant_type': 'client_credentials'}
        r = requests.post(host, headers=headers, auth=auth, data=data)

        if r.status_code == 200:
            token = json.loads(r.text)["access_token"]
            return token
        else:
            return False

    def getid(self, token, user, exclude_replies, include_rts, maxid=None, count=200):
        # check max_id
        # https://dev.twitter.com/rest/reference/get/statuses/user_timeline
        # https://dev.twitter.com/rest/public/timelines
        host = self.statuses
        headers = {"Authorization": "Bearer " + token}
        params = {"screen_name": user, "count": count,
                  "exclude_replies": exclude_replies, "include_rts": include_rts}
        if maxid:
            params["max_id"] = maxid
        r = requests.get(host, headers=headers, params=params, timeout=30)
        if r.status_code == 200:
            user_tweets = json.loads(r.text)
            self.flag = self.flag + 1
            if self.flag > self.count:
                return []
            else:
                print "Received %s responses" % len(user_tweets)
                if maxid:
                    return user_tweets[1:]
                else:
                    return user_tweets

    def __dformat(self, dates):
        dateformat = datetime.datetime.strptime(
            dates, '%a %b %d %H:%M:%S +0000 %Y')
        dateformat = str(dateformat)
        darray = time.strptime(dateformat, "%Y-%m-%d %H:%M:%S")
        dformats = time.strftime("%Y%m%d%H%M%S", darray)
        return dformats

    def getimgurl(self, token, user, exclude_replies, include_rts):
        imgs = []
        # traversal maxid
        tweets = self.getid(token, user, exclude_replies,
                            include_rts, self.lastid)
        while len(tweets) > 0:
            for t in tweets:
                try:
                    imgdict = {}
                    entities = t["extended_entities"]["media"]
                    createdat = self.__dformat(t["created_at"])
                    imgdict["date"] = createdat
                    temp = []
                    for media in entities:
                        temp.append(media["media_url_https"])
                    imgdict["urls"] = temp
                    imgs.append(imgdict)
                    self.lastid = t["id"]
                    if t["user"]["statuses_count"] < 3300:
                        self.count = (t["user"]["statuses_count"] / 200) + 2
                    else:
                        self.count = 20
                except:
                    pass
            tweets = self.getid(token, user, exclude_replies,
                                include_rts, self.lastid)
        return imgs

    def __downloadcore(self, paras):
        imgpath = paras[0]
        url = paras[1]
        try:
            r = requests.get(url + ":orig", stream=True, timeout=30)
            with open(imgpath, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
        except:
            print "Read timed out. [ Retry ]"
            self.__retry(imgpath, url)

    def __retry(self, imgpath, url):
        r = requests.get(url + ":orig", stream=True, timeout=30)
        with open(imgpath, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)

    def getimg(self, imgurl, save_path):
        imgnames = []
        imgurls = []
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        for i in imgurl:
            times = i["date"]
            urls = i["urls"]
            for u in urls:
                imgname = os.path.join(
                    save_path, times + "_" + u.split("/")[-1])
                imgnames.append(imgname)
                imgurls.append(u)
        print "With pictures: %s " % len(imgurls)
        print "Downloing..."
        pool = Pool(50)
        pool.map(self.__downloadcore, zip(imgnames, imgurls))
        pool.close()
        pool.join()



def opts():
    parser = argparse.ArgumentParser(description = "Twitter Image Download.")
    parser.add_argument('-u',dest='userid',help="screen name [@twitter]",required=True)
    parser.add_argument('-c',dest='apifile',help="APIdatas.json",required=True)
    parser.add_argument('-s',action='store_true',dest="ret",default=False,help="exclude retweets and replies")
    args = parser.parse_args()
    return args


def main():
    paras = opts()
    userid = paras.userid
    apifile = paras.apifile
    savepath = userid + "_" + time.strftime("%Y%m%d%H%M%S")
    if paras.ret:
        exclude_replies = True
        include_rts = False
    else:
        exclude_replies = False
        include_rts = True

    t = tweetimg()
    token = t.authtoken(apifile)
    if token:
        imgs = t.getimgurl(token, userid, exclude_replies, include_rts)
        t.getimg(imgs, savepath)
        raw_input("Press Enter to exit.")
    else:
        print "Bad Authentication."


if __name__ == "__main__":
    main()
