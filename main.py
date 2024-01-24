import os
from flask import Flask, request, redirect, render_template
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import dotenv

dotenv.load_dotenv()

############################estado funcional#######################################
app = Flask(__name__)

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = "http://localhost:5000/callback"
SCOPE = "user-library-read playlist-modify-public user-top-read"

sp_oauth = SpotifyOAuth(client_id=CLIENT_ID,
                        client_secret=CLIENT_SECRET,
                        redirect_uri=REDIRECT_URI,
                        scope=SCOPE,
                        show_dialog=True,
                        cache_path="token.txt")


@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route('/')
def index():
    return redirect('/about')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/callback')
def callback():
    code = request.args.get('code')
    sp_oauth.get_access_token(code)
    return redirect('/create_playlist')


@app.route('/success')
def success():
    playlist_uri = request.args.get('playlist_uri', None)
    return render_template('success.html', playlist_uri=playlist_uri)


def get_known_artist_ids(sp):
    known_artist_ids = set()

    saved_tracks = sp.current_user_saved_tracks(limit=50)
    for item in saved_tracks['items']:
        known_artist_ids.add(item['track']['artists'][0]['id'])

    top_artists = sp.current_user_top_artists(limit=50)
    for artist in top_artists['items']:
        known_artist_ids.add(artist['id'])

    playlists = sp.current_user_playlists(limit=50)
    for playlist in playlists['items']:
        tracks = sp.playlist_tracks(playlist['id'])
        for item in tracks['items']:
            known_artist_ids.add(item['track']['artists'][0]['id'])

    return known_artist_ids

@app.route('/create_playlist')
def create_playlist():
    if not os.path.isfile("token.txt"):
        return redirect('/')

    with open("token.txt") as token_file:
        token_info = json.load(token_file)
    sp = spotipy.Spotify(auth=token_info['access_token'])

    known_artist_ids = get_known_artist_ids(sp)
    saved_tracks = sp.current_user_saved_tracks(limit=50)
    track_ids = [track['track']['id'] for track in saved_tracks['items']]
    artist_ids = [track['track']['artists'][0]['id'] for track in saved_tracks['items']]

    recommendations = sp.recommendations(seed_artists=artist_ids[:2], seed_tracks=track_ids[:3], limit=20)
    unique_tracks = []
    for track in recommendations['tracks']:
        if track['artists'][0]['id'] not in known_artist_ids:
            unique_tracks.append(track['id'])

    user_id = sp.current_user()['id']
    playlist_name = "Descobertas automatizadas"
    playlist_id = None
    description = "Bip bop bop bip"
    playlists = sp.current_user_playlists(limit=50)
    while playlists:
        for playlist in playlists['items']:
            if playlist['name'] == playlist_name and playlist['owner']['id'] == user_id:
                playlist_id = playlist['id']
                break
        if playlist_id:
            break
        if playlists['next']:
            playlists = sp.next(playlists)
        else:
            playlists = None
    if not playlist_id:
        print(f"Tentando criar playlist com nome: {playlist_name} e descrição: {description}")
        playlist = sp.user_playlist_create(user_id, playlist_name, collaborative=False, description=description)
        playlist_id = playlist['id']
        playlist_uri = playlist['uri']
        print(f'Nova playlist criada: {playlist_uri}')
    else:
        playlist = sp.playlist(playlist_id)
        playlist_uri = playlist['uri']
        print(f'URI da playlist existente: {playlist_uri}')
    if unique_tracks:
        sp.playlist_add_items(playlist_id, unique_tracks)
        
    return redirect(f'/success?playlist_uri={playlist_uri}')

if __name__ == "__main__":
    app.run(debug=True)