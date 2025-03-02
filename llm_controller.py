import json
import random
import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
import traceback
import openai
from behavior import BehaviorFactory, MoveToBehavior, ExploreBehavior, PatrolBehavior, SearchBehavior
from drone import MoveAction
from event_system import EventCallback, Event
from environment import Position

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LLMController")

class LLMController:
    """Controller for integrating LLM with the simulation"""
    def __init__(self, api_key: str = None, environment=None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.environment = environment
        
        # Initialize OpenAI client if API key is available
        if self.api_key:
            openai.api_key = self.api_key
            self.client = openai.Client(api_key=self.api_key)
    
    def _generate_random_position(self):
        """Generate a random position within the environment's bounds"""
        if not self.environment:
            return {"x": random.randint(0, 10), "y": random.randint(0, 10)}
        
        return {
            "x": random.randint(0, self.environment.width - 1),
            "y": random.randint(0, self.environment.height - 1)
        }
    
    async def process_goal(self, goal_text: str, environment, drones: List, use_mock: bool = False) -> Dict:
        """Process a natural language goal and generate JSON commands for drones"""
        self.environment = environment
        
        logger.info(f"Processing goal: {goal_text}")
        
        if use_mock:
            logger.info("Using mock LLM - would normally generate commands for the drones here")
            
            # Create an ExploreBehavior for all drones as a mock response
            for drone in drones:
                explore_behavior = ExploreBehavior(steps=-1)  # Explore indefinitely
                drone.set_behavior(explore_behavior)
                logger.info(f"Set drone {drone.drone_id} to explore behavior")
            
            return {"status": "success", "message": "Drones are now exploring the environment"}
        
        # Real LLM implementation
        try:
            # Generate the behavior command
            behavior_command = await self._generate_behavior_command(goal_text, drones, environment)
            
            if behavior_command:
                try:
                    self.execute_behavior_command(behavior_command, environment, drones)
                    logger.info(f"Successfully executed command: {json.dumps(behavior_command, indent=2)}")
                    return {"status": "success", "message": "Command executed successfully"}
                except Exception as e:
                    logger.error(f"Error executing command: {e}")
                    traceback.print_exc()
                    return {"status": "error", "message": f"Error executing command: {str(e)}"}
            else:
                return {"status": "error", "message": "Could not parse command"}
                
        except Exception as e:
            logger.error(f"Error in LLM processing: {e}")
            traceback.print_exc()
            return {"status": "error", "message": f"Error processing command: {str(e)}"}
    
    async def _generate_behavior_command(self, goal_text: str, drones: List, environment) -> Optional[Dict]:
        """Use LLM to generate appropriate behavior commands based on goal"""
        # Create a prompt for the LLM
        system_prompt = self._generate_goal_system_prompt(drones, environment)
        user_prompt = goal_text
        
        logger.info("Generating LLM prompt for behavior planning")
        
        if not self.api_key:
            # Fallback to simple parsing for testing without API key
            logger.warning("No API key available - using simple fallback command generation")
            return self._simple_goal_parser(goal_text, drones)
        
        try:
            # Make the API call to OpenAI
            logger.info("Calling OpenAI API")
            response = await self._call_openai_api(system_prompt, user_prompt)
            logger.info(f"Received LLM response: {json.dumps(response, indent=2)}")
            return response
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            traceback.print_exc()
            return None
    
    def _generate_goal_system_prompt(self, drones: List, environment) -> str:
        """Generate a system prompt for the LLM to plan behaviors based on goals"""
        available_drones = ", ".join([f"drone{drone.drone_id}" for drone in drones])
        env_width = environment.width
        env_height = environment.height
        
        system_prompt = f"""You are a drone swarm controller that translates high-level goals into specific behaviors for drones.
Your task is to analyze the user's goal and generate appropriate behavior commands for the drones.

ENVIRONMENT INFORMATION:
- Grid size: {env_width}x{env_height}
- Available drones: {available_drones}

AVAILABLE BEHAVIORS:
1. "explore" - Random exploration of the environment
   Parameters: steps (optional, -1 for indefinite)
   
2. "move_to" - Move to a specific position
   Parameters: x (0-{env_width-1}), y (0-{env_height-1})
   
3. "patrol" - Patrol between multiple waypoints
   Parameters: waypoints (list of positions), loops (optional, -1 for indefinite)
   
4. "search" - Systematic search with periodic scanning
   Parameters: steps_between_scans, scan_range, max_steps (optional)

You must respond with a valid JSON object that follows one of these structures:

For explore behavior:
```json
{{
    "behavior_type": "explore",
    "targets": [
        {{"drone_id": <drone_id_number>}},
        ...
        ],
    "parameters": {{
        
    }}
}}
```

For move_to behavior:
```json
{{
    "behavior_type": "move_to",
    "targets": [
        {{"drone_id": <drone_id_number>}},
        ...
        ],
    "parameters": {{
        "x": <x_coordinate>,
        "y": <y_coordinate>
    }}
}}
```
For patrol behavior:
```json
{{
    "behavior_type": "patrol",
    "targets": [
        {{"drone_id": <drone_id_number>}},
        ...
        ],
    "parameters": {{
        "waypoints": [
            {{"x": <x1>, "y": <y1>}},
            {{"x": <x2>, "y": <y2>}},
            ...
        ],
        "loops": <number_of_loops_or_-1>
    }}
}}
```
For search behavior:
```json
{{
    "behavior_type": "search",
    "targets": [
        {{"drone_id": <drone_id_number>}},
        ...
    ],
    "parameters": {{
        "steps_between_scans": <steps>,
        "scan_range": <range>,
        "max_steps": <steps_or_-1>
    }}
}}
```
You can also specify different behaviors for different drones using multiple commands:
```json
[
    {{behavior_command_1}},
    {{behavior_command_2}},
    ...
]
```

RESPONSE FORMAT:
Provide ONLY the JSON object with no additional text or explanation. Do not include the code block formatting in your response.
If you cannot understand the goal, respond with: {{"error": "Could not parse goal"}}
"""
        logger.debug(f"Generated system prompt: {system_prompt}")
        return system_prompt
    
    async def _call_openai_api(self, system_prompt: str, user_prompt: str) -> Dict:
        """Make an API call to OpenAI using the official client"""
        try:
            # Call OpenAI API using async client
            logger.info("Sending prompt to OpenAI")
            logger.debug(f"System prompt: {system_prompt}")
            logger.debug(f"User prompt: {user_prompt}")
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",  # or other appropriate model
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1  # Low temperature for more deterministic outputs
            )
            
            # Extract the JSON content from the response
            content = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {content}")
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Error in OpenAI API call: {e}")
            traceback.print_exc()
            raise
    
    def _simple_goal_parser(self, text: str, drones: List) -> Dict:
        """A simple rule-based parser for goals when no API key is available"""
        text = text.lower()
        
        # Check for specific goal patterns
        if any(word in text for word in ["search", "find", "look", "scan", "detect"]):
            return {
                "behavior_type": "search",
                "targets": [{"drone_id": drone.drone_id} for drone in drones],
                "parameters": {
                    "steps_between_scans": 2,
                    "scan_range": 2,
                    "max_steps": -1
                }
            }
        
        if any(word in text for word in ["explore", "roam", "wander"]):
            return {
                "behavior_type": "explore",
                "targets": [{"drone_id": drone.drone_id} for drone in drones],
                "parameters": {
                    "steps": -1
                }
            }
        
        if any(word in text for word in ["patrol", "guard", "watch"]):
            # Create a simple patrol around the center
            center_x = self.environment.width // 2
            center_y = self.environment.height // 2
            radius = min(3, min(center_x, center_y))
            
            return {
                "behavior_type": "patrol",
                "targets": [{"drone_id": drone.drone_id} for drone in drones],
                "parameters": {
                    "waypoints": [
                        {"x": center_x - radius, "y": center_y - radius},
                        {"x": center_x + radius, "y": center_y - radius},
                        {"x": center_x + radius, "y": center_y + radius},
                        {"x": center_x - radius, "y": center_y + radius}
                    ],
                    "loops": -1
                }
            }
        
        # Default to exploration
        return {
            "behavior_type": "explore",
            "targets": [{"drone_id": drone.drone_id} for drone in drones],
            "parameters": {
                "steps": -1
            }
        }
    
    def execute_behavior_command(self, command_json: Dict, environment, drones: List) -> bool:
        """Execute a behavior command"""
        try:
            # Check if we have multiple commands
            if isinstance(command_json, list):
                for cmd in command_json:
                    self._execute_single_behavior_command(cmd, environment, drones)
                return True
            else:
                return self._execute_single_behavior_command(command_json, environment, drones)
                
        except Exception as e:
            logger.error(f"Error executing behavior command: {e}")
            traceback.print_exc()
            return False
    
    def _execute_single_behavior_command(self, command_json: Dict, environment, drones: List) -> bool:
        """Execute a single behavior command"""
        try:
            # Get behavior type and parameters
            behavior_type = command_json.get("behavior_type")
            targets = command_json.get("targets", [])
            parameters = command_json.get("parameters", {})
            
            if not behavior_type or not targets:
                logger.error("Invalid command: missing behavior_type or targets")
                return False
            
            # Find target drones
            target_drones = []
            for target in targets:
                drone_id = target.get("drone_id")
                if not drone_id:
                    continue
                    
                # Find the drone object
                drone = None
                for d in drones:
                    if d.drone_id == drone_id:
                        drone = d
                        break
                
                if drone:
                    target_drones.append(drone)
                else:
                    logger.warning(f"Drone with ID {drone_id} not found")
            
            if not target_drones:
                logger.error("No valid target drones found")
                return False
            
            # Create and apply behavior
            for drone in target_drones:
                behavior = BehaviorFactory.create_behavior(behavior_type, parameters)
                if behavior:
                    # Clear existing actions and behaviors
                    drone.clear_behavior()
                    drone.clear_actions()
                    
                    # Set new behavior
                    drone.set_behavior(behavior)
                    logger.info(f"Set drone {drone.drone_id} to {behavior_type} behavior")
                else:
                    logger.error(f"Failed to create behavior of type {behavior_type}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing behavior command: {e}")
            traceback.print_exc()
            return False
            
    # Keep existing methods for backward compatibility
    def _is_likely_movement_command(self, text: str) -> bool:
        """Determine if text is likely a movement command"""
        movement_keywords = ["move", "go", "take", "send", "navigate", "direct", "guide", "fly", "left", 
                            "right", "up", "down", "north", "south", "east", "west"]
        drone_keywords = ["drone", "uav", "quadcopter", "copter"]
        
        text_lower = text.lower()
        has_movement = any(keyword in text_lower for keyword in movement_keywords)
        has_drone = any(keyword in text_lower for keyword in drone_keywords)
        
        return has_movement and has_drone
    
    def execute_json_command(self, command_json: Dict, environment, drones: List) -> bool:
        """Execute a JSON command (maintained for backward compatibility)"""
        try:
            command_type = command_json.get("command_type")
            
            if command_type == "move":
                return self._execute_move_command(command_json, environment, drones)
            else:
                logger.warning(f"Unknown command type: {command_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing JSON command: {e}")
            traceback.print_exc()
            return False
    
    def _execute_move_command(self, command_json: Dict, environment, drones: List) -> bool:
        """Execute a move command"""
        try:
            # Get target drone
            target = command_json.get("target", {})
            drone_id = target.get("drone_id")
            
            # Find the drone object
            drone = None
            for d in drones:
                if d.drone_id == drone_id:
                    drone = d
                    break
            
            if not drone:
                logger.warning(f"Drone with ID {drone_id} not found")
                return False
            
            # Clear existing actions and behaviors
            drone.clear_behavior()
            drone.clear_actions()
            
            # Process movements
            movements = command_json.get("parameters", {}).get("movements", [])
            for movement in movements:
                direction = movement.get("direction")
                steps = movement.get("steps")
                
                if direction not in ["up", "down", "left", "right"]:
                    logger.warning(f"Invalid direction: {direction}")
                    continue
                
                # Add movement actions to the drone
                for _ in range(steps):
                    drone.add_action(MoveAction(direction))
            
            logger.info(f"Command executed: Drone {drone_id} will perform {len(movements)} movement(s)")
            return True
            
        except Exception as e:
            logger.error(f"Error executing move command: {e}")
            traceback.print_exc()
            return False
            