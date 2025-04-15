import re
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class ModeDefinition:
    """Stores metadata for each operational mode"""
    declarations: List[str]  # All components (variables, parameters, constants, imports, etc.)
    equations: List[str]  # Regular equations
    initial_equations: List[str]  # Initial equations
    algorithms: List[str]  # Algorithm blocks
    initial_algorithms: List[str]  # Initial algorithm blocks

    def __init__(self):
        self.declarations = []
        self.equations = []
        self.initial_equations = []
        self.algorithms = []
        self.initial_algorithms = []

class ModelicaAnnotationParser:
    """Parses ModeGen annotations from Modelica files"""
    
    # Patterns to detect the annotations and other Modelica elements
    MODE_TAG = re.compile(r'/*#\s*\[([a-zA-Z0-9_]+)\]')  # Mode annotation (e.g., /*# [pendulum] */)
    EQUATION_BLOCK_START = re.compile(r'@#\s*equation')
    ALGORITHM_BLOCK_START = re.compile(r'@#\s*algorithm')
    END_MODEL = re.compile(r'@#\s*end\s*(\w+)')
    MODEL_START = re.compile(r'^\s*model\s+(\w+)')  # Match the start of a model

    def parse(self, file_path: str) -> Dict[str, ModeDefinition]:
        """Extracts mode definitions from annotated Modelica file"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Detect modes
        modes = self._detect_modes(content)
        
        # Parse content and populate mode definitions
        self._parse_content(content, modes)
        
        return modes
    
    def _detect_modes(self, content: str) -> Dict[str, ModeDefinition]:
        """Extracts mode names ONLY from metadata"""
        metadata_match = re.search(r'Modes:\s*\[([^\]]+)\]', content, re.IGNORECASE)
        if not metadata_match:
            raise ValueError("ERROR: No 'Modes' section found in MODEL-METADATA!")
        
        # Extract modes from metadata
        mode_list = [mode.strip() for mode in metadata_match.group(1).split(',')]
        
        # Initialize mode definitions
        modes = {mode: ModeDefinition() for mode in mode_list}
        
        return modes
    
    def _parse_content(self, content: str, modes: Dict[str, ModeDefinition]):
        """Populates mode definitions with variables, parameters, and equations"""
        current_modes = set()  # Set of active modes for the current section
        in_model_block = False
        in_equation_block = False
        in_algorithm_block = False

        # Iterate through lines in content
        for line in content.splitlines():
            line = line.strip()

            # Detect mode annotation (e.g., /*# [pendulum] */)
            mode_match = self.MODE_TAG.search(line)
            if mode_match:
                mode_name = mode_match.group(1)
                current_modes = {mode_name} if mode_name != "All" else set(modes.keys())
                continue

            # Handle model start (find the start of the model block)
            if re.match(r'^\s*model', line):
                in_model_block = True
                continue

            # Handle equation block
            if in_model_block and self.EQUATION_BLOCK_START.search(line):
                in_model_block = False
                in_equation_block = True  # We are now in the equation block
                continue

            # Collect everything between model and equation
            if in_model_block:
                # Here we collect everything (declarations, library components, variables)
                # Add it to the appropriate modes
                for mode in current_modes:
                    modes[mode].declarations.append(line)

            # Handle equation block
            if in_equation_block:
                if line.lower().startswith("equation"):
                    continue  # Skip the "equation" header line
                if line:  # Non-empty lines
                    for mode in current_modes:
                        modes[mode].equations.append(line)

            # Handle algorithm blocks (if any)
            if in_algorithm_block:
                if line.lower().startswith("algorithm"):
                    continue  # Skip the "algorithm" header line
                if line:  # Non-empty lines
                    for mode in current_modes:
                        modes[mode].algorithms.append(line)

            # End of the model block or other sections
            if self.END_MODEL.search(line):
                in_equation_block = in_algorithm_block = False  # Exit equation or algorithm block
                continue