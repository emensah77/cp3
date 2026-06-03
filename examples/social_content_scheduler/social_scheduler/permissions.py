"""Role-based permission checks for scheduler operations."""

from __future__ import annotations

from dataclasses import dataclass


GENERATE = "generate"
SCHEDULE = "schedule"
APPROVE = "approve"
POST = "post"
ADMIN = "admin"


ROLE_PERMISSIONS = {
    "admin": {GENERATE, SCHEDULE, APPROVE, POST, ADMIN},
    "marketer": {GENERATE, SCHEDULE},
    "reviewer": {APPROVE},
    "worker": {POST},
}


@dataclass(frozen=True)
class Actor:
    id: str
    roles: set[str]

    @classmethod
    def from_role(cls, actor_id: str, role: str) -> "Actor":
        return cls(id=actor_id, roles={role})


def has_permission(actor: Actor, permission: str) -> bool:
    granted: set[str] = set()
    for role in actor.roles:
        granted.update(ROLE_PERMISSIONS.get(role, set()))
    return permission in granted


def require_permission(actor: Actor, permission: str) -> None:
    if not has_permission(actor, permission):
        roles = ",".join(sorted(actor.roles)) or "none"
        raise PermissionError(f"Actor {actor.id} with roles {roles} lacks {permission} permission")

