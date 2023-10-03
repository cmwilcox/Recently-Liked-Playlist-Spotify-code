from flask import Flask, request, url_for, session, redirect
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import time
import datetime



app = Flask(__name__)


app.secret_key = "write write some hard to guess password here"
app.config['SESSION_COOKIE_NAME'] = 'My Cookie'

@app.route('/')
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    print(auth_url)
    return redirect(auth_url)

@app.route('/authorize')
def authorize():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect("/modifyPlaylist")

@app.route('/logout')
def logout():
    for key in list(session.keys()):
        session.pop(key)
    return redirect('/')

@app.route('/modifyPlaylist')
def modiifyPlaylist():
    
    #Make sure access token is valid
    session['token_info'], authorized = get_token()
    session.modified = True
    if not authorized:
        return redirect('/')
    sp = spotipy.Spotify(auth=session.get('token_info').get('access_token'))

    recent_liked_songs_playlist_id = None
    user_id = sp.current_user()['id']

    #finds Recently liked playlist
    current_playlists = sp.current_user_playlists()['items']
    for playlist in current_playlists:
        if (playlist['name'] == "Recently Liked Songs"):
            recent_liked_songs_playlist_id = playlist["id"]

    #creates playlist if not already made
    if not recent_liked_songs_playlist_id:
        new_playlist = sp.user_playlist_create(user_id, "Recently Liked Songs", True)
        recent_liked_songs_playlist_id = new_playlist['id']

    current_day = datetime.date.today()
    still_new_songs = True
    offset_value = 0
    song_uris = []

    #Loops through user's liked tracks adding ones that are newer than 30 days old
    #Loop stops when a song older than 30 days is found
    while still_new_songs:
        track_list = sp.current_user_saved_tracks(limit=50,offset=offset_value) #Can only load 50 songs per request so songs must be loaded iteratively
        for track in track_list['items']:
            #Creates date object for when the song was added
            year = int(track['added_at'][0:4])
            month = int(track['added_at'][5:7])
            day = int(track['added_at'][8:10])
            date_added = datetime.date(year=year,month=month,day=day)
            
            #checks if the song is was added less than 30 days ago
            less_than_30_days = ((current_day-date_added).days < 30)
            
            if less_than_30_days:
                song_uris.append(track["track"]["uri"])
            else:
                still_new_songs = False
                break
        offset_value += 50 #changes value to load next 50 songs

    #replaces playlist with whatever songs where added to the list
    sp.user_playlist_replace_tracks(user=user_id,playlist_id=recent_liked_songs_playlist_id,tracks=song_uris)

    return "Successfully Added Songs"

def get_token():
    token_valid = False
    token_info = session.get("token_info", {})

    #Checks if the session already has token stored
    if not (session.get('token_info', False)):
        token_valid= False
        return token_info, token_valid
    
    #Checks if token has expired
    now = int(time.time())
    is_expired = session.get('token_info').get('expires_at') - now < 60
    
    #Refreshes token if expired
    if is_expired:
        sp_oauth = create_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(session.get('token_info').get('refresh_token'))
    
    token_valid = True
    return token_info, token_valid

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id = "paste_client_id_here",
        client_secret = "paste_client_secret_here",
        redirect_uri=url_for('authorize', _external=True),
        scope='user-library-read user-library-read playlist-modify-public playlist-modify-private'
    )




app.run(debug=True)