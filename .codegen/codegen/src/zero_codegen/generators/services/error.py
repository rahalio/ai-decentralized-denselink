"""
Error Generator - Generates application error classes

Per DDD: Application errors belong in services layer (application layer).
"""

from pathlib import Path
from typing import List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.file import ensure_directory, write_file


class ErrorGenerator(BaseGenerator):
    """
    Generates application error classes
    
    Pattern: export class NotFoundError extends Error {
      code = "NOT_FOUND";
      constructor(message: string) {
        super(message);
        this.name = "NotFoundError";
      }
    }
    """
    
    @property
    def name(self) -> str:
        return "Error Generator"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    @property
    def type(self) -> str:
        return "error"
    
    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate error file"""
        self.validate_context(context)
        
        files: List[Path] = []
        warnings: List[str] = []
        
        # Get output directory
        project_root = context.config.paths.project_root
        output_dir = project_root / "platform" / "services" / "src" / context.domain_name / "errors"
        ensure_directory(output_dir)
        
        # Generate errors file
        errors_file = output_dir / "index.ts"
        
        header = self.generate_header(
            context,
            "Application Errors - Application-level error classes"
        )
        
        errors_content = self._generate_errors_content(context, header)
        
        write_file(errors_file, errors_content)
        files.append(errors_file)
        
        context.logger.info(f"Generated error file for domain: {context.domain_name}")
        
        return GenerateResult(files=files, warnings=warnings)
    
    def _generate_errors_content(self, context: GenerationContext, header: str) -> str:
        """Generate errors file content"""
        # Standard application errors
        errors = [
            {
                "name": "NotFoundError",
                "code": "NOT_FOUND",
                "description": "Resource not found"
            },
            {
                "name": "PermissionDeniedError",
                "code": "PERMISSION_DENIED",
                "description": "Permission denied"
            },
            {
                "name": "ValidationError",
                "code": "VALIDATION_ERROR",
                "description": "Validation error"
            },
            {
                "name": "ConflictError",
                "code": "CONFLICT",
                "description": "Resource conflict"
            },
            {
                "name": "BadRequestError",
                "code": "BAD_REQUEST",
                "description": "Bad request"
            },
        ]
        
        error_classes = []
        for error in errors:
            error_classes.append(f"""export class {error["name"]} extends Error {{
  code = "{error["code"]}";
  constructor(message: string) {{
    super(message);
    this.name = "{error["name"]}";
  }}
}}""")
        
        errors_str = "\n\n".join(error_classes)
        
        return f"""{header}/**
 * Application Errors
 *
 * DDD: Application-level error classes.
 */

{errors_str}
"""
