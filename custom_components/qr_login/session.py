"""Pending login sessions and their outcome history."""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

HISTORY_SIZE = 25


def record_outcome(data, session, outcome: str, decided_by: str = "") -> None:
    """Append a request's outcome to the in-memory history, once."""
    if session.recorded:
        return
    session.recorded = True
    data.history.appendleft(session.to_history_dict(outcome, decided_by))


def new_history() -> deque:
    return deque(maxlen=HISTORY_SIZE)


@dataclass
class QRLoginSession:
    session_id: str
    username: str
    target_user: str
    notify_target: str
    channel: str
    client_ip: str
    user_agent: str
    expires_at: float
    public_channel: str = ""
    # Only an admin-configured mapping may retarget the token; a username
    # typed by the anonymous requester must never be trusted as a target.
    target_from_mapping: bool = False
    client_id: str = ""
    status: str = "pending"
    access_token: str | None = None
    refresh_token: str | None = None
    token_expires_in: int = 1800
    created_at: float = field(default_factory=time.time)
    recorded: bool = False

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def expires_in(self) -> int:
        return max(0, int(self.expires_at - time.time()))

    def age(self) -> int:
        return max(0, int(time.time() - self.created_at))

    def to_public_dict(self, include_tokens: bool = False) -> dict[str, Any]:
        """Payload for the anonymous requester polling /status.

        Deliberately free of username, target account, IP and user agent:
        anyone knowing the session id can call that endpoint.
        """
        payload: dict[str, Any] = {
            "session_id": self.session_id,
            "status": self.status,
            "channel": self.public_channel or self.channel,
            "expires_in": self.expires_in(),
        }
        if include_tokens:
            payload["access_token"] = self.access_token
            payload["refresh_token"] = self.refresh_token
            payload["token_expires_in"] = self.token_expires_in
        return payload

    def to_history_dict(self, outcome: str, decided_by: str = "") -> dict[str, Any]:
        """Compact, token-free record of how a request ended."""
        return {
            "session_id": self.session_id,
            "outcome": outcome,
            "at": time.time(),
            "username": self.username,
            "target_user": self.target_user,
            "target_from_mapping": self.target_from_mapping,
            "channel": self.channel,
            "client_ip": self.client_ip,
            "decided_by": decided_by,
        }

    def to_detail_dict(self) -> dict[str, Any]:
        """Payload for the authenticated approver reviewing the request."""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "username": self.username,
            "target_user": self.target_user,
            "target_from_mapping": self.target_from_mapping,
            "channel": self.channel,
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "expires_in": self.expires_in(),
            "age": self.age(),
        }
