import time
from collections import deque
from urllib.parse import quote

import httpx

from src import config


class RiotError(Exception):
    pass


class AuthError(RiotError):
    pass


class NotFoundError(RiotError):
    pass


class RateLimitError(RiotError):
    pass


class NetworkError(RiotError):
    pass


class _RateLimiter:
    """Giữ dưới 20 req/giây và 100 req/2 phút cho dev key."""

    def __init__(self, sleep_fn, time_fn=time.monotonic):
        self._sleep = sleep_fn
        self._time_fn = time_fn
        self._sec = deque()
        self._long = deque()

    def _now(self):
        return self._time_fn()

    def acquire(self):
        while True:
            now = self._now()
            while self._sec and now - self._sec[0] >= 1:
                self._sec.popleft()
            while self._long and now - self._long[0] >= 120:
                self._long.popleft()
            if len(self._sec) < 20 and len(self._long) < 100:
                self._sec.append(now)
                self._long.append(now)
                return
            wait_sec = 1 - (now - self._sec[0]) if len(self._sec) >= 20 else 0
            wait_long = 120 - (now - self._long[0]) if len(self._long) >= 100 else 0
            self._sleep(max(0.02, wait_sec, wait_long))


class RiotClient:
    def __init__(self, api_key=config.RIOT_API_KEY, transport=None, sleep_fn=time.sleep,
                 max_retries=3):
        self.api_key = api_key
        self.sleep_fn = sleep_fn
        self.max_retries = max_retries
        self.limiter = _RateLimiter(sleep_fn)
        self._client = httpx.Client(
            transport=transport,
            timeout=15.0,
            headers={"X-Riot-Token": api_key},
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _get(self, url, params=None):
        attempt = 0
        while True:
            attempt += 1
            self.limiter.acquire()
            try:
                resp = self._client.get(url, params=params)
            except httpx.HTTPError as e:
                raise NetworkError(str(e)) from e
            code = resp.status_code
            if code == 200:
                return resp.json()
            if code in (401, 403):
                raise AuthError(f"{code}: key sai hoặc hết hạn")
            if code == 404:
                raise NotFoundError(f"404: {url}")
            if code == 429:
                try:
                    retry_after = float(resp.headers.get("Retry-After", "1"))
                except (TypeError, ValueError):
                    retry_after = 1.0
                if attempt > self.max_retries:
                    raise RateLimitError("429 quá nhiều lần")
                self.sleep_fn(retry_after)
                continue
            if 500 <= code < 600:
                if attempt > self.max_retries:
                    raise RiotError(f"{code}: lỗi máy chủ Riot")
                self.sleep_fn(1.0)
                continue
            raise RiotError(f"{code}: {url}")

    def get_account_by_riot_id(self, game_name, tag_line):
        url = (f"{config.account_host()}/riot/account/v1/accounts/by-riot-id/"
               f"{quote(game_name)}/{quote(tag_line)}")
        return self._get(url)

    def get_league_entries(self, puuid):
        # Ưu tiên endpoint by-puuid (mới). Nếu 404 -> fallback qua summoner-v4.
        url = f"{config.platform_host()}/lol/league/v4/entries/by-puuid/{quote(puuid)}"
        try:
            return self._get(url)
        except NotFoundError:
            surl = f"{config.platform_host()}/lol/summoner/v4/summoners/by-puuid/{quote(puuid)}"
            summoner = self._get(surl)
            sid = summoner.get("id")
            if not sid:
                return []
            lurl = f"{config.platform_host()}/lol/league/v4/entries/by-summoner/{quote(sid)}"
            return self._get(lurl)

    def get_ranked_match_ids(self, puuid, count=config.MATCH_COUNT):
        url = f"{config.match_host()}/lol/match/v5/matches/by-puuid/{quote(puuid)}/ids"
        return self._get(url, params={"type": config.MATCH_TYPE, "start": 0, "count": count})

    def get_match(self, match_id):
        url = f"{config.match_host()}/lol/match/v5/matches/{quote(match_id)}"
        return self._get(url)
