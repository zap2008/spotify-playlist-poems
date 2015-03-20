# Spotify Playlist Poems
Inspired by [this tumblr page](http://spotifypoetry.tumblr.com/) ,this repository lays out a program to create Spotify playlists out of poems.

In order to run this program, you will need Python 2.7.8 installed, as well as the external libraries [NumPy](http://www.numpy.org/) (pip install numpy) and [Requests](http://docs.python-requests.org/en/latest/) (pip install requests).

Example Usage:
	
	python cli-playlist.py -s "If I can't let it go out of my mind."

	python cli-playlist.py -f test-data/red-wheelbarrow.txt

## My Approach:
I decided to treat this as an optimization problem with a clearly defined search-space (all spotify songs titles) and an objective that must be minimized.  I chose [Levenshtein Distance](http://en.wikipedia.org/wiki/Levenshtein_distance) as my objective similarity function.  The reason I chose this method is that it lets us find an objectively "best" solution out of a set of candidate solutions as determined by a commonly-used similarity metric.  I also wanted the program to _always_ return a "best" match, no matter what words are in the input poem.  As long as at least one of the n-grams in the poem returns a song from the search API, this program will return a playlist.

## High-Level Process:
At a high level, my program works as follows:

1. Find all possible n-grams (or all n-grams up to an 8-gram depending on how long the input poem is) that can be made with the input poem.
2. For each n-gram starting with the max n-gram, query the search API and return the information for whichever song (or songs) has the lowest Levenshtein distance from the query.
3. Remove duplicate song titles from the vector of returned songs.
4. For each possible permutation of returned, de-duped song titles, calculate the Levenshtein distance from the permutation to the input poem.
5. Return the permutation of song titles that minimizes the Levenshtein distance.  This permutation is the optimal playlist.

## Notes on Implementation:
* My optimization efforts were focused mainly on the piece of the program that searches the space of song permutations (step 5 above).  I parallelized this process and added functionality to let the process time out after 2 minutes and return the 'best effort' result.  In the future, I will work to optimize/parallelize the API queries as well. I chose to spend time optimizing the song permutation search for the following reason:
  * For any input poem, there are 1/2 * _x_ (_x_ + 1) possible n-grams, where _x_ is the number of words in the poem.
  * However, there are _y_! possible song permuations, where _y_ is the number of candidate songs for the playlist.
  * [As can be seen here](http://www.wolframalpha.com/input/?i=x%21+and+x*%28x%2B1%29%2F2), the number of possible song permutations will almost always be greater than the number of possible n-gram API queries for input poems with more than two words (two words allows for three n-grams and therefore up to three songs).
* Due to the fact that a string distance metric was used, the resulting playlist will occasionally return songs that have words that were not in the input poem (e.g. "live" instead of "love").  My distance function has an option that allows you to find word-distances instead of just string-distances, however the string distances seemed to return better results overall so I decided not to use this option.  This does mean that the program effectively matches colloquial language to the input (e.g. "running" can match with "runnin").
* Another implication of the string distance approach is that there will occasionally be unmatched words in the resulting playlist.  In the future, I will either implement logic to minimize this occurence or I will include something like word-level [Hamming Distance](http://en.wikipedia.org/wiki/Hamming_distance) in the objective function.
* I tested more complex minimization objectives, such as functions of both string distance AND number of tracks, however these didn't perform quite as well.  I decided to avoid instances of one-word songs ("if", "I", "can't", etc...) by setting the maximum number of songs to be equal to 1/3 the number of words in the input poem.  This served the dual function of keeping the playlist short and reducing the possible search-space of song title permutations.
* The relevant informaiton from each potential song is cached in-memory so that I can quickly return the URL of the optimal permutation/playlist without hitting the API again.