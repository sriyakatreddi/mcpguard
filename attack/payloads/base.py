"""Base class defining the contract every attack payload must satisfy.

Every attack in MCPGuard's offensive module is a ``Payload`` subclass. The base
class fixes a two-phase contract the test harness depends on:

    fire(session)      -> deliver the attack against a live MCP session
    verify_success()   -> inspect what happened and decide if it landed

Delivery and verification are deliberately separate methods so a payload can
carry state (for example, the server's response) from one phase to the next, and
so the harness can run the same payload against the raw server ("confirmed") and
again through the gateway ("blocked") to produce the before/after demo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from mcp import ClientSession


@dataclass(frozen=True)
class PayloadResult:
    """Verdict for a single payload after it has been fired and verified.

    Attributes:
        confirmed: True when the exploit executed and the attacker's objective
            was achieved; False when it did not (blocked, errored, or no-op).
        detail: Human-readable evidence for the verdict, surfaced in the report.
    """

    confirmed: bool
    detail: str


class Payload(ABC):
    """Abstract base for every attack payload.

    Subclasses override the three metadata attributes and implement both phases
    of the contract. Because ``Payload`` is abstract, forgetting to implement
    ``fire`` or ``verify_success`` raises ``TypeError`` at instantiation rather
    than failing silently mid-run.
    """

    name: str = ""
    owasp_category: str = ""
    description: str = ""

    @abstractmethod
    async def fire(self, session: ClientSession) -> None:
        """Deliver the attack against a live, initialized MCP session.

        The harness owns the session and decides what it points at: the
        vulnerable server directly (for the "before" run) or the MCPGuard proxy
        (for the "after" run). The payload does not know or care which.

        Args:
            session: An initialized MCP client session connected to the target.
        """

    @abstractmethod
    def verify_success(self) -> PayloadResult:
        """Decide whether the exploit executed, based on state from ``fire``.

        Returns:
            A ``PayloadResult`` whose ``confirmed`` flag is True when the
            attacker's objective was achieved.
        """
