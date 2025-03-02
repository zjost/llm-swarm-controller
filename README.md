# Drone Swarm LLM Controller

A simulation environment that allows an LLM (Large Language Model) to translate goals expressed in natural language into instructions for a swarm of drones. Built with Python and Pygame, this project enables experimentation with autonomous drone coordination through natural language interfaces.

## Overview

This project simulates a swarm of drones that can be controlled either through direct commands or via an LLM that translates high-level goals into specific drone behaviors. Drones operate in a 2D grid world where they can move, scan for targets, and execute complex behaviors like exploration and patrolling.

## Features

- **Grid-based simulation environment** with customizable dimensions
- **Multiple drone entities** that can be controlled individually or as a swarm
- **Target detection** using drone sensors with configurable detection ranges
- **Primitive actions** (move, wait, scan) that drones can perform
- **Complex behaviors** built from primitive actions (explore, patrol, move to position)
- **Event system** for reacting to environment changes
- **LLM integration** for translating natural language goals into drone instructions
- **Command line interface** for direct drone control
- **Interactive UI** with command input

## Architecture

The simulation is built with the following components:

- **Environment**: A 2D grid where entities exist and interact
- **Drones**: Entities that can perform actions and follow behaviors
- **Actions**: Primitive operations like movement and scanning
- **Behaviors**: Complex sequences of actions (patrol routes, exploration)
- **Event System**: Handles events like target detection and movement
- **Command Processor**: Parses text commands into drone actions
- **LLM Controller**: Integrates with an LLM to process natural language goals

## Installation

1. Clone the repository: 
```
git clone https://github.com/yourusername/drone-swarm-llm-controller.git
cd drone-swarm-llm-controller
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

3. (Optional) Set up LLM API access:
- For OpenAI integration, set your API key as an environment variable:
```
export OPENAI_API_KEY="your_openai_api_key"
```


## Usage

Run the simulation with default settings:
```
python main.py
```

### Command-line Arguments

- `--mock`: Use mock LLM behavior for testing
- `--num-drones`: Number of drones in the simulation (default: 3)
- `--num-targets`: Number of targets to place (default: 3)
- `--width`: Grid width (default: 20)
- `--height`: Grid height (default: 15)
- `--detection-range`: Range for drone sensors (default: 2)

Example:
```
python main.py --num-drones 5 --num-targets 5 --width 30 --height 20 --detection-range 3
```

### In-Simulation Commands

Once the simulation is running, you can type commands in the input box at the bottom of the screen. Commands follow this format:

```
move drone<id> <direction>=<steps>
```


Examples:
- `move drone1 up=3`
- `move drone2 right=4 and down=2`

## Extending the Simulation

### Adding New Behaviors

Create new behaviors by extending the `Behavior` class in `behavior.py`:

```python
class YourNewBehavior(Behavior):
    def init(self, param1, param2):
        super().init()
        self.param1 = param1
        self.param2 = param2
    
    def update(self, drone, environment) -> bool:
        # Your behavior logic here
        return False # Return True when completed
```

Register your behavior in the `BehaviorFactory` class.

### Adding Event Handlers

You can define custom event handlers in the simulation:
```python
def custom_handler(event):
    drone = event.data['drone']
    # Your handler logic here

callback = EventCallback(custom_handler)
environment.event_manager.register("your_event_type", callback)
```

### LLM Integration

To use a real LLM instead of the mock implementation:
1. Update the `process_goal` method in `llm_controller.py`
2. Implement your LLM API call (OpenAI, Anthropic, etc.)
3. Parse the response and generate commands for the drones

## Examples

### Patrolling Behavior
```
python main.py --mock --num-drones 3
```

In the command input:
```
move drone1 right=5 and down=5 and left=5 and up=5
```

### Target Finding
```
python main.py --mock --num-drones 5 --num-targets 10 --detection-range 3
```

Drones will automatically detect targets within their configured range.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.