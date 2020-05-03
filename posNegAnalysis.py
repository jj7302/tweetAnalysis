import warnings
import time
import datetime
warnings.filterwarnings("ignore") #ignore tweepy warning
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.sentiment.util import demo_liu_hu_lexicon
import requests
import json
import base64
nltk.download('vader_lexicon')

class TweetRetriever():
    def __init__(self):
        self.since_id = None #the largest id on last query, used to get most recent tweets
        self.max_id = None #the smallest id on last query, used to get tweets that are are older and older
        self.access_token = None
        self.base_url = 'https://api.twitter.com/'
        self.Authenticate()



    def Authenticate(self, client_key = 'KcOK0nl3NPnEpoySNON1M6Q9O', client_secret = 'it2tYQyo1HXXnS6nk15pDB3kjVfeBEYbzqKhver982cvMm6Zgp'):
        secret_key = '{}:{}'.format(client_key, client_secret).encode('ascii')
        encoded_key = base64.b64encode(secret_key)
        encoded_key = encoded_key.decode('ascii')

        auth_url = '{}oauth2/token'.format(self.base_url)

        auth_headers = {
            'Authorization': 'Basic {}'.format(encoded_key),
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }

        auth_data = {
            'grant_type': 'client_credentials'
        }

        auth_resp = requests.post(auth_url, headers=auth_headers, data=auth_data)

        self.access_token = auth_resp.json()['access_token']

    def getRecentTweets(self, query, fileName='', save=False, count=100, updateSinceId=False):


        tweet_search_headers = {
            'Authorization': 'Bearer {}'.format(self.access_token)
        }

        tweet_search_params = {
            'q': query + '-filter:retweets',
            'result_type': 'recent',
            'count': count,
            'tweet_mode': 'extended',
            'lang': 'en'
        }

        if self.since_id != None:
            tweet_search_params['since_id'] = self.since_id


        search_url = '{}1.1/search/tweets.json'.format(self.base_url)

        search_resp = requests.get(search_url, headers=tweet_search_headers, params=tweet_search_params)

        tweet_data = search_resp.json()

        #set since_id
        print(len(tweet_data['statuses']))
        print(updateSinceId)
        if len(tweet_data['statuses']) > 0 and updateSinceId == True:
            self.since_id = tweet_data['statuses'][0]['id']


        if save and fileName != '':
            with open(fileName, 'w') as outfile:
                json.dump(tweet_data, outfile)
        elif save and fileName == '':
            raise Exception('Filename to save to not specified')

        return tweet_data

    def getHistoricalTweets(self, query, fileName='', save=False, count=100, updateMaxId=False):
        tweet_search_headers = {
            'Authorization': 'Bearer {}'.format(self.access_token)
        }

        tweet_search_params = {
            'q': query + '-filter:retweets',
            'result_type': 'recent',
            'count': count,
            'tweet_mode': 'extended',
            'lang': 'en'
        }

        if self.max_id != None:
            tweet_search_params['max_id'] = self.max_id


        search_url = '{}1.1/search/tweets.json'.format(self.base_url)

        search_resp = requests.get(search_url, headers=tweet_search_headers, params=tweet_search_params)

        tweet_data = search_resp.json()

        # set max_id
        if len(tweet_data['statuses']) > 0 and updateMaxId == True:
            self.max_id = tweet_data['statuses'][len(tweet_data['statuses']) - 1]['id']

        if save and fileName != '':
            with open(fileName, 'w') as outfile:
                json.dump(tweet_data, outfile)
        elif save and fileName == '':
            raise Exception('Filename to save to not specified')

        return tweet_data


def open_json(filename):
    with open(filename) as json_file:
        return json.load(json_file)


class Tweet():
    def __init__(self, status, subject=''):
        self.completeResponse = status
        self.complete_text = ''
        self.retweet = False
        self.subject = subject

        #if status is a retweet
        if ('retweeted_status' in status):
            self.complete_text = status['retweeted_status']['full_text']
            self.retweet = True

        #if its not a retweet
        else:
            self.complete_text = status['full_text']

class TopicSentiment():
    def __init__(self, TweetJson, subject='None', limit=None):
        self.subject = subject
        self.limit = limit
        self.TweetList = self.create_tweet_list(TweetJson)
        self.tweetSentiments = []
        self.sentAnalyzer = SentimentIntensityAnalyzer()
        self.averageSentiment = 0

    # credit to Hutto, C.J. & Gilbert, E.E. (2014). VADER: A Parsimonious
    # Rule-based Model for Sentiment Analysis of Social Media Text. Eighth International
    # Conference on Weblogs and Social Media (ICWSM-14). Ann Arbor, MI, June 2014.

    def create_tweet_list(self, jsonResponse):
        all_tweets = []

        jResp = jsonResponse['statuses']
        if self.limit != None:
            jResp = jsonResponse['statuses'][0:self.limit]

        for status in jResp:
            all_tweets.append(Tweet(status, subject=self.subject))

        return all_tweets

    def analyze_tweets(self):
        for tweet in self.TweetList:
            self.tweetSentiments.append(self.sentAnalyzer.polarity_scores(tweet.complete_text))

        total_sentiment = 0
        for sent in self.tweetSentiments:
            total_sentiment += sent['compound']

        if len(self.tweetSentiments) > 0:
            self.averageSentiment = total_sentiment / len(self.tweetSentiments)
        else:
            self.averageSentiment = None

        print(self.subject + ': ' + str(self.averageSentiment))
        print('Number of Tweets: ' + str(len(self.tweetSentiments)))
        print('')


    def print_tweets(self):
        for tweet in self.TweetList:
            print(tweet.complete_text)

