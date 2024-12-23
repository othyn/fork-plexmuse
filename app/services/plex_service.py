"""
Plex Service

Provides the PlexService class for interacting with the Plex API.
"""

import logging
from difflib import SequenceMatcher
from typing import List, Optional

from dotenv import load_dotenv
from plexapi.server import PlexServer

from app.models import Artist

load_dotenv()
logger = logging.getLogger(__name__)


def get_best_track_match(album_tracks: List[dict], suggested_title: str, threshold: float = 0.6) -> Optional[dict]:
    """
    Find the best matching track from an album using fuzzy string matching.

    Args:
        album_tracks: List of track dictionaries from Plex
        suggested_title: The track title suggested by the LLM
        threshold: Minimum similarity score to consider a match

    Returns:
        Best matching track dict or None if no good match found
    """
    best_match = None
    best_score = 0

    for track in album_tracks:
        score = SequenceMatcher(None, track["title"].lower(), suggested_title.lower()).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best_match = track

    if best_match:
        logger.debug("Matched '%s' to '%s' with score %s", suggested_title, best_match["title"], best_score)
    else:
        logger.debug("No match found for '%s' above threshold %s", suggested_title, threshold)

    return best_match


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

    def get_artist_albums(self, artist_name: str) -> dict:
        """Get just album metadata for an artist"""
        server = PlexServer(self.base_url, self.token)
        music = server.library.section("Music")

        artists = music.search(artist_name, libtype="artist")
        if not artists:
            return {}

        artist = artists[0]
        albums = []

        for album in artist.albums():
            albums.append({"name": album.title, "year": album.year, "track_count": len(album.tracks())})

        return {artist_name: albums}

    def create_curated_playlist(self, name: str, track_recommendations: List[dict]):
        """Create a playlist with fuzzy track matching"""
        server = PlexServer(self.base_url, self.token)
        music = server.library.section("Music")

        matched_tracks = []
        for rec in track_recommendations:
            # Find the artist first
            artists = music.search(rec["artist"], libtype="artist")
            if not artists:
                logger.warning("Artist not found: %s", rec["artist"])
                continue

            artist = artists[0]

            # Search through each album
            track_found = False
            for album in artist.albums():
                match = get_best_track_match([{"title": t.title, "key": t.key} for t in album.tracks()], rec["title"])
                if match:
                    track = music.fetchItem(match["key"])
                    matched_tracks.append(track)
                    track_found = True
                    break

            if not track_found:
                logger.warning("No matching track found for: %s by %s", rec["title"], rec["artist"])

        if not matched_tracks:
            raise ValueError("No tracks could be matched from recommendations")

        playlist = server.createPlaylist(name, items=matched_tracks)
        return playlist
