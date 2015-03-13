# spotify-playlist-poems
Program to create Spotify playlists out of poems.

In order to run this program, you will need Python 2.7.8 installed, as well as the external libraries NumPy (pip install numpy) and Requests (pip install requests).

Example Usage:
	
	python cli-playlist.py -s "If I can't let it go out of my mind."

	python cli-playlist.py -f test-data/red-wheelbarrow.txt

# My Approach:

# High-Level Process:

# Notes on Implementation:
* strings - "running" versus "runnin" was handled by using levenshtein stringdist instead of worddist, but this will make "text" appear in lieu of "test" in some cases, as i am minimizing the string-based levenshtein distance