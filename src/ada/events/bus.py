"""
Event Bus - Central event dispatching system
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Union
import heapq
import weakref

from ada.events.base import Event, EventType, EventPriority

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """Event subscription details"""
    id: str
    event_types: Set[EventType]
    callback: Callable
    filter_func: Optional[Callable[[Event], bool]] = None
    priority: int = 0
    once: bool = False
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    call_count: int = 0


class EventBus:
    """
    Central event bus for publishing and subscribing to events.

    Features:
    - Type-based subscription
    - Priority-based dispatching
    - Filter functions
    - One-time subscriptions
    - Async support
    - Event history (optional)
    """

    def __init__(self, history_size: int = 100):
        self._subscriptions: Dict[EventType, List[Subscription]] = defaultdict(list)
        self._wildcard_subscriptions: List[Subscription] = []
        self._subscription_by_id: Dict[str, Subscription] = {}
        self._history: List[Event] = []
        self._history_size = history_size
        self._lock = asyncio.Lock()
        self._processing = False
        self._event_queue: asyncio.Queue = None

    async def start(self):
        """Start the event processing loop"""
        self._event_queue = asyncio.Queue()
        self._processing = True

        # Start processing task
        asyncio.create_task(self._process_loop())
        logger.info("Event bus started")

    async def stop(self):
        """Stop the event processing loop"""
        self._processing = False
        if self._event_queue:
            await self._event_queue.put(None)  # Signal to stop
        logger.info("Event bus stopped")

    def subscribe(
        self,
        event_types: Union[EventType, List[EventType], None],
        callback: Callable[[Event], Any],
        filter_func: Callable[[Event], bool] = None,
        priority: int = 0,
        once: bool = False
    ) -> str:
        """
        Subscribe to events.

        Args:
            event_types: Event type(s) to subscribe to, or None for all
            callback: Function to call when event occurs
            filter_func: Optional filter function
            priority: Higher priority = called first
            once: Remove after first call

        Returns:
            Subscription ID for unsubscribing
        """
        import uuid

        sub_id = str(uuid.uuid4())

        if event_types is None:
            # Subscribe to all events
            types_set = set()
            subscription = Subscription(
                id=sub_id,
                event_types=types_set,
                callback=callback,
                filter_func=filter_func,
                priority=priority,
                once=once,
            )
            self._wildcard_subscriptions.append(subscription)
        else:
            # Subscribe to specific types
            if isinstance(event_types, EventType):
                types_set = {event_types}
            else:
                types_set = set(event_types)

            subscription = Subscription(
                id=sub_id,
                event_types=types_set,
                callback=callback,
                filter_func=filter_func,
                priority=priority,
                once=once,
            )

            for event_type in types_set:
                self._subscriptions[event_type].append(subscription)

        self._subscription_by_id[sub_id] = subscription
        logger.debug(f"Created subscription {sub_id} for {event_types}")

        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription"""
        if subscription_id not in self._subscription_by_id:
            return False

        subscription = self._subscription_by_id[subscription_id]
        subscription.active = False

        # Remove from type-specific lists
        for event_type in subscription.event_types:
            if event_type in self._subscriptions:
                self._subscriptions[event_type] = [
                    s for s in self._subscriptions[event_type]
                    if s.id != subscription_id
                ]

        # Remove from wildcard list
        self._wildcard_subscriptions = [
            s for s in self._wildcard_subscriptions
            if s.id != subscription_id
        ]

        del self._subscription_by_id[subscription_id]
        logger.debug(f"Removed subscription {subscription_id}")

        return True

    async def publish(self, event: Event) -> int:
        """
        Publish an event to all matching subscribers.

        Args:
            event: Event to publish

        Returns:
            Number of handlers that processed the event
        """
        if self._event_queue:
            await self._event_queue.put(event)
            return 0  # Will be processed asynchronously
        else:
            return await self._dispatch_event(event)

    def publish_sync(self, event: Event) -> int:
        """Synchronous publish (creates async task)"""
        if asyncio.get_event_loop().is_running():
            asyncio.create_task(self.publish(event))
        return 0

    async def _process_loop(self):
        """Event processing loop"""
        while self._processing:
            try:
                event = await self._event_queue.get()

                if event is None:
                    break

                await self._dispatch_event(event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def _dispatch_event(self, event: Event) -> int:
        """Dispatch event to matching subscriptions"""
        # Add to history
        if self._history_size > 0:
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history.pop(0)

        # Collect matching subscriptions
        matching = []

        # Type-specific subscriptions
        if event.event_type in self._subscriptions:
            matching.extend(self._subscriptions[event.event_type])

        # Wildcard subscriptions
        matching.extend(self._wildcard_subscriptions)

        # Sort by priority
        matching.sort(key=lambda s: s.priority, reverse=True)

        # Dispatch
        dispatch_count = 0
        to_remove = []

        for subscription in matching:
            if not subscription.active:
                continue

            if event.propagation_stopped:
                break

            # Apply filter
            if subscription.filter_func:
                try:
                    if not subscription.filter_func(event):
                        continue
                except Exception as e:
                    logger.error(f"Filter error: {e}")
                    continue

            # Call callback
            try:
                result = subscription.callback(event)
                if asyncio.iscoroutine(result):
                    await result

                subscription.call_count += 1
                dispatch_count += 1

                if subscription.once:
                    to_remove.append(subscription.id)

            except Exception as e:
                logger.error(f"Callback error for {subscription.id}: {e}")

        # Remove one-time subscriptions
        for sub_id in to_remove:
            self.unsubscribe(sub_id)

        event.mark_handled()
        return dispatch_count

    def get_history(self, event_type: EventType = None, limit: int = 10) -> List[Event]:
        """Get event history"""
        events = self._history

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events[-limit:]

    def clear_history(self):
        """Clear event history"""
        self._history.clear()

    def get_subscription_count(self, event_type: EventType = None) -> int:
        """Get number of active subscriptions"""
        if event_type:
            return len([s for s in self._subscriptions.get(event_type, []) if s.active])
        return len([s for s in self._subscription_by_id.values() if s.active])

    # Context manager for temporary subscriptions
    def temporary_subscription(
        self,
        event_types: Union[EventType, List[EventType]],
        callback: Callable,
        **kwargs
    ):
        """Context manager for temporary subscription"""
        return _TemporarySubscription(self, event_types, callback, **kwargs)


class _TemporarySubscription:
    """Context manager for temporary event subscription"""

    def __init__(self, bus: EventBus, event_types, callback, **kwargs):
        self.bus = bus
        self.event_types = event_types
        self.callback = callback
        self.kwargs = kwargs
        self.subscription_id = None

    def __enter__(self):
        self.subscription_id = self.bus.subscribe(
            self.event_types,
            self.callback,
            **self.kwargs
        )
        return self.subscription_id

    def __exit__(self, *args):
        if self.subscription_id:
            self.bus.unsubscribe(self.subscription_id)

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, *args):
        self.__exit__(*args)
