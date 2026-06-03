"""Redfish EventService — subscriptions and test events.

Endpoint: /redfish/v1/EventService
Supports HTTP(S) push-style event delivery to external destinations.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..client import KaytusClient

_EVENT_SVC  = "/redfish/v1/EventService"
_SUBS       = "/redfish/v1/EventService/Subscriptions"

EVENT_FORMATS = ["Event", "MetricReport"]
REGISTRY_PREFIXES = ["Base", "OpenBMC", "TaskEvent"]


class EventsModule:
    def __init__(self, client: "KaytusClient"):
        self._c = client

    def info(self) -> dict:
        """Full EventService resource."""
        return self._c.get(_EVENT_SVC)

    def summary(self) -> dict:
        """Concise EventService status and subscription count."""
        d = self.info()
        subs = self._c.get(_SUBS)
        return {
            "enabled":          d.get("ServiceEnabled"),
            "retry_attempts":   d.get("DeliveryRetryAttempts"),
            "retry_interval_s": d.get("DeliveryRetryIntervalSeconds"),
            "event_formats":    d.get("EventFormatTypes", []),
            "subscription_count": subs.get("Members@odata.count", 0),
        }

    def subscriptions(self) -> list[dict]:
        """Return all event subscriptions (full detail)."""
        col = self._c.get(_SUBS)
        result = []
        for m in col.get("Members", []):
            try:
                result.append(self._c.get(m["@odata.id"]))
            except Exception:
                pass
        return result

    def subscribe(
        self,
        destination: str,
        *,
        context: str = "KaytusSDK",
        event_format: str = "Event",
        registry_prefixes: Optional[list[str]] = None,
        protocol: str = "Redfish",
        verify_certificate: bool = False,
    ) -> dict:
        """
        Create an event subscription (HTTP/HTTPS push).

        destination: URL that will receive POST event payloads.
        event_format: Event | MetricReport
        registry_prefixes: e.g. ["Base", "TaskEvent"] — None = all
        """
        if event_format not in EVENT_FORMATS:
            raise ValueError(f"event_format must be one of {EVENT_FORMATS}")
        payload: dict = {
            "Destination":   destination,
            "Context":       context,
            "EventFormatType": event_format,
            "Protocol":      protocol,
        }
        if registry_prefixes is not None:
            payload["RegistryPrefixes"] = registry_prefixes
        return self._c.post(_SUBS, payload)

    def unsubscribe(self, subscription_id: str) -> dict:
        """Delete an event subscription by ID."""
        return self._c.delete(f"{_SUBS}/{subscription_id}")

    def unsubscribe_all(self) -> int:
        """Delete all subscriptions. Returns count deleted."""
        count = 0
        for sub in self.subscriptions():
            sub_id = sub.get("Id")
            if sub_id:
                try:
                    self.unsubscribe(sub_id)
                    count += 1
                except Exception:
                    pass
        return count

    def configure(
        self,
        *,
        retry_attempts: Optional[int] = None,
        retry_interval_s: Optional[int] = None,
    ) -> dict:
        """Update EventService delivery retry settings."""
        payload: dict = {}
        if retry_attempts is not None:
            payload["DeliveryRetryAttempts"] = retry_attempts
        if retry_interval_s is not None:
            payload["DeliveryRetryIntervalSeconds"] = retry_interval_s
        return self._c.patch(_EVENT_SVC, payload)

    def test_event(
        self,
        *,
        event_type: str = "Alert",
        message_id: str = "Base.1.0.GeneralError",
    ) -> dict:
        """Send a test event via EventService.SubmitTestEvent."""
        return self._c.post(
            f"{_EVENT_SVC}/Actions/EventService.SubmitTestEvent",
            {"EventType": event_type, "MessageId": message_id},
        )
