import time
import base64
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo_refresh")

# fake users store
users = [
    {"id": "u1", "spotify_refresh_token": base64.b64encode(b"old_refresh").decode(), "spotify_token_expires_at": time.time() - 10},
    {"id": "u2", "spotify_refresh_token": base64.b64encode(b"still_old").decode(), "spotify_token_expires_at": time.time() + 3600},
]


def decrypt_token(enc: str):
    try:
        return base64.b64decode(enc.encode()).decode()
    except Exception:
        return None


def encrypt_token(token: str):
    return base64.b64encode(token.encode()).decode()


def fake_exchange_refresh(rt):
    # simulate network call and token rotation
    logger.info("exchanging refresh token for token: %s", rt)
    time.sleep(0.2)
    return {"access_token": "access_" + rt, "refresh_token": "new_" + rt, "expires_in": 3600}


def refresh_all(max_per_run=None):
    now = time.time()
    count = 0
    for u in users:
        if max_per_run is not None and count >= max_per_run:
            break
        enc = u.get("spotify_refresh_token")
        expires_at = u.get("spotify_token_expires_at") or 0
        if not enc or (expires_at and expires_at > now + 300):
            continue
        rt = decrypt_token(enc)
        if not rt:
            continue
        try:
            resp = fake_exchange_refresh(rt)
            new_rt = resp.get("refresh_token")
            expires_in = int(resp.get("expires_in", 3600))
            u["spotify_refresh_token"] = encrypt_token(new_rt)
            u["spotify_token_expires_at"] = time.time() + max(expires_in - 30, 30)
            count += 1
            logger.info("rotated token for %s, new_expiry=%s", u["id"], u["spotify_token_expires_at"])
        except Exception as e:
            logger.exception("failed to refresh for %s: %s", u.get("id"), e)
    return count


if __name__ == "__main__":
    logger.info("starting demo scheduler loop")
    for i in range(2):
        n = refresh_all()
        logger.info("iteration %d refreshed %d tokens", i + 1, n)
        time.sleep(2)
    logger.info("demo complete")
