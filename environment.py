import pygame
import numpy as np
from typing import List, Dict, Any, Tuple

class Position:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
    
    def __eq__(self, other):
        if not isinstance(other, Position):
            return False
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))
    
    def __add__(self, other):
        return Position(self.x + other.x, self.y + other.y)

class Entity:
    def __init__(self, position: Position, entity_type: str):
        self.position = position
        self.entity_type = entity_type
        self.id = id(self)
    
    def update(self, environment):
        pass
    
    def render(self, surface, cell_size):
        pass

class GridEnvironment:
    def __init__(self, width: int, height: int, cell_size: int = 20):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        self.entities: List[Entity] = []
        self.grid = np.zeros((height, width), dtype=object)
        self.screen_width = width * cell_size
        # Add extra height for the text input area
        self.text_input_height = 40
        self.screen_height = height * cell_size + self.text_input_height
        self.screen = None
        self.clock = None
        self.running = False
        self.event_manager = None  # Will be set later
        
        # Text input related variables
        self.input_text = ""
        self.input_active = False
        self.command_processor = None  # Will be set from main.py
        
    def initialize(self):
        """Initialize Pygame and environment"""
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Drone Swarm Simulation")
        self.clock = pygame.time.Clock()
        self.running = True
    
    def add_entity(self, entity: Entity):
        """Add an entity to the environment"""
        self.entities.append(entity)
    
    def remove_entity(self, entity: Entity):
        """Remove an entity from the environment"""
        if entity in self.entities:
            self.entities.remove(entity)
    
    def get_entities_at(self, position: Position) -> List[Entity]:
        """Get all entities at a specific position"""
        return [e for e in self.entities if e.position == position]
    
    def is_valid_position(self, position: Position) -> bool:
        """Check if a position is within the grid boundaries"""
        return (0 <= position.x < self.width and 
                0 <= position.y < self.height)
    
    def update(self):
        """Update all entities in the environment"""
        for entity in self.entities:
            entity.update(self)
    
    def process_input_events(self, event):
        """Process keyboard events for text input"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check if click was in text input area
            input_rect = pygame.Rect(0, self.height * self.cell_size, 
                                    self.screen_width, self.text_input_height)
            self.input_active = input_rect.collidepoint(event.pos)
            
        if event.type == pygame.KEYDOWN:
            if self.input_active:
                if event.key == pygame.K_RETURN:
                    # Process command when Enter is pressed
                    if self.command_processor and self.input_text:
                        self.command_processor.process_command(self.input_text, self)
                    self.input_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    # Add character to input text
                    self.input_text += event.unicode
    
    def render(self):
        """Render the environment and all entities"""
        self.screen.fill((255, 255, 255))
        
        # Draw grid lines
        for x in range(0, self.screen_width, self.cell_size):
            pygame.draw.line(self.screen, (200, 200, 200), 
                            (x, 0), (x, self.height * self.cell_size))
        for y in range(0, self.height * self.cell_size, self.cell_size):
            pygame.draw.line(self.screen, (200, 200, 200), 
                            (0, y), (self.screen_width, y))
        
        # Render entities
        for entity in self.entities:
            entity.render(self.screen, self.cell_size)
        
        # Draw text input area
        input_rect = pygame.Rect(10, self.height * self.cell_size + 10, 
                                self.screen_width - 20, self.text_input_height - 20)
        pygame.draw.rect(self.screen, (200, 200, 200), input_rect, 2)
        
        # Render input text
        font = pygame.font.SysFont(None, 32)
        text_surface = font.render(self.input_text, True, (0, 0, 0))
        self.screen.blit(text_surface, (input_rect.x + 5, input_rect.y + 5))
        
        # Draw prompt text if no input
        if not self.input_text:
            prompt_text = font.render("Type command here...", True, (150, 150, 150))
            self.screen.blit(prompt_text, (input_rect.x + 5, input_rect.y + 5))
        
        pygame.display.flip()
    
    def run(self, fps: int = 60):
        """Main simulation loop"""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                self.process_input_events(event)
            
            self.update()
            self.render()
            self.clock.tick(fps)
        
        pygame.quit() 