import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request


class RateLimiter:
    """Limite le nombre d'appels par adresse IP sur une fenêtre glissante (en mémoire, un seul processus).

    Sert de dépendance FastAPI : `Depends(RateLimiter(max_calls=10, window_seconds=60))`.
    Derrière un reverse proxy, uvicorn doit être lancé avec `--proxy-headers` pour lire la vraie adresse.
    """

    def __init__(self, max_calls: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        if max_calls < 1 or window_seconds <= 0:
            raise ValueError("max_calls doit être >= 1 et window_seconds > 0")
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._clock = clock
        self._calls: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = self._clock()
        calls = self._calls[key]
        while calls and now - calls[0] >= self.window_seconds:
            calls.popleft()
        if len(calls) >= self.max_calls:
            retry = int(self.window_seconds - (now - calls[0])) + 1
            raise HTTPException(status_code=429, detail=f"Trop de tentatives, réessayer dans {retry} s",
                                headers={"Retry-After": str(retry)})
        calls.append(now)
        if len(self._calls) > 10_000:                      # évite une croissance sans fin de la mémoire
            self._calls = defaultdict(deque, {k: v for k, v in self._calls.items() if v})

    def __call__(self, request: Request) -> None:
        self.check(request.client.host if request.client else "inconnu")
