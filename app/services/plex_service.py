"""
Plex Service

Provides the PlexService class for interacting with the Plex API.
"""

import logging
from typing import List

from dotenv import load_dotenv
from plexapi.server import PlexServer

from app.models import Artist

load_dotenv()
logger = logging.getLogger(__name__)


class PlexService:
    """
    A service class for interacting with the Plex API.
    """

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token

    def get_music_library(self):
        """Get the music library section from Plex"""
        server = PlexServer(self.base_url, self.token)
        return server.library.section("Music")

    def get_all_artists(self) -> List[Artist]:
        """Get all artists from the music library"""
        try:
            server = PlexServer(self.base_url, self.token)
            music = server.library.section("Music")
            artists = music.search(libtype="artist")
            return [
                Artist(
                    id=str(artist.ratingKey),
                    name=artist.title,
                    genres=[genre.tag for genre in getattr(artist, "genres", [])],
                )
                for artist in artists
            ]
        except Exception as e:
            logger.error("Failed to get artists: %s", str(e))
            raise

    def get_artist_tracks(self, artist_name: str) -> dict:
        """Get all albums and tracks for an artist"""
        server = PlexServer(self.base_url, self.token)
        music = server.library.section("Music")

        artists = music.search(artist_name, libtype="artist")
        if not artists:
            return {}

        artist = artists[0]
        albums = []

        for album in artist.albums():
            album_tracks = []
            for track in album.tracks():
                album_tracks.append(
                    {
                        "title": track.title,
                        "duration": track.duration,
                        "track_number": track.trackNumber,
                        "key": track.key,  # for finding the track later
                    }
                )

            albums.append({"name": album.title, "year": album.year, "tracks": album_tracks})

        return {artist_name: albums}

    def create_curated_playlist(self, name: str, track_recommendations: List[dict]):
        """Create a playlist from specific track recommendations"""
        server = PlexServer(self.base_url, self.token)
        music = server.library.section("Music")

        tracks = []
        for rec in track_recommendations:
            # Find the specific track
            results = music.search(rec["title"], libtype="track")
            for track in results:
                if track.artist().title == rec["artist"]:
                    tracks.append(track)
                    break

        if not tracks:
            raise ValueError("No tracks found from recommendations")

        playlist = server.createPlaylist(name, items=tracks)
        return playlist
