"""
LLM Service

This module provides the LLMService class for generating playlist recommendations
using language models.
"""

import json
import logging
import os
from typing import List

from litellm import completion

from app.models import Artist

logger = logging.getLogger(__name__)


class LLMService:
    """
    A service class for generating playlist recommendations using language models.
    """

    def __init__(self, openai_key: str, anthropic_key: str | None = None):
        os.environ["OPENAI_API_KEY"] = openai_key
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key

        self.model_mapping = {
            "gpt-4": "gpt-4",
            "claude": "anthropic/claude-3-5-sonnet-latest",
        }

    def get_recommendations(self, prompt: str, artists: List[Artist], model: str = "gpt-4"):
        """Get playlist recommendations using LiteLLM"""
        try:
            model_id = self.model_mapping.get(model, model)

            # Create context with available artists
            artist_context = "Available artists and their genres:\n" + "\n".join(
                [f"{a.name} - {', '.join(a.genres)}" for a in artists if a.name]  # Skip empty names
            )

            system_prompt = """You are a music curator helping to create playlists.
            Analyze the available artists and their genres,
            then select the most appropriate ones for the requested playlist.
            Return your response as a JSON object with:
            - 'artists': array of 15-20 artist names from the provided list.
            Only include artists from the provided list."""

            response = completion(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Context: {artist_context}\n\nCreate a playlist for: {prompt}",
                    },
                ],
                max_tokens=1024,
                temperature=0.7,
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("artists", [])  # Return just the artists list

        except Exception as e:
            logger.error("AI recommendation failed: %s", str(e))
            raise

    def get_artist_recommendations(self, prompt: str, artists: List[Artist], model: str = "gpt-4"):
        """First step: Get relevant artists based on the prompt"""
        try:
            artist_context = "Available artists and their genres:\n" + "\n".join(
                [f"{a.name} - {', '.join(a.genres)}" for a in artists if a.name]
            )

            system_prompt = """You are a multilingual music curator helping to create playlists.
            Your responses must ALWAYS be in English, even when the prompt is in another language.
            Analyze the available artists and their genres,
            then select the most appropriate ones for the requested playlist.

            You must ALWAYS respond with valid JSON only, in this exact format:
            {"artists": ["Artist1", "Artist2", "Artist3"]}

            Do not add any explanations or other text - just the JSON object.
            Select 10-15 artists that match the mood/theme, only from the provided list."""

            response = completion(
                model=self.model_mapping.get(model, model),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Context: {artist_context}\n\nCreate a playlist for: {prompt}",
                    },
                ],
                max_tokens=1024,
                temperature=0.7,
            )

            content = response.choices[0].message.content.strip()
            logger.debug("Raw LLM response: %s", content)

            try:
                result = json.loads(content)
                artists_list = result.get("artists", [])
                if not artists_list:
                    raise ValueError("No artists found in response")

                logger.info("Selected artists: %s", artists_list)
                return artists_list

            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON: %s", e)
                logger.error("Received content: %s", content)
                raise

        except Exception as e:
            logger.error("Artist recommendation failed: %s", str(e))
            raise

    def get_track_recommendations(
        self, prompt: str, artist_tracks: dict, model: str = "gpt-4", min_tracks: int = 30, max_tracks: int = 50
    ):
        """Get track recommendations with simplified album context"""
        try:
            # Format just album information for context
            albums_context = "Available albums by artist:\n"
            for artist, albums in artist_tracks.items():
                albums_context += f"\n{artist}:\n"
                for album in albums:
                    albums_context += f"- {album['name']} ({album['year']})\n"

            system_prompt = """You are a multilingual music curator creating a cohesive playlist.
            Your responses must ALWAYS be in English and contain ONLY a valid JSON object.

            Based on your knowledge of these artists' albums and the playlist theme,
            recommend specific songs that would create a great playlist. You can recommend
            any tracks you know exist on these albums - you don't need to see the track list.

            You must respond with ONLY a JSON object in this exact format:
            {
                "tracks": [
                    {"artist": "artist name", "title": "track title"}
                ]
            }

            Select between {min_tracks} and {max_tracks} tracks total.
            Do not add any explanations or additional text."""

            response = completion(
                model=self.model_mapping.get(model, model),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"""Context: {albums_context}\n\n
                        Create a playlist with {min_tracks}-{max_tracks} tracks for: {prompt}
                        """,
                    },
                ],
                max_tokens=2048,
                temperature=0.7,
            )

            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            tracks_list = result.get("tracks", [])

            if not tracks_list:
                raise ValueError("No tracks found in response")

            logger.info("Selected tracks: %s", tracks_list)
            return tracks_list

        except Exception as e:
            logger.error("Track recommendation failed: %s", str(e))
            raise

    def generate_playlist_name(self, prompt: str, model: str = "gpt-4") -> str:
        """Generate a playlist name based on the prompt"""
        try:
            system_prompt = """
            You are a creative assistant.
            Generate a SINGLE catchy and relevant playlist name based on the following prompt. Do not wrap in quotes.
            """

            response = completion(
                model=self.model_mapping.get(model, model),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=30,
                temperature=0.7,
            )

            name = response.choices[0].message.content.strip()
            logger.info("Generated playlist name: %s", name)
            return name

        except Exception as e:
            logger.error("Failed to generate playlist name: %s", str(e))
            raise
