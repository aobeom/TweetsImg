# -*- coding:utf-8 -*-
import argparse
import datetime
import json
import multiprocessing
import os
import shutil
import sys
import time
from multiprocessing.dummy import Pool

import requests

try:
    import queue
except ImportError:
    import Queue as queue



class tweetimg(object):
    def __init__(self, limit, maxid):
        self.limit = limit
        self.lastid = maxid

        self.id = 0
        self.flag = 0
        self.count = 1

    def __dformat(self, dates):
        dateformat = datetime.datetime.strptime(
            dates, '%a %b %d %H:%M:%S +0000 %Y')
        dateformat = str(dateformat)
        darray = time.strptime(dateformat, "%Y-%m-%d %H:%M:%S")
        dformats = time.strftime("%Y%m%d%H%M%S", darray)
        return dformats

    def getToken(self, apikeys):
        # auth api
        oauth_host = "https://api.twitter.com/oauth2/token"
        # get api info
        with open(apikeys, "rb") as f:
            api = json.loads(f.read())
        consumer_key = api["consumer_key"]
        consumer_secret = api["consumer_secret"]
        # auth token
        # https://dev.twitter.com/oauth/application-only
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        }
        auth_info = (consumer_key, consumer_secret)
        auth_data = {'grant_type': 'client_credentials'}
        res = requests.post(oauth_host, headers=headers, auth=auth_info, data=auth_data)
        if res.status_code == 200:
            res_json = json.loads(res.text)
            token = res_json["access_token"]
            return True, token
        else:
            return False, res.status_code

    def __getID(self, token, user, exclude_replies, include_rts, maxid):
        # check max_id
        # https://dev.twitter.com/rest/reference/get/statuses/user_timeline
        # https://dev.twitter.com/rest/public/timelines
        statuses_host = "https://api.twitter.com/1.1/statuses/user_timeline.json"
        headers = {"Authorization": "Bearer " + token}
        params = {"screen_name": user, "count": self.limit,
                  "exclude_replies": exclude_replies, "include_rts": include_rts}
        if maxid:
            params["max_id"] = maxid
        res = requests.get(statuses_host, headers=headers, params=params, timeout=30)
        if res.status_code == 200:
            user_tweets = json.loads(res.text)
            self.flag = self.flag + 1
            if self.flag > self.count:
                return []
            else:
                print("Received %s responses" % len(user_tweets))
                return user_tweets

    def getImgURL(self, token, user, exclude_replies, include_rts):
        img_urls = []
        # traversal maxid
        tweets = self.__getID(token, user, exclude_replies,
                            include_rts, self.lastid)
        while len(tweets) > 0:
            for t in tweets:
                imgdict = {}
                if "extended_entities" in t:
                    entities = t["extended_entities"]["media"]
                    createdat = self.__dformat(t["created_at"])
                    imgdict["date"] = createdat
                    temp = []
                    for media in entities:
                        if "video_info" in media:
                            videos = media["video_info"]
                            variants = videos["variants"]
                            bitrate = [i["bitrate"] for i in variants if i.get("bitrate")]
                            bitrate = max(bitrate)
                            for v in variants:
                                if "bitrate" in v:
                                    if v["bitrate"] == bitrate:
                                        temp.append(v["url"])
                        else:
                            temp.append(media["media_url_https"])
                    imgdict["urls"] = temp
                    img_urls.append(imgdict)
                    if t["id"] != self.lastid:
                        self.id = t["id"]
                else:
                    self.id = t["id"]
            if self.limit < 200:
                return img_urls
            else:
                if t["user"]["statuses_count"] < 3300:
                    self.count = (t["user"]["statuses_count"] / 200) + 2
                else:
                    self.count = 20
                tweets = self.__getID(
                    token, user, exclude_replies, include_rts, self.id)
        return img_urls

    def __downloadcore(self, paras):
        imgpath = paras[0]
        url = paras[1]
        if url.split(".")[-1] == "mp4":
            url = url
        else:
            url = url + ":orig"
        try:
            r = requests.get(url, stream=True, timeout=30)
            with open(imgpath, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
        except BaseException:
            print("Read timed out. [ Retry ]")
            self.__retry(imgpath, url)

    def __retry(self, imgpath, url):
        if url.split(".")[-1] == "mp4":
            url = url
        else:
            url = url + ":orig"
        r = requests.get(url, stream=True, timeout=30)
        try:
            with open(imgpath, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
        except BaseException:
            print("[{}] Failed.".format(url))

    def getImg(self, imgurl, save_path, thread):
        img_names = []
        img_urls = []
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        for i in imgurl:
            times = i["date"]
            urls = i["urls"]
            for u in urls:
                img_name = os.path.join(
                    save_path, times + "_" + u.split("/")[-1].split("?")[0])
                img_names.append(img_name)
                img_urls.append(u)
        print("With pictures: %s " % len(img_urls))
        print("Downloing...")
        # pool = Pool(thread)
        # pool.map(self.__downloadcore, zip(img_names, img_urls))
        # pool.close()
        # pool.join()
        t = threadProcBar(self.__downloadcore, list(zip(img_names, img_urls)), thread)
        t.worker()
        t.process()


def opts():
    parser = argparse.ArgumentParser(description="Twitter Image Download.")
    parser.add_argument('-u', dest='userid',
                        help="screen name [@twitter]", required=True)
    parser.add_argument('-c', dest='apikeys',
                        help="apikeys.json", required=True)
    parser.add_argument('-s', action='store_true', dest="ret",
                        default=False, help="exclude retweets and replies")
    parser.add_argument('-l', dest='limit', default=200, type=int,
                        help="[default: 200] specifies the number of Tweets to try and retrieve, up to a maximum of 200 per distinct request.")
    parser.add_argument(
        '--id', dest='maxid', default=None, type=int, help="[default: first id] returns results with an ID less than or equal to the specified ID")
    args = parser.parse_args()
    return args


def main():
    paras = opts()
    userid = paras.userid
    apikeys = paras.apikeys
    limit = paras.limit
    maxid = paras.maxid
    savepath = userid + "_" + time.strftime("%Y%m%d%H%M%S")
    if paras.ret:
        exclude_replies = True
        include_rts = False
    else:
        exclude_replies = False
        include_rts = True

    t = tweetimg(limit, maxid)
    status, token = t.getToken(apikeys)
    if status:
        img_urls = t.getImgURL(token, userid, exclude_replies, include_rts)
        thread = len(img_urls)
        if thread > 200:
            thread = 24
        elif 100 <= thread <= 200:
            thread = 16
        elif 50 <= thread < 100:
            thread = 8
        else:
            thread = 4
        t.getImg(img_urls, savepath, thread)
    else:
        print("[{}] Bad Authentication.".format(token))


class threadProcBar(object):
    def __init__(self, func, tasks, pool=multiprocessing.cpu_count()):
        self.func = func
        self.tasks = tasks

        self.bar_i = 0
        self.bar_len = 50
        self.bar_max = len(tasks)

        self.p = Pool(pool)
        self.q = queue.Queue()

    def __dosth(self, percent, task):
        if percent == self.bar_max:
            return True
        else:
            self.func(task)
            return percent

    def worker(self):
        process_bar = '[' + '>' * 0 + '-' * 0 + ']' + '%.2f' % 0 + '%' + '\r'
        sys.stdout.write(process_bar)
        sys.stdout.flush()
        pool = self.p
        for i, task in enumerate(self.tasks):
            try:
                percent = pool.apply_async(self.__dosth, args=(i, task))
                self.q.put(percent)
            except BaseException:
                break

    def process(self):
        pool = self.p
        while 1:
            result = self.q.get().get()
            if result == self.bar_max:
                self.bar_i = self.bar_max
            else:
                self.bar_i += 1
            num_arrow = int(self.bar_i * self.bar_len / self.bar_max)
            num_line = self.bar_len - num_arrow
            percent = self.bar_i * 100.0 / self.bar_max
            process_bar = '[' + '>' * num_arrow + '-' * \
                num_line + ']' + '%.2f' % percent + '%' + '\r'
            sys.stdout.write(process_bar)
            sys.stdout.flush()
            if result == self.bar_max-1:
                pool.terminate()
                break
        pool.join()
        self.__close()

    def __close(self):
        print('')


if __name__ == "__main__":
    main()
