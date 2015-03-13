# spotify-playlist-poems
Program to create Spotify playlists out of poems.

In order to run this program, you will need Python 2.7.8 installed, as well as the external libraries NumPy (pip install numpy) and Requests (pip install requests).

Example Usage:
	
	python cli-playlist.py -s "If I can't let it go out of my mind."

	python cli-playlist.py -f test-data/red-wheelbarrow.txt

Once a command has been run, the program will ask you to input the client secret for API access.  This will be provided to anyone who wishes to run this program.

# My Approach:
I decided to treat this assignment as an optimization problem with a clearly defined search-space (all spotify songs titles) and an objective that must be minimized.  I chose [Levenshtein Distance](http://en.wikipedia.org/wiki/Levenshtein_distance) as my objective similarity function.

# High-Level Process:
At a high level, my program works as follows:
1) Find all possible n-grams (or all n-grams up to an 8-gram depending on how long the input poem is) that can be made with the input poem.
2) For each n-gram starting with the max n-gram, query the search API and return the information for whichever song (or songs) has the lowest Levenshtein distance from the query.
3) Remove duplicate song titles from the vector of returned songs.
4) For each possible permutation of returned, de-duped song titles, calculate the Levenshtein distance from the permutation to the input poem.
5) Return the permutation of song titles that minimizes the Levenshtein distance.  This permutation is the optimal playlist.

# Notes on Implementation:
* Due to the time constraint, my optimization efforts were focused mainly on the piece of the program that searches the space of song permutations.  I parallelized this process (threads=#CPUs) and added functionality to let the process time out after 2 minutes and return the 'best effort' result.  Given more time, I would work to optimize/parallelize the API queries as well.
* Due to the fact that a string distance metric was used, the resulting playlist will occasionally return songs that have words that were not in the input poem (e.g. "live" instead of "love").  My distance function has an option that allows you to find word-distances instead of just string-distances, however the string distances seemed to return better results overall so I decided not to use this option.  This does mean that the program effectively matches colloquial language to the input (e.g. "running" can match with "runnin").
* Another implication of the string distance approach is that there will occasionally be unmatched words in the resulting playlist.  Given more time, I would either implement logic to minimize this occurence or I would include something like word-level Hamming distance in the objective function.
* I tested more complex minimization objectives, such as functions of both string distance AND number of tracks, however these didn't perform quite as well.  I decided to avoid instances of one-word songs ("if", "I", "can't", etc...) by setting the maximum number of songs to be equal to 1/3 the number of words in the input poem.