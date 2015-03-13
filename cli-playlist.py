"""
This program creates Spotify playlists out of arbitrary text inputs
"""

__author__ = "Zachary Pustejovsky"

import re
import sys
import multiprocessing
import itertools
import time
from collections import defaultdict
from multiprocessing import Pool
from itertools import permutations
from datetime import datetime
import requests
import numpy as np


# FIX - PROMPT FOR CLIENT SECRET!!!!
# TEST SCRIPT WITH LETTER DISTANCES!!!  MAKE IT A COMMAND LINE OPTION

def levenshtein(s, t, word=False):
    """
    From Wikipedia article; Iterative with two matrix rows.
        Adapted slightly to work with words as well as characters
    """
    if word:
        s = s.split(' ')
        t = t.split(' ')
    if s == t: return 0
    elif len(s) == 0: return len(t)
    elif len(t) == 0: return len(s)
    v0 = [None] * (len(t) + 1)
    v1 = [None] * (len(t) + 1)
    for i in range(len(v0)):
        v0[i] = i
    for i in range(len(s)):
        v1[0] = i + 1
        for j in range(len(t)):
            cost = 0 if s[i] == t[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        for j in range(len(v0)):
            v0[j] = v1[j]
    return v1[len(t)]


def findMaxGram(query_list):
    """
    Find the maximum n-gram to search for via the API
    10 is a somewhat arbitrary number that i'm using to
        ensure that i dont query for overly-large n-grams
    Ideally this  would check for 3 SDs greater than average len of song,
        but i don't have query access to the entire DB of songs/features
    """
    if len(query_list) > 10:
        max_gram = 10
    else:
        max_gram = len(query_list)
    return max_gram


def queryCleaner(q):
    """
    Clean up the command line input to be more usable
    """
    # split query into list of lowercase words without punctuation
    qsplit = [stringScrunch(word) for word in q.lower().split(' ')]
    for word in qsplit:
        if word == '':
            del qsplit[qsplit.index('')]
    # recombine q with lowercase and scrunch
    q = ' '.join(qsplit)
    return q, qsplit


def permutationDistanceLooper(perm):
    """
    This is the function that map() performs at each iteration
    Must be in global environment
    Each iteration in this case is a perutation of song titles
    """
    # define q from the global env to be used in looper
    if sys.argv[1] == '-s':
        q = sys.argv[2]
    if sys.argv[1] == '-f':
        with open(sys.argv[2], 'r') as input:
            q = input.read()
            q = q.replace('\n', ' ').rstrip()
    qsplit = [stringScrunch(word) for word in q.lower().split(' ')]
    for word in qsplit:
        if word == '':
            del qsplit[qsplit.index('')]
    # recombine q with lowercase and scrunch
    q = ' '.join(qsplit)

    if len(perm) == 1:
        test_string = perm[0]
    else:
        test_string = ' '.join(perm[:len(perm)])
    dist = levenshtein(q, test_string)
    return dist, perm


def gen(at, max_p):
    """
    Defining generator object in global environment
    for use in parallel permutation looping with chunking
    """
    for prm in permutations(at, max_p):
        yield prm


def stringScrunch(s):
    """
    Keep only alphanumeric
    """
    delchars = ''.join(c for c in map(chr, range(256)) if not c.isalnum())
    return s.translate(None, delchars)


def ngrams(input, n):
    """
    Break a sentence into a list containing lists of
    word sequences of length n (n-gram)
    """
    input = input.split(' ')
    output = []
    for i in range(len(input)-n+1):
            output.append(input[i:i+n])
    return output


def uniquifyList(seq, idfun=None):
    """
    De-dupe a list while preserving order and output the IDs that are used 
    """ 
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    idxs = []
    for idx, item in enumerate(seq):
        marker = idfun(item)
        if marker in seen: continue
        seen[marker] = 1
        result.append(item)
        idxs.append(idx)
    return result, idxs


def songPermutationSearch(q_split, track_list, link_list):
    """
    Search through all candidate song recommendations
    search is parallelized across multiprocessing.cpu_count() cpus
    function times out and returns best guess after 2 minutes
    """
    # this is a little arbitrary, but we want to find permutations 
    # with no more than 1/3 as many songs as there are words
    # it is rounding up without importing extra modules
    max_permutations = int(len(q_split) / 3) + (len(q_split) % 3 > 0)
    # create pool object for multithreading
    pl = Pool(processes=None) # set None to use all available cores
    chunks = 101
    outputs = []
    start_time = datetime.now()
    print "Searching the songs for distance-minimizing permutations"
    # LOOP STARTING AT MAX PERMUTATIONS
    for i in range(max_permutations + 1)[1:]:
        go = gen(track_list, i)
        # kick off multithreading process
        while True:
            chunked_output = pl.map(permutationDistanceLooper, itertools.islice(go, chunks))
            if chunked_output:
                outputs.extend(chunked_output)
                tdelta = datetime.now() - start_time
                if tdelta.seconds > 120:
                    print "Search Timeout - 2 minutes"
                    break
            else:
                break
    distances = [output[0] for output in outputs]
    perms = [output[1] for output in outputs]
    perm = perms[np.argmin(distances)]
    links = [link_list[track_list.index(perm[i])] for i in range(len(perm))]
    final_levenshtein = distances[np.argmin(distances)]
    return perm, links, final_levenshtein


class ApiQueryPipeline(object):
    """
    Class for handling API queries and filtering for relevant information
    """
    def __init__(self, target_poem, client_secret):
        self.target_poem = target_poem
        self.client_secret = client_secret
        self.api_query_input = None
        self.request = None
        self.request_json = None
        self.tracks = None
        self.links = None
        self.lvsd = None
        self.min_tracks = None
        self.min_links = None
        self.link_idxs = None
        self.qsplit = None
        self.all_tracks = []
        self.all_links = []

    def _apiInitialize(self):
        """
        Method to initialize the Spotify search API
        """
        # Specify the API that is being called
        self.api = 'https://api.spotify.com/'
        # Specify the Action that needs to be performed
        self.action = 'v1/search'
        self.actiontype = '&type=track'
        
        # Create variables that are needed for the login request
        self.my_client_id = 'cabb734da9474e0099ac197a9e8ed5c7'
    
    def apiQuery(self):
        """
        Method to query the Spotify search API and return track names and links
        """
        query = '?q=' + '%20'.join(self.api_query_input) # double quotes yield an exact match
        full_query = self.api + self.action + query + self.actiontype
        request = requests.get(full_query)
        self.request = request
        return request

    def requestParser(self):
        """
        Method to retrieve the relevant json objects from the API request
        """
        if self.request is None:
            return
        # error handling in case the request came up empty
        try:
            self.request_json = self.request.json()['tracks']['items']
        except ValueError:
            return False
        if not self.request_json:
            return False

    def tracksAndLinks(self):
        """
        Method for extracting the necessary information from 
        JSON returned via Spotify API
        """
        if self.request_json is None:
            return
        page_iter = range(len(self.request_json))
        self.tracks = [self.request_json[i]['name'] for i in page_iter]
        self.links = [self.request_json[i]['external_urls']['spotify'] for i in page_iter]
        self.tracks = [track.lower() for track in self.tracks]
        pattern = re.compile('([^\s\w]|_)+')
        self.tracks = [pattern.sub('', track) for track in self.tracks]

    def levenshteinCheck(self):
        """
        Method for removing empty strings and finding the
        levenshtein distance between song titles and the query
        """
        if self.tracks is None:
            return
        ng = ' '.join(self.api_query_input)
        self.lvsd = []
        for track in self.tracks:
            current = track.split(' ')
            if '' in current:
                del current[current.index('')]
                self.tracks[self.tracks.index(track)] = ' '.join(current)
            # find levenshtein distance between trackname and ngram
            self.lvsd.append(levenshtein(ng, track))
        #return self.lvsd

    def levenshteinMinimize(self):
        """
        Method for finding the track(s) that minimize
        the levenshtein distance between the song title(s)
        and the query
        """
        if self.lvsd is None:
            return
        argmin = np.argmin(self.lvsd)
        self.min_tracks = self.tracks[argmin]
        self.min_links = self.links[argmin]
        #return self.min_tracks, self.min_links

    def run(self):
        """
        Run the ApiQueryPipeline for the given input string
        This will connect to the Spotify API and search for
        all n-grams (up to 10-grams) that can be made out of
        the input string, starting with the max n-gram.
        For each of the n-grams, it will find the song title
        (or titles) that is closest to the n-gram API query.
        """
        self._apiInitialize()
        q, self.qsplit = queryCleaner(self.target_poem)
        print "Collecting possible songs from the Spotify API"
        # start at MaxGram and work your way down
        n_list = range(findMaxGram(self.qsplit) + 1)[::-1][:-1]
        for n in n_list:
            ngram_list = ngrams(q, n)
            for ngram in ngram_list:
                # call pipeline methods
                # api_obj = ApiQueryPipeline(ngram)
                # api_obj.apiCaller()
                self.api_query_input = ngram
                self.apiQuery()
                self.requestParser()
                if self.request_json is None:
                    continue
                if not self.request_json:
                    continue
                self.tracksAndLinks()
                self.levenshteinCheck()
                self.levenshteinMinimize()
    
                # check if the resulting track is a list or a string
                if isinstance(self.min_tracks, (str, unicode)):
                    self.all_tracks.append(self.min_tracks)
                    self.all_links.append(self.min_links)
                else:
                    self.all_tracks.extend(self.min_tracks)
                    self.all_links.extend(self.min_links)

        self.all_tracks, self.link_idxs = uniquifyList(self.all_tracks)
        self.all_links = [self.all_links[i] for i in self.link_idxs]

def main(argv):
    """
    Command Line program to return tuples in the form of:
        (song_name, song_link)
    as well as the final minimized distance
    """
    # handle system arguments from command line
    if len(sys.argv) == 1:
        print "Please specify a valid string or file"

    if sys.argv[1] not in ['-s', '-f']:
        print """Please specify a valid argument:
        -s: string enclosed by quotes ''
        -f: text file"""
        sys.exit('Input Error')
    
    if sys.argv[1] == '-s':
        q = sys.argv[2]
    
    if sys.argv[1] == '-f':
        with open(sys.argv[2], 'r') as input:
            q = input.read()
            q = q.replace('\n', ' ').rstrip()

    client_secret = raw_input("""Please enter client secret for API access:
        """)
    apiQuery = ApiQueryPipeline(q, client_secret)
    apiQuery.run()
    
    perm, links, final_levenshtein = songPermutationSearch(
        apiQuery.qsplit,
        apiQuery.all_tracks,
        apiQuery.all_links)

    for key, track in enumerate(perm):
        print (track, links[key])
    print "Levenshtein distance between playlist and input:  " + str(final_levenshtein)


if __name__ == '__main__':
    main(sys.argv)