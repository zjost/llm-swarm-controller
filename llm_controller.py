import json
import random
import os
import asyncio
from typing import Dict, List, Any, Optional
import traceback
import openai
from behavior import BehaviorFactory, MoveToBehavior
from drone import MoveAction
from event_system import EventCallback, Event

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
        
        if use_mock:
            print(f"Processing goal: {goal_text}")
            print("LLM would normally generate commands for the drones here")
            
            # For demonstration, create a mock JSON command
            if drones:
                drone_id = drones[0].drone_id
                command_json = {
                    "command_type": "move",
                    "target": {
                        "drone_id": drone_id
                    },
                    "parameters": {
                        "movements": [
                            {"direction": "up", "steps": 2},
                            {"direction": "right", "steps": 3}
                        ]
                    }
                }
                
                try:
                    self.execute_json_command(command_json, environment, drones)
                    print(f"Successfully issued command: {json.dumps(command_json, indent=2)}")
                except Exception as e:
                    print(f"Error issuing command: {e}")
            
            return {"status": "success", "message": "Drones are searching the environment"}
        
        # Real LLM implementation
        try:
            # Check if this is a movement command
            if self._is_likely_movement_command(goal_text):
                command_json = await self._generate_command_json(goal_text, drones)
                
                if command_json:
                    try:
                        self.execute_json_command(command_json, environment, drones)
                        print(f"Successfully issued command: {json.dumps(command_json, indent=2)}")
                        return {"status": "success", "message": "Command executed successfully"}
                    except Exception as e:
                        print(f"Error executing command: {e}")
                        traceback.print_exc()
                        return {"status": "error", "message": f"Error executing command: {str(e)}"}
                else:
                    return {"status": "error", "message": "Could not parse command"}
            else:
                # For higher-level goals, we would have more complex planning logic
                return {"status": "info", "message": "Currently only supporting movement commands"}
                
        except Exception as e:
            print(f"Error in LLM processing: {e}")
            traceback.print_exc()
            return {"status": "error", "message": f"Error processing command: {str(e)}"}
    
    def _is_likely_movement_command(self, text: str) -> bool:
        """Determine if text is likely a movement command"""
        movement_keywords = ["move", "go", "take", "send", "navigate", "direct", "guide", "fly", "left", 
                            "right", "up", "down", "north", "south", "east", "west"]
        drone_keywords = ["drone", "uav", "quadcopter", "copter"]
        
        text_lower = text.lower()
        has_movement = any(keyword in text_lower for keyword in movement_keywords)
        has_drone = any(keyword in text_lower for keyword in drone_keywords)
        
        return has_movement and has_drone
    
    async def _generate_command_json(self, command_text: str, drones: List) -> Optional[Dict]:
        """Use LLM to parse natural language command into JSON format"""
        # Create a prompt for the LLM
        system_prompt = self._generate_command_system_prompt(drones)
        user_prompt = command_text
        
        if not self.api_key:
            # Fallback to simple parsing for testing without API key
            return self._simple_command_parser(command_text, drones)
        
        try:
            # Make the API call to OpenAI
            response = await self._call_openai_api(system_prompt, user_prompt)
            return response
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            traceback.print_exc()
            return None
    
    def _generate_command_system_prompt(self, drones: List) -> str:
        """Generate a system prompt for the LLM to parse natural language into JSON commands"""
        available_drones = ", ".join([f"drone{drone.drone_id}" for drone in drones])
        
        system_prompt = f"""You are a command interpreter for a drone control system. Your task is to translate natural language
commands into structured JSON commands that the system can understand.

Available drones: {available_drones}

You must respond with a valid JSON object that follows this structure:
```json
{{
    "command_type": "move",
    "target": {{
        "drone_id": <drone_id_number>
    }},
    "parameters": {{
        "movements": [
            {{"direction": "<direction>", "steps": <number_of_steps>}},
        ...
        ]
    }}
}}
```

Where:
- <drone_id_number> is the numeric ID of the drone (1, 2, 3, etc.)
- <direction> is one of: "up", "down", "left", "right"
- <number_of_steps> is a positive integer representing the number of grid cells to move

Examples:
- "move drone1 up 3 steps" would translate to:
```json
{{
    "command_type": "move",
    "target": {{
        "drone_id": 1
    }},
    "parameters": {{
        "movements": [
            {{"direction": "up", "steps": 3}}
        ]
    }}
}}
```

- "take drone two left 2 units and down 4 cells" would translate to:
```json
{{
    "command_type": "move",
    "target": {{
        "drone_id": 2
    }},
    "parameters": {{
        "movements": [
            {{"direction": "left", "steps": 2}},
            {{"direction": "down", "steps": 4}}
        ]
    }}
}}
```

RESPONSE FORMAT:
Provide ONLY the JSON object with no additional text or explanation. Do not include the ```json code block formatting in your response.
If you cannot understand the command, respond with: {{"error": "Could not parse command"}}
"""
        return system_prompt
    
    async def _call_openai_api(self, system_prompt: str, user_prompt: str) -> Dict:
        """Make an API call to OpenAI using the official client"""
        try:
            # Call OpenAI API using async client
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
            return json.loads(content)
            
        except Exception as e:
            print(f"Error in OpenAI API call: {e}")
            traceback.print_exc()
            raise
    
    def _simple_command_parser(self, text: str, drones: List) -> Dict:
        """A simple rule-based parser for demo purposes when no API key is available"""
        text = text.lower()
        
        # Try to identify the drone
        drone_id = None
        for i in range(1, len(drones) + 1):
            # Look for both numeric and word forms
            patterns = [
                f"drone {i}", f"drone{i}", f"drone #{i}", 
                f"drone number {i}", f"drone-{i}"
            ]
            
            # Add word forms for numbers 1-10
            number_words = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
            if i <= len(number_words):
                patterns.extend([
                    f"drone {number_words[i-1]}", 
                    f"drone number {number_words[i-1]}"
                ])
                
            if any(pattern in text for pattern in patterns):
                drone_id = i
                break
        
        if drone_id is None:
            return {"error": "Could not determine drone ID"}
        
        # Initialize result structure
        result = {
            "command_type": "move",
            "target": {
                "drone_id": drone_id
            },
            "parameters": {
                "movements": []
            }
        }
            
        # Look for direction words and numbers
        if "left" in text or "west" in text:
            steps = self._extract_steps(text, ["left", "west"])
            if steps > 0:
                result["parameters"]["movements"].append({"direction": "left", "steps": steps})
        
        if "right" in text or "east" in text:
            steps = self._extract_steps(text, ["right", "east"])
            if steps > 0:
                result["parameters"]["movements"].append({"direction": "right", "steps": steps})
        
        if "up" in text or "north" in text:
            steps = self._extract_steps(text, ["up", "north"])
            if steps > 0:
                result["parameters"]["movements"].append({"direction": "up", "steps": steps})
        
        if "down" in text or "south" in text:
            steps = self._extract_steps(text, ["down", "south"])
            if steps > 0:
                result["parameters"]["movements"].append({"direction": "down", "steps": steps})
        
        if not result["parameters"]["movements"]:
            return {"error": "Could not determine movement directions"}
            
        return result
    
    def _extract_steps(self, text: str, direction_words: List[str]) -> int:
        """Extract number of steps for a specific direction from text"""
        # Simple number extraction - would need more sophisticated parsing for a real system
        import re
        
        # Check for each direction word
        for direction in direction_words:
            # Try to find a number following the direction word
            pattern = f"{direction}\s+(\d+)"
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
            
            # Check for word numbers
            number_words = {
                "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
            }
            
            for word, value in number_words.items():
                if f"{direction} {word}" in text:
                    return value
        
        return 0
        
    def execute_json_command(self, command_json: Dict, environment, drones: List) -> bool:
        """Execute a JSON command"""
        try:
            command_type = command_json.get("command_type")
            
            if command_type == "move":
                return self._execute_move_command(command_json, environment, drones)
            else:
                print(f"Unknown command type: {command_type}")
                return False
                
        except Exception as e:
            print(f"Error executing JSON command: {e}")
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
                print(f"Drone with ID {drone_id} not found")
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
                    print(f"Invalid direction: {direction}")
                    continue
                
                # Add movement actions to the drone
                for _ in range(steps):
                    drone.add_action(MoveAction(direction))
            
            print(f"Command executed: Drone {drone_id} will perform {len(movements)} movement(s)")
            return True
            
        except Exception as e:
            print(f"Error executing move command: {e}")
            traceback.print_exc()
            return False
    
    def parse_json_instructions(self, json_str: str) -> Dict:
        """Parse JSON instructions from LLM response"""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            print("Error parsing JSON instructions")
            return {}

    def generate_command(self, target_position, drone_id=1):
        """Generate a JSON command to reach a target position.
        
        Args:
            target_position: Position object with x,y coordinates
            drone_id: ID of the drone to move (defaults to 1)
            
        Returns:
            dict: JSON command to move the drone
        """
        # Calculate distances to move vertically and horizontally
        vertical_dist = target_position.y - self.environment.drones[drone_id-1].position.y
        horizontal_dist = target_position.x - self.environment.drones[drone_id-1].position.x
        
        # Build JSON command
        command = {
            "command_type": "move",
            "target": {
                "drone_id": drone_id
            },
            "parameters": {
                "movements": []
            }
        }
        
        # Add vertical movement
        if vertical_dist != 0:
            direction = "up" if vertical_dist < 0 else "down"
            command["parameters"]["movements"].append({
                "direction": direction,
                "steps": abs(vertical_dist)
            })
            
        # Add horizontal movement
        if horizontal_dist != 0:
            direction = "left" if horizontal_dist < 0 else "right"
            command["parameters"]["movements"].append({
                "direction": direction,
                "steps": abs(horizontal_dist)
            })
            
        return command