class AggregateSentiment():
    def __init__(self):
        self.agregated_sentiment = 0
        self.allAverageSentiments = []
        self.aggregateHistory = {}

    def add_sentiment(self, score, record=True):
        self.allAverageSentiments.append(score)
        if len(self.allAverageSentiments) > 0:
            self.agregated_sentiment = sum(self.allAverageSentiments) / len(self.allAverageSentiments)

        if record:
            self.aggregateHistory[datetime.datetime.now()] = self.agregated_sentiment



class CandidateAnalysis():
    def __init__(self, candidates):
        self.aggregateSentiments = {}
        self.candidateSentiments = {}
        self.tweetRetriever = TweetRetriever()
        self.candidates = candidates
        self.lastRequestTime = 0
        self.initial_sentiments()
        self.currentXcords = []
        self.currentYcords = []
        self.labels = []


    def refresh_tweets(self, retrievalMethod='Most Recent'):
        for candidateName in self.candidates:
            candidateJson = None
            if retrievalMethod == 'Most Recent':
                if candidateName == self.candidates[len(self.candidates) -  1]: #update the since id if its the last candidate
                    candidateJson = self.tweetRetriever.getRecentTweets(candidateName, updateSinceId=True)
                    print(self.tweetRetriever.since_id)
                else:
                    candidateJson = self.tweetRetriever.getRecentTweets(candidateName)

            elif retrievalMethod == 'Historical 7 Days':
                if candidateName == self.candidates[len(self.candidates) -  1]: #update the since id if its the last candidate
                    candidateJson = self.tweetRetriever.getHistoricalTweets(candidateName, updateMaxId=True)
                else:
                    candidateJson = self.tweetRetriever.getHistoricalTweets(candidateName)


            self.candidateSentiments[candidateName] = TopicSentiment(candidateJson, subject=candidateName)

    def initial_sentiments(self, batchesPerCandidate=10):
        for candidateName in self.candidates:
            self.aggregateSentiments[candidateName] = AggregateSentiment()

        for i in range(batchesPerCandidate):
            self.refresh_tweets(retrievalMethod='Historical 7 Days')
            self.analyze_candidates(record=False)

        for name in self.candidates:
            print(name + ' Total: ' + str(self.aggregateSentiments[name].agregated_sentiment))



    def update_sentiments(self):
        self.refresh_tweets()
        self.analyze_candidates()

    def analyze_candidates(self, record=True):
        for name in self.candidateSentiments.keys():
            self.candidateSentiments[name].analyze_tweets()
            if self.candidateSentiments[name].averageSentiment != None:
                self.aggregateSentiments[name].add_sentiment(self.candidateSentiments[name].averageSentiment, record=record)
            print(name + ' Total: ' + str(self.aggregateSentiments[name].agregated_sentiment))
            ###

    def run_analysis(self, frequency=1800):
        while True:
            self.update_sentiments()
            time.sleep(frequency)

    def get_plot_data(self, updateFrequency=600):
        allXCords = []
        allYCords = []
        labels = []
        if time.time() - self.lastRequestTime > updateFrequency:
            self.update_sentiments()
            for thing in self.aggregateSentiments.keys():
                xcords = []
                ycords = []
                history = self.aggregateSentiments[thing].aggregateHistory
                for point in history.keys():
                    xcords.append(point)
                    ycords.append(history[point])
                allXCords.append(xcords)
                allYCords.append(ycords)
                labels.append(thing)
            self.labels = labels
            self.currentXcords = allXCords
            self.currentYcords = allYCords
            self.lastRequestTime = time.time()

        return self.currentXcords, self.currentYcords, self.labels

#print(tweetsJson['statuses'][5].keys())
#sentiment2 = demo_liu_hu_lexicon(sentence, plot=False).... not very accurate

#trumpJson = open_json('dTrumpTweets.txt')
#print(trumpJson['statuses'][0]['id'])
#print(trumpJson['statuses'][80]['id'])
candidates = ['Donald Trump', 'Bernie Sanders', 'Joe Biden']
analysis = CandidateAnalysis(candidates)
x, y, label = analysis.get_plot_data()
print(x)
print(y)
print(label)
#analysis.run_analysis(frequency=60)





