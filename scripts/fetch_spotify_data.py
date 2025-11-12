"""Fetch playlist and track metadata from the Spotify Web API and
rewrite data/scripts/data.js for the Afrobeats dashboard.

Usage (PowerShell example):

    # 1. Ensure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are available.
    #    Consider keeping them in a .env file next to this script.
    # 2. Populate data/playlist_config.json with the playlists you want to analyse.
    # 3. Maintain artist details in data/artist_metadata.csv (artistCountry, regionGroup, diaspora).
    # 4. If requests isn't installed yet, run:  python -m pip install requests
    # 5. Execute the script from the repository root:
    #      python scripts/fetch_spotify_data.py
    # 6. Outputs are written to:
    #      data/raw/<slug>.json
    #      data/processed/afrobeats_playlists.json
    #      data/scripts/data.js (for the dashboard)
"""
from __future__ import annotations

import base64
import json
import os
from csv import DictReader
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
OUTPUT_FILE = REPO_ROOT / "data" / "scripts" / "data.js"
PLAYLIST_CONFIG_FILE = REPO_ROOT / "data" / "playlist_config.json"
RAW_DATA_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DATA_FILE = REPO_ROOT / "data" / "processed" / "afrobeats_playlists.json"
ARTIST_METADATA_FILE = REPO_ROOT / "data" / "artist_metadata.csv"

# Update this structure with the playlists you want to analyse.
# Keys become the playlist ids in the dashboard output.
_DEFAULT_PLAYLIST_CONFIG = {
    "afrobeats-hits": {
        "id": "25Y75ozl2aI0NylFToefO5",
        "curatorType": "Independent Curator",
        "label": "Afrobeats Hits",
    },
    "afrobeats-2026": {
        "id": "5myeBzohhCVewaK2Thqmo5",
        "curatorType": "Independent Curator",
        "label": "Afrobeats 2026",
    },
    "ginja": {
        "id": "4XtoXt98uSrnUbMz7JtWZk",
        "curatorType": "User-Generated",
        "label": "Ginja",
    },
    "viral-afrobeats": {
        "id": "6ebiO5veMmbIWL5aGvalgQ",
        "curatorType": "Media Publisher",
        "label": "Viral Afrobeats",
    },
    "top-afrobeats-hits": {
        "id": "0RChPss4CYl5LTfK0CRgOZ",
        "curatorType": "Media Publisher",
        "label": "Top Afrobeats Hits",
    },
    "afrobeats-gold": {
        "id": "1UFBYLsMwB2q0EypxWdBLO",
        "curatorType": "Independent Curator",
        "label": "Afrobeats Gold",
    },
    "amapiano-2025": {
        "id": "4Ymf8eaPQGT7HMTymoX82f",
        "curatorType": "Independent Curator",
        "label": "Amapiano 2025",
    },
    "top-picks-afrobeats": {
        "id": "1ynsIf7ZgpEFxIvuDBlUcK",
        "curatorType": "Media Publisher",
        "label": "Top Picks: Afrobeats",
    },
    "afrobeats-hits-indie": {
        "id": "2DfNaw9Z1nuddjI6NczTXS",
        "curatorType": "Independent Curator",
        "label": "Afrobeats Hits (Indie)",
    },
}

_DEFAULT_ARTIST_METADATA = {
    "Rema": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Ayra Starr": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Burna Boy": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Wizkid": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Davido": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Tems": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Omah Lay": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "CKay": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Lojay": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Fireboy DML": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Joeboy": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Oxlade": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Tyla": {"artistCountry": "South Africa", "regionGroup": "Southern Africa", "diaspora": False},
    "Rotimi": {"artistCountry": "United States", "regionGroup": "US Diaspora", "diaspora": True},
    "Chris Brown": {"artistCountry": "United States", "regionGroup": "US Diaspora", "diaspora": True},
    "Don Toliver": {"artistCountry": "United States", "regionGroup": "US Diaspora", "diaspora": True},
    "Ed Sheeran": {"artistCountry": "United Kingdom", "regionGroup": "UK Collaborator", "diaspora": True},
    "Sarz": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Victony": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Mack H.D": {"artistCountry": "Canada", "regionGroup": "Diaspora Collective", "diaspora": True},
    "Black Sherif": {"artistCountry": "Ghana", "regionGroup": "Ghana", "diaspora": False},
    "King Promise": {"artistCountry": "Ghana", "regionGroup": "Ghana", "diaspora": False},
    "Amaarae": {"artistCountry": "Ghana", "regionGroup": "Ghana", "diaspora": True},
    "Stonebwoy": {"artistCountry": "Ghana", "regionGroup": "Ghana", "diaspora": False},
    "Kuami Eugene": {"artistCountry": "Ghana", "regionGroup": "Ghana", "diaspora": False},
    "Lasmid": {"artistCountry": "Ghana", "regionGroup": "Ghana", "diaspora": False},
    "Shatta Wale": {"artistCountry": "Ghana", "regionGroup": "Ghana", "diaspora": False},
    "Teni": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Tiwa Savage": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Kizz Daniel": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Mr Eazi": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
    "Yemi Alade": {"artistCountry": "Nigeria", "regionGroup": "Nigeria", "diaspora": False},
}

