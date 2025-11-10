"""Template rendering for VibeWP CLI"""

from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound


class TemplateRenderer:
    """Renders Jinja2 templates for Docker Compose and configuration files"""

    def __init__(self, template_dir: Optional[str] = None):
        """
        Initialize template renderer

        Args:
            template_dir: Directory containing templates (defaults to ../templates)
        """
        if template_dir is None:
            # Default to templates directory in project root
            template_dir = Path(__file__).parent.parent.parent / "templates"

        self.template_dir = Path(template_dir)

        if not self.template_dir.exists():
            raise FileNotFoundError(
                f"Template directory not found: {self.template_dir}"
            )

        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )

    def render(self, template_name: str, **kwargs) -> str:
        """
        Render template with variables

        Args:
            template_name: Name of template file (relative to template_dir)
            **kwargs: Template variables

        Returns:
            Rendered template as string
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except TemplateNotFound:
            raise FileNotFoundError(
                f"Template not found: {template_name} in {self.template_dir}"
            )
        except Exception as e:
            raise RuntimeError(f"Template rendering failed: {e}")

    def render_to_file(
        self,
        template_name: str,
        output_path: str,
        **kwargs
    ) -> None:
        """
        Render template and write to file

        Args:
            template_name: Name of template file
            output_path: Destination file path
            **kwargs: Template variables
        """
        content = self.render(template_name, **kwargs)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            f.write(content)

    def render_string(self, template_string: str, **kwargs) -> str:
        """
        Render template from string

        Args:
            template_string: Template content as string
            **kwargs: Template variables

        Returns:
            Rendered content
        """
        try:
            template = Template(template_string)
            return template.render(**kwargs)
        except Exception as e:
            raise RuntimeError(f"String template rendering failed: {e}")

    def list_templates(self, pattern: str = "*.yml") -> list[str]:
        """
        List available templates

        Args:
            pattern: Glob pattern for filtering

        Returns:
            List of template file names
        """
        return [
            str(f.relative_to(self.template_dir))
            for f in self.template_dir.rglob(pattern)
        ]

    def template_exists(self, template_name: str) -> bool:
        """
        Check if template exists

        Args:
            template_name: Name of template file

        Returns:
            True if template exists, False otherwise
        """
        template_path = self.template_dir / template_name
        return template_path.exists()
