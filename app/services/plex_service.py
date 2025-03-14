"""
Plex Service with artist caching and optimized album loading.
"""

import logging
from difflib import SequenceMatcher
from typing import Dict, List, Optional

from plexapi.server import PlexServer

from app.models import Artist

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """Normalize track title for better matching by removing common variations"""
    # Convert to lowercase
    title = title.lower()
    # Remove common suffixes in parentheses
    if "(" in title:
        title = title.split("(")[0].strip()
    # Remove special characters but preserve spaces
    title = title.replace("'", "").replace(",", " ").replace(".", " ")
    # Normalize whitespace
    return " ".join(word for word in title.split() if word)


def find_best_track_match(tracks, target_title, threshold=0.85):
    """
    Find best matching track using fuzzy string matching.

    Args:
        tracks: List of track objects from Plex
        target_title: Title to match against
        threshold: Minimum similarity score (0-1) to consider a match

    Returns:
        Tuple of (best_match, score) or (None, 0) if no match found
    """

    target_normalized = normalize_title(target_title)
    best_match = None
    best_score = 0

    for track in tracks:
        track_normalized = normalize_title(track.title)

        # Calculate similarity on normalized titles
        score = SequenceMatcher(None, track_normalized, target_normalized).ratio()

        # If exact match found after normalization, return immediately
        if score == 1.0:
            return track, 1.0

        if score > best_score and score >= threshold:
            best_score = score
            best_match = track

    return best_match, best_score


class PlexService:
    """
    A service class for interacting with the Plex API with artist caching.
    """

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self._server: Optional[PlexServer] = None
        self.machine_identifier: Optional[str] = None
        self._music_libraries = []

        # Only cache artists
        self._artists_cache: Dict[str, Artist] = {}  # key: artist_id -> Artist

    def get_cache_size(self) -> int:
        """Get the number of artists in the cache"""
        return len(self._artists_cache)

    def initialize(self):
        """Initialize artist cache"""
        logger.info("Initializing PlexService artist cache...")
        try:
            self._server = PlexServer(self.base_url, self.token)
            self.machine_identifier = self._server.machineIdentifier

            # Find all music libraries instead of assuming one called "Music"
            self._music_libraries = []
            for section in self._server.library.sections():
                if section.type == "artist":
                    self._music_libraries.append(section)
                    logger.info(f"Found music library: {section.title}")

            if not self._music_libraries:
                logger.warning("No music libraries found on the Plex server")
                return

            # Load all artists from all music libraries
            for library in self._music_libraries:
                artists = library.search(libtype="artist")
                for artist in artists:
                    artist_id = str(artist.ratingKey)
                    # Only add if not already in cache (avoid duplicates across libraries)
                    if artist_id not in self._artists_cache:
                        self._artists_cache[artist_id] = Artist(
                            id=artist_id,
                            name=artist.title,
                            genres=[genre.tag for genre in getattr(artist, "genres", [])],
                        )

            logger.info(
                "Cached %d artists from %d music libraries", len(self._artists_cache), len(self._music_libraries)
            )

        except Exception as e:
            logger.error("Failed to initialize Plex cache: %s", str(e))
            raise

    def get_all_artists(self) -> List[Artist]:
        """Get all artists from cache"""
        return list(self._artists_cache.values())

    def get_artists_albums_bulk(self, artist_names: List[str]) -> dict:
        """Get albums for multiple artists in one go"""
        if not self._server:
            self._server = PlexServer(self.base_url, self.token)

        result = {}
        # Find all matching artists first
        artist_objects = []
        for artist_name in artist_names:
            artist_found = None
            # First try cache lookup by name
            for artist in self._artists_cache.values():
                if artist.name.lower() == artist_name.lower():
                    # Found in cache, now get the Plex object
                    # Search across all music libraries
                    for library in self._music_libraries:
                        matches = library.search(artist.name, libtype="artist")
                        if matches:
                            artist_found = matches[0]
                            break
                    if artist_found:
                        break

            if artist_found:
                artist_objects.append(artist_found)
            else:
                logger.warning("Artist not found: %s", artist_name)

        # Now get all albums in one go
        for artist in artist_objects:
            albums = []
            for album in artist.albums():
                albums.append({"name": album.title, "year": album.year, "track_count": len(album.tracks())})
            result[artist.title] = albums

        return result

    def create_curated_playlist(
        self, name: str, track_recommendations: List[dict]
    ):  # pylint: disable=too-many-locals,too-many-branches
        """Create a playlist with fuzzy track matching"""
        if not self._server:
            self._server = PlexServer(self.base_url, self.token)

        matched_tracks = []
        # Group recommendations by artist for efficiency
        artist_tracks = {}
        for rec in track_recommendations:
            artist_tracks.setdefault(rec["artist"], []).append(rec["title"])

        # Process each artist's tracks in bulk
        for artist_name, track_titles in artist_tracks.items():
            # Search for artist across all music libraries
            artists = []
            for library in self._music_libraries:
                found_artists = library.search(artist_name, libtype="artist")
                if found_artists:
                    artists.append(found_artists[0])
                    break  # Found in one library, no need to check others

            if not artists:
                logger.warning("Artist not found: %s", artist_name)
                continue

            artist = artists[0]
            # Get all tracks for this artist at once
            all_tracks = []
            for album in artist.albums():
                all_tracks.extend(album.tracks())

            # Match tracks using fuzzy matching
            for title in track_titles:
                track, score = find_best_track_match(all_tracks, title)
                if track:
                    logger.debug("Matched '%s' to '%s' (score: %.2f)", title, track.title, score)
                    matched_tracks.append(track)
                else:
                    # If no match found for artist, try global search across all music libraries
                    global_tracks = []
                    for library in self._music_libraries:
                        found_tracks = library.search(title, libtype="track")
                        global_tracks.extend(found_tracks)

                    if global_tracks:
                        track, score = find_best_track_match(global_tracks, title, threshold=0.75)
                        if track and track.artist().title.lower() == artist_name.lower():
                            logger.debug("Found track '%s' through global search (score: %.2f)", track.title, score)
                            matched_tracks.append(track)
                        else:
                            logger.warning("No matching track found for: %s by %s", title, artist_name)
                    else:
                        logger.warning("No matching track found for: %s by %s", title, artist_name)

        if not matched_tracks:
            raise ValueError("No tracks could be matched from recommendations")

        playlist = self._server.createPlaylist(name, items=matched_tracks)
        return playlist