def load_env_file(path: Path) -> None:
    """Populate os.environ with variables from a simple KEY=VALUE .env file."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"')
        os.environ.setdefault(key, value)


def build_basic_auth_header(client_id: str, client_secret: str) -> str:
    token = base64.b64encode(f"{client_id}:{client_secret}".encode("ascii")).decode("ascii")
    return f"Basic {token}"


def get_access_token(client_id: str, client_secret: str) -> str:
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        headers={"Authorization": build_basic_auth_header(client_id, client_secret)},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["access_token"]


def fetch_playlist_snapshot(playlist_id: str, token: str, market: Optional[str] = None) -> Dict:
    """Fetch playlist metadata plus the first page of tracks."""
    params = {"market": market} if market else None
    response = requests.get(
        f"https://api.spotify.com/v1/playlists/{playlist_id}",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def fetch_all_playlist_tracks(playlist: Dict, token: str) -> List[Dict]:
    """Walk the paginated playlist tracks feed and collect all track entries."""
    items: List[Dict] = []
    tracks_block = playlist.get("tracks", {})
    next_url = tracks_block.get("next")
    items.extend(tracks_block.get("items", []))

    while next_url:
        response = requests.get(next_url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        response.raise_for_status()
        page = response.json()
        next_url = page.get("next")
        items.extend(page.get("items", []))

    return items


def chunked(iterable: Iterable[str], size: int) -> Iterable[List[str]]:
    chunk: List[str] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def utc_timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def load_playlist_config(path: Path) -> Dict[str, Dict]:
    if not path.exists():
        return dict(_DEFAULT_PLAYLIST_CONFIG)

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse playlist config at {path}: {exc}") from exc

    config = payload.get("playlists") if isinstance(payload, dict) else payload
    if not isinstance(config, dict):
        raise SystemExit("Playlist config file must map playlist slugs to configuration objects.")

    if not config:
        raise SystemExit("Playlist config file is empty. Populate it with playlist entries before running.")

    return config


def load_artist_metadata(path: Path) -> Dict[str, Dict]:
    if not path.exists():
        return dict(_DEFAULT_ARTIST_METADATA)

    with path.open(encoding="utf-8") as handle:
        reader = DictReader(handle)
        required_columns = {"artist", "artistCountry", "regionGroup", "diaspora"}
        if not required_columns.issubset(reader.fieldnames or []):
            missing = required_columns - set(reader.fieldnames or [])
            raise SystemExit(
                f"Artist metadata file is missing required columns: {', '.join(sorted(missing))}."
            )

        metadata: Dict[str, Dict] = {}
        for row in reader:
            artist_name = (row.get("artist") or "").strip()
            if not artist_name:
                continue
            diaspora_value = (row.get("diaspora") or "").strip().lower()
            metadata[artist_name] = {
                "artistCountry": (row.get("artistCountry") or "Unknown").strip() or "Unknown",
                "regionGroup": (row.get("regionGroup") or "Unknown").strip() or "Unknown",
                "diaspora": diaspora_value in {"true", "1", "yes", "y"},
            }

    return metadata or dict(_DEFAULT_ARTIST_METADATA)


def fetch_audio_features(track_ids: List[str], token: str) -> Dict[str, Dict]:
    features: Dict[str, Dict] = {}
    for batch in chunked(track_ids, 100):
        try:
            response = requests.get(
                "https://api.spotify.com/v1/audio-features",
                params={"ids": ",".join(batch)},
                headers={"Authorization": f"Bearer {token}"},
                timeout=20,
            )
            response.raise_for_status()
        except requests.HTTPError as error:
            print(
                "Warning: audio-features request failed",
                getattr(error.response, "status_code", "?"),
                getattr(error.response, "text", ""),
            )
            continue
        for entry in response.json().get("audio_features", []) or []:
            if entry and entry.get("id"):
                features[entry["id"]] = entry
    return features


def parse_release_year(album: Optional[Dict]) -> Optional[int]:
    if not album:
        return None
    release_date = album.get("release_date")
    if not release_date:
        return None
    try:
        return datetime.fromisoformat(release_date[:10]).year
    except ValueError:
        try:
            return int(release_date[:4])
        except (TypeError, ValueError):
            return None


def build_track_payload(
    track_item: Dict,
    feature: Optional[Dict],
    artist_metadata: Dict[str, Dict],
    missing_artists: Set[str],
) -> Optional[Dict]:
    track = track_item.get("track")
    if not track or track.get("is_local"):
        return None

    track_id = track.get("id")
    if not track_id:
        return None

    artists = track.get("artists", [])
    artist_names = ", ".join(artist.get("name", "Unknown") for artist in artists) or "Unknown"
    primary_artist = artists[0].get("name") if artists else None
    metadata = artist_metadata.get(primary_artist or "") if primary_artist else None
    if not metadata and primary_artist:
        missing_artists.add(primary_artist)

    features_block = None
    if feature:
        features_block = {
            "danceability": feature.get("danceability"),
            "energy": feature.get("energy"),
            "valence": feature.get("valence"),
            "tempo": feature.get("tempo"),
            "acousticness": feature.get("acousticness"),
        }

    return {
        "id": track_id,
        "title": track.get("name", "Unknown"),
        "artist": artist_names,
        "artistCountry": metadata.get("artistCountry") if metadata else "Unknown",
        "regionGroup": metadata.get("regionGroup") if metadata else "Unknown",
        "diaspora": metadata.get("diaspora") if metadata else False,
        "releaseYear": parse_release_year(track.get("album")),
        "features": features_block,
    }


def normalize_playlist(
    playlist_id: str,
    config: Dict,
    snapshot: Dict,
    track_items: List[Dict],
    audio_features: Dict[str, Dict],
    artist_metadata: Dict[str, Dict],
    missing_artists: Set[str],
) -> Dict:
    tracks_payload: List[Dict] = []
    for item in track_items:
        track_id = item.get("track", {}).get("id")
        payload = build_track_payload(
            item,
            audio_features.get(track_id),
            artist_metadata,
            missing_artists,
        )
        if payload:
            tracks_payload.append(payload)

    playlist_owner = snapshot.get("owner", {})
    followers = snapshot.get("followers", {}).get("total")

    launch_year = None
    for item in track_items:
        first_year = parse_release_year(item.get("track", {}).get("album"))
        if first_year:
            launch_year = first_year
            break

    return {
        "id": playlist_id,
        "name": snapshot.get("name", config.get("label", playlist_id)),
        "curatorType": config.get("curatorType", "Unknown"),
        "curator": playlist_owner.get("display_name") or playlist_owner.get("id") or "Unknown",
        "followerCount": followers,
        "launchYear": launch_year,
        "description": snapshot.get("description"),
        "tracks": tracks_payload,
    }


def main() -> None:
    load_env_file(ENV_FILE)

    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set.")

    playlist_config = load_playlist_config(PLAYLIST_CONFIG_FILE)
    artist_metadata = load_artist_metadata(ARTIST_METADATA_FILE)

    access_token = get_access_token(client_id, client_secret)

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    run_started_at = utc_timestamp()
    playlists_payload: List[Dict] = []
    missing_artists: Set[str] = set()
    skipped_playlists: Dict[str, Dict[str, Optional[str]]] = {}
    for slug, cfg in playlist_config.items():
        if "id" not in cfg:
            raise SystemExit(f"Playlist config for '{slug}' is missing an 'id'.")
        print(f"Fetching playlist {slug} ({cfg['id']})...", flush=True)
        market = cfg.get("market")
        try:
            snapshot = fetch_playlist_snapshot(cfg["id"], access_token, market=market)
        except requests.HTTPError as error:
            status_code = getattr(error.response, "status_code", "?")
            message = getattr(error.response, "text", "") or getattr(error.response, "reason", "")
            print(f"  ! Failed to fetch playlist (status {status_code}). Skipping.")
            skipped_playlists[slug] = {
                "playlistId": cfg["id"],
                "status": str(status_code),
                "message": (message or "")[:200],
            }
            continue
        track_items = fetch_all_playlist_tracks(snapshot, access_token)
        track_ids = [item.get("track", {}).get("id") for item in track_items if item.get("track")]
        track_ids = [track_id for track_id in track_ids if track_id]

        audio_features = fetch_audio_features(track_ids, access_token) if track_ids else {}

        missing_for_playlist: Set[str] = set()
        playlists_payload.append(
            normalize_playlist(
                slug,
                cfg,
                snapshot,
                track_items,
                audio_features,
                artist_metadata,
                missing_for_playlist,
            )
        )
        if missing_for_playlist:
            missing_artists.update(missing_for_playlist)

        raw_payload = {
            "slug": slug,
            "playlistId": cfg["id"],
            "fetchedAt": utc_timestamp(),
            "config": dict(cfg),
            "snapshot": snapshot,
            "trackItems": track_items,
            "audioFeatures": audio_features,
            "missingArtists": sorted(missing_for_playlist),
        }
        raw_file = RAW_DATA_DIR / f"{slug}.json"
        raw_file.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
        print(f"  ↳ raw -> {raw_file.relative_to(REPO_ROOT)}")

    run_completed_at = utc_timestamp()
    dataset = {
        "playlists": playlists_payload,
        "runMetadata": {
            "startedAt": run_started_at,
            "generatedAt": run_completed_at,
            "playlistCount": len(playlists_payload),
            "missingArtists": sorted(missing_artists),
            "skippedPlaylists": skipped_playlists,
        },
    }

    PROCESSED_DATA_FILE.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    print(f"Wrote {PROCESSED_DATA_FILE.relative_to(REPO_ROOT)}")

    OUTPUT_FILE.write_text(
        "window.AFROBEATS_DATA = " + json.dumps(dataset, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_FILE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
