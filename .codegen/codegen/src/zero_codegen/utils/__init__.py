"""Utility functions"""

from zero_codegen.utils.string import (
    camel_case,
    pascal_case,
    kebab_case,
    snake_case,
    pluralize,
    singularize,
    extract_resource_from_operation_id,
)
from zero_codegen.utils.openapi import (
    load_openapi_spec,
    extract_operations,
    extract_schemas,
    get_operation_by_id,
    resolve_ref,
    get_input_schema_or_type_name,
)
from zero_codegen.utils.file import (
    ensure_directory,
    write_file,
    read_file,
    file_exists,
    clean_directory,
)
from zero_codegen.utils.generator_setup import GeneratorSetup
from zero_codegen.utils.index_file_generator import IndexFileGenerator
from zero_codegen.utils.openapi_bundler import OpenApiBundler

__all__ = [
    "camel_case",
    "pascal_case",
    "kebab_case",
    "snake_case",
    "pluralize",
    "singularize",
    "extract_resource_from_operation_id",
    "load_openapi_spec",
    "extract_operations",
    "extract_schemas",
    "get_operation_by_id",
    "resolve_ref",
    "get_input_schema_or_type_name",
    "ensure_directory",
    "write_file",
    "read_file",
    "file_exists",
    "clean_directory",
    "GeneratorSetup",
    "IndexFileGenerator",
    "OpenApiBundler",
]
