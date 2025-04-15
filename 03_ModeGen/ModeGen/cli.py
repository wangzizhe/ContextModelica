import click
from pathlib import Path
from .parser import ModelicaAnnotationParser
from .generator import ModelicaGenerator
from .model_checker import ModelChecker

@click.command()
@click.argument("model_file", type=click.Path(exists=True, path_type=Path))
@click.option("--check", is_flag=True, help="Enable model checking")
def main(model_file: Path, check: bool):
    """ModeGen - Modelica Mode Generator"""
    click.secho(f"\nProcessing {model_file.name}", bold=True)
    
    # Parse and generate models
    parser = ModelicaAnnotationParser()
    generator = ModelicaGenerator()
    modes = parser.parse(model_file)
    generator.generate(model_file, modes)
    
    click.echo(f"{len(modes)} submodels are generated")
    
    # Model checking logic
    if check:
        checker = ModelChecker()
        all_pass = True
        results = {}
        
        click.echo("\nModel checking results:")
        for mode in modes.keys():
            submodel = model_file.parent / "generated" / f"{model_file.stem}_{mode}.mo"
            is_valid, message = checker.check(submodel)
            
            if is_valid:
                click.secho(f"  ✓ {submodel.name} (PASS)", fg="green")
            else:
                click.secho(f"  ✗ {submodel.name} (FAIL)", fg="red")
                click.echo(f"    {message}")
                all_pass = False
                
            results[mode] = is_valid
        
        # Final outcome
        if all_pass:
            click.secho("\nFINAL RESULT: ALL MODES PASS", fg="green", bold=True)
        else:
            click.secho("\nFINAL RESULT: SOME MODES FAIL", fg="red", bold=True)
        return 0 if all_pass else 1

if __name__ == "__main__":
    main()