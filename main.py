import asyncio
import argparse
import random
from environment import GridEnvironment, Position, Entity
from drone import Detector, Drone, MoveAction, WaitAction, ScanAction
from behavior import MoveToBehavior, ExploreBehavior, PatrolBehavior
from llm_controller import LLMController
from event_system import EventManager, EventCallback
from command_processor import CommandProcessor
from typing import List, Dict
import re
import pygame
import traceback

class Target(Entity):
    """A simple target entity for drones to find"""
    def __init__(self, position: Position):
        super().__init__(position, "target")
    
    def render(self, surface, cell_size):
        x = self.position.x * cell_size
        y = self.position.y * cell_size
        pygame.draw.rect(surface, (255, 0, 0), (x + 4, y + 4, cell_size - 8, cell_size - 8))

async def run_simulation():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Run drone swarm simulation')
    parser.add_argument('--mock', action='store_true', help='Use mock LLM for testing')
    parser.add_argument('--num-drones', type=int, default=3, help='Number of drones')
    parser.add_argument('--num-targets', type=int, default=3, help='Number of targets')
    parser.add_argument('--width', type=int, default=20, help='Grid width')
    parser.add_argument('--height', type=int, default=15, help='Grid height')
    parser.add_argument('--detection-range', type=int, default=2, help='Detection range for drone sensors')
    args = parser.parse_args()
    
    # Create environment
    environment = GridEnvironment(args.width, args.height)
    event_manager = EventManager()
    environment.event_manager = event_manager
    
    # Create command processor
    command_processor = CommandProcessor()
    environment.command_processor = command_processor
    
    # Create drones and equip them with detectors
    drones = []
    for i in range(args.num_drones):
        # Random position for the drone
        position = Position(
            random.randint(0, args.width - 1),
            random.randint(0, args.height - 1)
        )
        drone = Drone(position, i + 1)
        
        # Create and attach a detector
        detector = Detector(range=args.detection_range)
        drone.set_detector(detector)
        
        drones.append(drone)
        environment.add_entity(drone)
    
    # Update command processor with drones
    command_processor.set_drones(drones)
    
    # Create targets
    for i in range(args.num_targets):
        # Random position for the target
        position = Position(
            random.randint(0, args.width - 1),
            random.randint(0, args.height - 1)
        )
        target = Target(position)
        environment.add_entity(target)
    
    # Set up target detection event handler
    @event_manager.register("target_detected")
    def handle_target_detected(event):
        drone = event.data['drone']
        targets = event.data['targets']
        
        print(f"Drone {drone.drone_id} found {len(targets)} target(s) at ({drone.position.x}, {drone.position.y})!")
        
        # Pause briefly to visually indicate finding a target
        drone.clear_behavior()
        drone.add_action(WaitAction(5))  # Wait 5 ticks
        
        # Then resume exploring from a different position
        import random
        directions = ["up", "down", "left", "right"]
        for _ in range(3):  # Move away from current position
            drone.add_action(MoveAction(random.choice(directions)))
            
        # Then resume exploring
        explore_behavior = ExploreBehavior(steps=-1)
        drone.set_behavior(explore_behavior)
    
    # Initialize LLM controller
    llm_controller = LLMController()
    
    # Initialize the environment
    environment.initialize()
    
    # Set initial input text to default goal
    environment.input_text = "Search for and find all targets in the environment"
    
    # Set drones to idle initially
    for drone in drones:
        drone.clear_behavior()
    
    # MAIN SIMULATION LOOP
    font = pygame.font.SysFont(None, 24)
    clock = pygame.time.Clock()
    
    while environment.running:
        # Process Pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                environment.running = False
            
            # Handle text input events
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check if click was in the text input area
                input_area = pygame.Rect(0, environment.height * environment.cell_size, 
                                        environment.screen_width, environment.text_input_height)
                if input_area.collidepoint(event.pos):
                    environment.input_active = True
                else:
                    environment.input_active = False
            
            elif event.type == pygame.KEYDOWN:
                if environment.input_active:
                    if event.key == pygame.K_RETURN:
                        # Process the goal when Enter is pressed
                        goal = environment.input_text
                        print(f"New goal received: {goal}")
                        try:
                            # Process the new goal asynchronously
                            response = await llm_controller.process_goal(goal, environment, drones, use_mock=args.mock)
                            if response.get("status") == "error":
                                print(f"Error from LLM controller: {response.get('message')}")
                        except Exception as e:
                            print(f"Error processing goal: {e}")
                            traceback.print_exc()
                        environment.input_text = ""  # Clear the input
                    elif event.key == pygame.K_BACKSPACE:
                        environment.input_text = environment.input_text[:-1]
                    else:
                        environment.input_text += event.unicode
        
        # Update all entities
        environment.update()
        
        # Render everything
        environment.screen.fill((0, 0, 0))  # Black background
        
        # Draw grid lines
        for x in range(0, environment.width * environment.cell_size, environment.cell_size):
            pygame.draw.line(environment.screen, (50, 50, 50), (x, 0), 
                             (x, environment.height * environment.cell_size))
        for y in range(0, environment.height * environment.cell_size, environment.cell_size):
            pygame.draw.line(environment.screen, (50, 50, 50), (0, y), 
                             (environment.width * environment.cell_size, y))
        
        # Draw all entities
        for entity in environment.entities:
            entity.render(environment.screen, environment.cell_size)
        
        # Draw text input area
        input_area = pygame.Rect(0, environment.height * environment.cell_size, 
                                 environment.screen_width, environment.text_input_height)
        pygame.draw.rect(environment.screen, (50, 50, 70), input_area)
        
        # Add some visual feedback on active input box
        if environment.input_active:
            pygame.draw.rect(environment.screen, (100, 100, 200), input_area, 2)
        else:
            pygame.draw.rect(environment.screen, (70, 70, 100), input_area, 2)
            
        # Render the input text
        prompt_text = font.render("Command: ", True, (200, 200, 200))
        environment.screen.blit(prompt_text, (10, environment.height * environment.cell_size + 10))
        
        input_text = font.render(environment.input_text, True, (255, 255, 255))
        environment.screen.blit(input_text, (100, environment.height * environment.cell_size + 10))
        
        # Update the display
        pygame.display.flip()
        
        # Cap the frame rate
        clock.tick(10)  # 10 FPS
    
    # Clean up
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(run_simulation()) 