from plexapi.server import PlexServer
from typing import List
import os
import logging
from ..models import Artist
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class PlexService:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token

    def get_music_library(self):
        """Get the music library section from Plex"""
        server = PlexServer(self.base_url, self.token)
        return server.library.section('Music')

    def get_all_artists(self) -> List[Artist]:
        """Get all artists from the music library"""
        try:
            server = PlexServer(self.base_url, self.token)
            music = server.library.section('Music')
            artists = music.search(libtype='artist')
            return [
                Artist(
                    id=str(artist.ratingKey),
                    name=artist.title,
                    genres=[genre.tag for genre in getattr(artist, 'genres', [])]
                )
                for artist in artists
            ]
        except Exception as e:
            logger.error(f"Failed to get artists: {str(e)}")
            raise

    def create_playlist(self, name: str, artist_names: List[str], min_tracks: int = 30, max_tracks: int = 50):
        """Create a playlist with tracks from the specified artists"""
        try:
            server = PlexServer(self.base_url, self.token)
            music = server.library.section('Music')
            
            # Collect tracks from all specified artists
            all_tracks = []
            for artist_name in artist_names:
                artists = music.search(artist_name, libtype='artist')
                if artists:
                    artist_tracks = artists[0].tracks()
                    all_tracks.extend(artist_tracks)
            
            if not all_tracks:
                raise ValueError("No tracks found for the specified artists")
            
            # Shuffle and limit tracks
            import random
            random.shuffle(all_tracks)
            selected_tracks = all_tracks[:max(min(len(all_tracks), max_tracks), min_tracks)]
            
            # Create the playlist
            playlist = server.createPlaylist(name, items=selected_tracks)
            
            return playlist

        except Exception as e:
            logger.error(f"Failed to create playlist: {str(e)}")
            raise

    def get_artist_tracks(self, artist_name: str) -> dict:
        """Get all albums and tracks for an artist"""
        server = PlexServer(self.base_url, self.token)
        music = server.library.section('Music')
        
        artists = music.search(artist_name, libtype='artist')
        if not artists:
            return {}

        artist = artists[0]
        albums = []
        
        for album in artist.albums():
            album_tracks = []
            for track in album.tracks():
                album_tracks.append({
                    'title': track.title,
                    'duration': track.duration,
                    'track_number': track.trackNumber,
                    'key': track.key  # for finding the track later
                })
            
            albums.append({
                'name': album.title,
                'year': album.year,
                'tracks': album_tracks
            })

        return {
            artist_name: albums
        }

    def create_curated_playlist(self, name: str, track_recommendations: List[dict]):
        """Create a playlist from specific track recommendations"""
        server = PlexServer(self.base_url, self.token)
        music = server.library.section('Music')
        
        tracks = []
        for rec in track_recommendations:
            # Find the specific track
            results = music.search(rec['title'], libtype='track')
            for track in results:
                if track.artist().title == rec['artist']:
                    tracks.append(track)
                    break
        
        if not tracks:
            raise ValueError("No tracks found from recommendations")
            
        playlist = server.createPlaylist(name, items=tracks)
        return playlist

