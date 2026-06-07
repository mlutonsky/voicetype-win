"""Pause and resume playing media via Windows System Media Transport Controls.

Works with players integrated into SMTC: YouTube/media in the browser (Chrome,
Edge), Spotify, Groove, VLC (with a plugin), etc. Pauses ONLY what is currently
playing and resumes exactly those players - it never blindly starts anything else.
"""
import asyncio

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as _Manager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as _Status,
    )
    _AVAILABLE = True
except Exception:
    _AVAILABLE = False


def available() -> bool:
    return _AVAILABLE


async def _pause_playing_async() -> list[str]:
    mgr = await _Manager.request_async()
    paused: list[str] = []
    for s in mgr.get_sessions():
        try:
            info = s.get_playback_info()
            if info and info.playback_status == _Status.PLAYING:
                if await s.try_pause_async():
                    paused.append(s.source_app_user_model_id or "")
        except Exception:
            pass
    return paused


async def _resume_async(app_ids: list[str]) -> None:
    if not app_ids:
        return
    wanted = set(app_ids)
    mgr = await _Manager.request_async()
    for s in mgr.get_sessions():
        try:
            if (s.source_app_user_model_id or "") in wanted:
                await s.try_play_async()
        except Exception:
            pass


def pause_playing() -> list[str]:
    """Pause playing media. Returns the list of app IDs that were paused."""
    if not _AVAILABLE:
        return []
    try:
        return asyncio.run(_pause_playing_async())
    except Exception:
        return []


def resume(app_ids: list[str]) -> None:
    """Resume the players from the given list of app IDs."""
    if not _AVAILABLE or not app_ids:
        return
    try:
        asyncio.run(_resume_async(app_ids))
    except Exception:
        pass


if __name__ == "__main__":
    async def _list():
        mgr = await _Manager.request_async()
        for s in mgr.get_sessions():
            info = s.get_playback_info()
            print(f"- {s.source_app_user_model_id!r}: status={info.playback_status if info else '?'}")
    print("winsdk available:", _AVAILABLE)
    asyncio.run(_list())
