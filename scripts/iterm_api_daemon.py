#!/usr/bin/env python3
"""Keep one trusted iTerm2 API connection for repeatable theme switches."""

import asyncio

import iterm2


LIVE_PROFILE_KEYS = {
    "Name",
    "Background Color",
    "Foreground Color",
    "Bold Color",
    "Cursor Color",
    "Cursor Text Color",
    "Selection Color",
    "Selected Text Color",
    "Link Color",
    "Background Image Location",
    "Background Image Mode",
    "Background Image Source Mode",
    "Blend",
    "Normal Font",
    "Non Ascii Font",
    "Horizontal Spacing",
    "Vertical Spacing",
    "Keyboard Map",
}
LIVE_PROFILE_KEYS.update(f"Ansi {index} Color" for index in range(16))
API_TIMEOUT = 3


async def _set_session_profile(session, profile):
    try:
        await asyncio.wait_for(
            session.async_set_profile_properties(profile), timeout=API_TIMEOUT
        )
    except Exception:
        return False
    return True


@iterm2.RPC
async def terminal_theme_suite_ping():
    return "ready"


@iterm2.RPC
async def terminal_theme_suite_switch(profile_guid, scope):
    if scope not in {"all", "current"}:
        raise ValueError("scope must be 'all' or 'current'")

    profiles = []
    for _ in range(20):
        profiles = await asyncio.wait_for(
            iterm2.PartialProfile.async_query(
                terminal_theme_suite_switch.rpc_connection, guids=[profile_guid]
            ),
            timeout=API_TIMEOUT,
        )
        if profiles:
            break
        await asyncio.sleep(0.1)
    if not profiles:
        raise RuntimeError(f"iTerm2 has not loaded profile {profile_guid}")

    profile = await asyncio.wait_for(
        profiles[0].async_get_full_profile(), timeout=API_TIMEOUT
    )
    session_profile = iterm2.LocalWriteOnlyProfile(
        {
            key: value
            for key, value in profile.all_properties.items()
            if key in LIVE_PROFILE_KEYS
        }
    )
    await asyncio.wait_for(profile.async_make_default(), timeout=API_TIMEOUT)
    app = await asyncio.wait_for(
        iterm2.async_get_app(terminal_theme_suite_switch.rpc_connection),
        timeout=API_TIMEOUT,
    )
    if scope == "current":
        window = app.current_window
        session = window.current_tab.current_session if window else None
        sessions = [session] if session else []
    else:
        sessions = [
            session
            for window in app.windows
            for tab in window.tabs
            for session in tab.sessions
        ]
    results = await asyncio.gather(
        *(_set_session_profile(session, session_profile) for session in sessions)
    )
    return sum(results)


async def main(connection):
    await terminal_theme_suite_ping.async_register(connection)
    await terminal_theme_suite_switch.async_register(connection, timeout=15)
    await iterm2.async_wait_forever()


iterm2.run_forever(main)
