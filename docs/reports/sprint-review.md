# Sprint Review

## Sprint Goal

Implement Version 1 of the music artist recommendation app. This includes a music player with engagement features (like buttons), a niche artist recommendation engine, and a secure OAuth connection to link Spotify accounts with persistent user data.

---

## Team
Mike Savio,
Anthony Holubiak,
Owen Buhler,
Carson Dodd,

---

## Sprint Backlog Review

### Done

| # | Item | Owner |
|---|---|---|
| #6 | Recommend smaller artists from listening history | Anthony Holubiak |
| #1 | Persist user data between sessions | Owen Buhler |
| #4 | Build basic media player (play/pause, skip controls) | Mike Savio |
| #12 | Add simple volume memory (remember last volume between sessions) | Mike Savio |
| #11 | Add song duration display (track length shown next to each song) | Mike Savio |
| #7 | Add recent plays section (short list of recently recommended tracks) | Mike Savio |
| #5 | Improve empty and error states (clear messages when no data or loading fails) | Carson Dodd |
| #13 | Connection safety (secure Spotify OAuth with CSRF state validation) | Anthony Holubiak |

### Not Done

| # | Item | Reason |
|---|---|---|
| #3 | Add recommended song to playlist | Deprioritized — deferred to next sprint |
| #9 | Add remove song from playlist | Deprioritized — deferred to next sprint |

---

## What Went Well

- The Spotify Web Playback SDK integration came together cleanly, giving us a fully in-browser player without needing an iframe.
- OAuth PKCE flow with CSRF state validation was implemented and tested end-to-end — users can securely connect and disconnect Spotify accounts.
- Persistent user data (liked songs, settings, recommendation history, volume) works reliably via MongoDB, surviving page reloads and sessions.
- The recommendation engine successfully returns lesser-known, genre-diverse tracks by deliberately skipping the top popularity results from external APIs.

---

## Problems & Resolutions

### Problem — Spotify Recommendation API Removed

Last year, Spotify deprecated large portions of their developer platform and completely removed access to the Recommendations API. This broke the core feature of the app and required a full rethink of how song data would be sourced and analyzed.

### Resolution — Multi-API Strategy

Rather than relying on Spotify's catalog for discovery, we pivoted to a multi-API approach:

| API | Purpose |
|---|---|
| Spotify Web API | Fetch user's top tracks and listening history |
| Spotify Web Playback SDK | In-browser audio playback |
| iTunes Search API | Song catalog and niche artist discovery |
| Spotify Music Analytics (internal) | Popularity filtering to surface lesser-known songs |

This allowed us to build a recommendation engine that analyzes a user's taste from their Spotify history but sources new discoveries from external catalogs — bypassing Spotify's access restrictions entirely.

---

## Demo

> [Demo Video Link](https://example.com) — ~5 minutes

The demo covers:
- Connecting a Spotify account via secure OAuth
- Loading your top tracks and playing them in the web player
- Using "Recommend a Song" to discover lesser-known artists
- Like button, seek bar, duration display, and volume control
- Recommendation history panel showing recent discoveries
- Empty state and error state messages

---

## Next Steps — Revised Product Backlog

The following items are carried over or newly identified for the next sprint:

| Priority | Item | Notes |
|---|---|---|
| High | Add recommended song to playlist (#3) | Core engagement feature, ready to implement |
| High | Add remove song from playlist (#9) | Paired with above |
| Medium | Add Like Button on Player (#8) — close issue | Already implemented; close the issue on the board |
| Medium | Add Recommended-Only Filter (#2) | Filter the UI to show only recommended tracks |
| Medium | Add Playlist Rename Option (#10) | UX polish for playlist management |
| Low | Improve volume icon state on load | Minor UI polish — icon should reflect restored volume |

---

## Issue Board Status

- **Closed (Done):** #1, #4, #5, #6, #7, #8, #11, #12, #13
- **Open (Next Sprint):** #2, #3, #9, #10
- **Action items:**
  - Close #7 and #5 — stale "in progress" labels should be removed
  - Close #8 — Like button is fully implemented in code
  - Move #2, #3, #9, #10 to next sprint planning
