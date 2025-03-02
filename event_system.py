from typing import Dict, List, Callable, Any

class Event:
    """Base class for events in the simulation"""
    def __init__(self, event_type: str, **kwargs):
        self.event_type = event_type
        self.data = kwargs

class EventCallback:
    """Callback for event handlers"""
    def __init__(self, callback_function: Callable[[Event], None]):
        self.callback_function = callback_function
    
    def execute(self, event: Event):
        self.callback_function(event)

class EventManager:
    """Manages events and callbacks in the simulation"""
    def __init__(self):
        self.callbacks = {}
    
    def register(self, event_type: str):
        """Decorator to register a callback for an event type"""
        def decorator(callback):
            if event_type not in self.callbacks:
                self.callbacks[event_type] = []
            self.callbacks[event_type].append(callback)
            return callback
        return decorator
    
    def on(self, event_type: str, callback: Callable):
        """Register a callback for an event type"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def trigger(self, event_type: str, **kwargs):
        """Trigger an event with the provided data"""
        event = Event(event_type, **kwargs)
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                callback(event)
    
    def clear_all(self):
        """Clear all registered callbacks"""
        self.callbacks = {} 