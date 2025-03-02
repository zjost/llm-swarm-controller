from typing import List, Dict, Any, Optional, Callable
from drone import Action, MoveAction, WaitAction, ScanAction
from environment import Position

class Behavior:
    """Base class for complex drone behaviors"""
    def __init__(self):
        self.completed = False
    
    def start(self, drone):
        """Initialize the behavior"""
        pass
    
    def update(self, drone, environment) -> bool:
        """Update the behavior, return True if completed"""
        raise NotImplementedError
    
    def stop(self, drone):
        """Cleanup when behavior is stopped"""
        pass

class MoveToBehavior(Behavior):
    """Move to a specific position"""
    def __init__(self, target_position: Position):
        super().__init__()
        self.target_position = target_position
        self.path = []
        self.current_action = None
    
    def start(self, drone):
        # Simple path planning (direct route)
        self._plan_path(drone)
    
    def _plan_path(self, drone):
        """Simple path planning from current position to target"""
        self.path = []
        current = drone.position
        
        while current.x != self.target_position.x or current.y != self.target_position.y:
            if current.x < self.target_position.x:
                self.path.append(MoveAction("right"))
                current = Position(current.x + 1, current.y)
            elif current.x > self.target_position.x:
                self.path.append(MoveAction("left"))
                current = Position(current.x - 1, current.y)
            elif current.y < self.target_position.y:
                self.path.append(MoveAction("down"))
                current = Position(current.x, current.y + 1)
            elif current.y > self.target_position.y:
                self.path.append(MoveAction("up"))
                current = Position(current.x, current.y - 1)
    
    def update(self, drone, environment) -> bool:
        if self.completed:
            return True
        
        # Check if we've reached the destination
        if drone.position.x == self.target_position.x and drone.position.y == self.target_position.y:
            self.completed = True
            return True
        
        # Execute next action in path
        if self.current_action is None and self.path:
            self.current_action = self.path.pop(0)
        
        if self.current_action:
            if self.current_action.execute(drone, environment):
                self.current_action = None
                # If action blocked, replan path
                if drone.position.x != self.target_position.x or drone.position.y != self.target_position.y:
                    self._plan_path(drone)
        
        return False

class ExploreBehavior(Behavior):
    """Explore the environment randomly"""
    def __init__(self, steps: int = -1):
        super().__init__()
        self.steps = steps  # -1 means explore indefinitely
        self.current_step = 0
        self.directions = ["up", "down", "left", "right"]
        self.current_action = None
    
    def update(self, drone, environment) -> bool:
        if self.completed:
            return True
        
        if self.steps > 0 and self.current_step >= self.steps:
            self.completed = True
            return True
        
        if self.current_action is None:
            import random
            direction = random.choice(self.directions)
            self.current_action = MoveAction(direction)
        
        if self.current_action.execute(drone, environment):
            self.current_action = None
            self.current_step += 1
        
        return False

class PatrolBehavior(Behavior):
    """Patrol between a list of positions"""
    def __init__(self, waypoints: List[Position], loops: int = -1):
        super().__init__()
        self.waypoints = waypoints
        self.current_waypoint_index = 0
        self.loops = loops  # -1 means infinite
        self.current_loop = 0
        self.current_move_behavior = None
    
    def update(self, drone, environment) -> bool:
        if self.completed:
            return True
        
        # Check if we need to create a new MoveTo behavior
        if self.current_move_behavior is None or self.current_move_behavior.completed:
            # Get next waypoint
            target = self.waypoints[self.current_waypoint_index]
            self.current_move_behavior = MoveToBehavior(target)
            self.current_move_behavior.start(drone)
            
            # Update waypoint index for next time
            self.current_waypoint_index = (self.current_waypoint_index + 1) % len(self.waypoints)
            
            # Check if we've completed a loop
            if self.current_waypoint_index == 0:
                self.current_loop += 1
                if 0 <= self.loops <= self.current_loop:
                    self.completed = True
                    return True
        
        # Update the current MoveTo behavior
        self.current_move_behavior.update(drone, environment)
        return False

class SearchBehavior(Behavior):
    """Search behavior that combines random movement with periodic scanning"""
    def __init__(self, steps_between_scans: int = 1, scan_range: int = 1, max_steps: int = -1):
        super().__init__()
        self.steps_between_scans = steps_between_scans
        self.scan_range = scan_range
        self.max_steps = max_steps  # -1 means infinite
        self.step_count = 0
        self.total_steps = 0
        self.current_action = None
    
    def update(self, drone, environment) -> bool:
        if self.completed:
            return True
            
        # Check if we've hit our maximum steps
        if self.max_steps > 0 and self.total_steps >= self.max_steps:
            self.completed = True
            return True
            
        # If no current action, decide what to do next
        if self.current_action is None:
            # Time to scan?
            if self.step_count >= self.steps_between_scans:
                self.current_action = ScanAction(range=self.scan_range)
                self.step_count = 0
            else:
                # Choose a random direction to move
                import random
                directions = ["up", "down", "left", "right"]
                self.current_action = MoveAction(random.choice(directions))
                
        # Execute the current action
        if self.current_action.execute(drone, environment):
            # Action completed
            if isinstance(self.current_action, MoveAction):
                self.step_count += 1
                self.total_steps += 1
            self.current_action = None
            
        return False

class BehaviorFactory:
    """Factory for creating behaviors from parameters"""
    @staticmethod
    def create_behavior(behavior_type: str, params: Dict[str, Any]) -> Optional[Behavior]:
        if behavior_type == "move_to":
            return MoveToBehavior(Position(params["x"], params["y"]))
        elif behavior_type == "explore":
            return ExploreBehavior(params.get("steps", -1))
        elif behavior_type == "patrol":
            waypoints = [Position(wp["x"], wp["y"]) for wp in params["waypoints"]]
            return PatrolBehavior(waypoints, params.get("loops", -1))
        elif behavior_type == "search":
            return SearchBehavior(
                steps_between_scans=params.get("steps_between_scans", 1),
                scan_range=params.get("scan_range", 1),
                max_steps=params.get("max_steps", -1)
            )
        else:
            print(f"Unknown behavior type: {behavior_type}")
            return None 