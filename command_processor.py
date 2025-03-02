import re
from typing import Dict, List, Optional, Tuple
from drone import MoveAction
from environment import GridEnvironment

class CommandProcessor:
    """Processes text commands and converts them to drone actions"""
    
    def __init__(self, drones=None):
        self.drones = drones or []
        # Map of drone IDs to drone objects
        self.drone_map = {drone.drone_id: drone for drone in self.drones}
    
    def set_drones(self, drones):
        """Update the list of drones"""
        self.drones = drones
        self.drone_map = {drone.drone_id: drone for drone in self.drones}
    
    def process_command(self, command_text: str, environment: GridEnvironment) -> bool:
        """Process a text command and apply it to drones"""
        print(f"Processing command: {command_text}")
        
        # Try to extract drone ID and movement commands using regex
        # Pattern to match: "drone(\s*)(\d+)" to capture both "drone 1" and "drone1" formats
        drone_pattern = r"drone\s*(\d+)"
        
        # Find drone ID
        drone_match = re.search(drone_pattern, command_text.lower())
        if not drone_match:
            print("No drone ID found in command")
            return False
        
        drone_id = int(drone_match.group(1))
        if drone_id not in self.drone_map:
            print(f"Drone {drone_id} not found")
            return False
        
        drone = self.drone_map[drone_id]
        
        # Find all movement commands
        movement_pattern = r"(up|down|left|right)\s*=\s*(\d+)"
        movement_matches = re.findall(movement_pattern, command_text.lower())
        if not movement_matches:
            print("No movement commands found")
            return False
        
        # Clear drone's current behavior and actions
        drone.clear_behavior()
        drone.clear_actions()
        
        # Add movement actions
        for direction, steps_str in movement_matches:
            steps = int(steps_str)
            for _ in range(steps):
                drone.add_action(MoveAction(direction))
        
        print(f"Command executed: Drone {drone_id} will move {movement_matches}")
        return True 