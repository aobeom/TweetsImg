## TweetsImg
You can download images(orig) uploaded by specific twitter users.

PS: only return up to [3200](https://dev.twitter.com/rest/reference/get/statuses/user_timeline) of a user’s most recent Tweets.

### Usage

Go to [Twitter Developer](https://dev.twitter.com/) and get your API key and API secret.

Modify the contents of the "APIdatas.json".

```python
python2 tweetsimg.py -u screen_name -c APIdatas.json
```

### Reference 

[morinokami](https://github.com/morinokami/twitter-image-downloader)  
[tweepy](https://github.com/tweepy/tweepy)