import pygame
from typing import List, Dict, Any, Optional
from environment import Position, Entity, GridEnvironment
from event_system import Event

# Movement directions as position deltas
DIRECTIONS = {
    "up": Position(0, -1),
    "down": Position(0, 1),
    "left": Position(-1, 0),
    "right": Position(1, 0),
    "stay": Position(0, 0)
}

class Action:
    """Base class for primitive actions a drone can take"""
    def __init__(self):
        self.completed = False
    
    def execute(self, drone, environment) -> bool:
        """Execute the action, return True if completed"""
        raise NotImplementedError
    
    def reset(self):
        """Reset the action state"""
        self.completed = False

class MoveAction(Action):
    """Move in a specified direction"""
    def __init__(self, direction: str):
        super().__init__()
        self.direction = direction
    
    def execute(self, drone, environment) -> bool:
        if self.completed:
            return True
        
        if self.direction not in DIRECTIONS:
            print(f"Invalid direction: {self.direction}")
            self.completed = True
            return True
        
        delta = DIRECTIONS[self.direction]
        new_position = drone.position + delta
        
        if environment.is_valid_position(new_position):
            drone.position = new_position
            self.completed = True
            environment.event_manager.trigger("drone_moved", drone=drone, position=new_position)
            return True
        else:
            # Can't move there
            self.completed = True
            environment.event_manager.trigger("movement_blocked", drone=drone, direction=self.direction)
            return True

class WaitAction(Action):
    """Wait for a specified number of ticks"""
    def __init__(self, ticks: int = 1):
        super().__init__()
        self.ticks = ticks
        self.current_tick = 0
    
    def execute(self, drone, environment) -> bool:
        if self.completed:
            return True
        
        self.current_tick += 1
        if self.current_tick >= self.ticks:
            self.completed = True
            return True
        return False
    
    def reset(self):
        super().reset()
        self.current_tick = 0

class ScanAction(Action):
    """Scan the surrounding area for entities"""
    def __init__(self, range: int = 1):
        super().__init__()
        self.range = range
    
    def execute(self, drone, environment) -> bool:
        if self.completed:
            return True
        
        detected_entities = []
        for dx in range(-self.range, self.range + 1):
            for dy in range(-self.range, self.range + 1):
                scan_pos = Position(drone.position.x + dx, drone.position.y + dy)
                if environment.is_valid_position(scan_pos):
                    entities = environment.get_entities_at(scan_pos)
                    detected_entities.extend(entities)
        
        # Trigger scan completed event with results
        environment.event_manager.trigger(
            "scan_completed", 
            drone=drone, 
            entities=detected_entities
        )
        
        self.completed = True
        return True

class Detector:
    """A detector that can be attached to a drone to automatically detect entities within a field of view"""
    def __init__(self, range: int = 1):
        self.range = range
        self.drone = None
    
    def attach_to(self, drone):
        """Attach this detector to a specific drone"""
        self.drone = drone
    
    def check(self, environment):
        """Check for entities in range and trigger events if targets are found"""
        if not self.drone:
            return []
            
        detected_entities = []
        for dx in range(-self.range, self.range + 1):
            for dy in range(-self.range, self.range + 1):
                scan_pos = Position(self.drone.position.x + dx, self.drone.position.y + dy)
                if environment.is_valid_position(scan_pos):
                    entities = environment.get_entities_at(scan_pos)
                    detected_entities.extend(entities)
        
        # Filter out the drone itself and other non-target entities
        targets = [e for e in detected_entities if e.entity_type == 'target' and e.id != self.drone.id]
        
        if targets:
            # Trigger target detected event
            environment.event_manager.trigger(
                "target_detected", 
                drone=self.drone, 
                targets=targets
            )
            
        return targets

class Drone(Entity):
    """Represents a drone in the simulation"""
    def __init__(self, position: Position, drone_id: int):
        super().__init__(position, "drone")
        self.drone_id = drone_id
        self.color = (0, 100, 255)  # Blue by default
        self.current_action: Optional[Action] = None
        self.action_queue: List[Action] = []
        self.current_behavior = None
        self.detector = None  # New property for the detector
    
    def set_detector(self, detector: Detector):
        """Attach a detector to this drone"""
        self.detector = detector
        detector.attach_to(self)
    
    def update(self, environment):
        """Update drone state based on current action or behavior"""
        if self.current_behavior:
            # Let behavior manage actions
            self.current_behavior.update(self, environment)
        elif self.current_action:
            # Execute current action
            if self.current_action.execute(self, environment):
                self.current_action = None
                if self.action_queue:
                    self.current_action = self.action_queue.pop(0)
        
        # Always check for targets if we have a detector
        if self.detector:
            self.detector.check(environment)
    
    def render(self, surface, cell_size):
        """Render the drone on the surface"""
        x = self.position.x * cell_size
        y = self.position.y * cell_size
        pygame.draw.rect(surface, self.color, (x + 2, y + 2, cell_size - 4, cell_size - 4))
        
        # Draw drone ID
        font = pygame.font.SysFont(None, 24)
        text = font.render(str(self.drone_id), True, (255, 255, 255))
        text_rect = text.get_rect(center=(x + cell_size // 2, y + cell_size // 2))
        surface.blit(text, text_rect)
    
    def add_action(self, action: Action):
        """Add an action to the queue"""
        if self.current_action is None:
            self.current_action = action
        else:
            self.action_queue.append(action)
    
    def clear_actions(self):
        """Clear all pending actions"""
        self.action_queue = []
        self.current_action = None
    
    def set_behavior(self, behavior):
        """Set the current behavior"""
        self.clear_actions()
        self.current_behavior = behavior
        if behavior:
            behavior.start(self)
    
    def clear_behavior(self):
        """Clear the current behavior"""
        if self.current_behavior:
            self.current_behavior.stop(self)
        self.current_behavior = None 