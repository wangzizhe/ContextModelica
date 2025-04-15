from typing import Tuple
import subprocess
from pathlib import Path

class ModelChecker:
    """Validates Modelica files using OpenModelica compiler"""
    
    def __init__(self, omc_path: str = "omc"):
        self.omc_path = omc_path
    
    def check(self, model_path: Path) -> Tuple[bool, str]:
        """Checks model syntax using OMC and returns a boolean result with message"""
        try:
            # Debugging: print the omc path to confirm it's found
            print(f"Calling OpenModelica compiler for model checking")

            # Debugging: print the full command being executed
            command = [self.omc_path, str(model_path)]
            print(f"Running command: {' '.join(command)}")

            # Execute the OpenModelica command
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            # Check for success or failure based on return code
            if result.returncode == 0:
                return True, f"{model_path.name} passed validation."
            else:
                return False, f"Error in {model_path.name}: {result.stderr}"
        
        except subprocess.TimeoutExpired:
            return False, f"Timeout expired while validating {model_path.name}."
        except Exception as e:
            return False, f"Validation error for {model_path.name}: {e}"