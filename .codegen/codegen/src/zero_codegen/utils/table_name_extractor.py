"""
Table Name Extractor - Extracts DynamoDB table configuration from OpenAPI

Per DDD: Table names should be derived from OpenAPI x-dynamodb extensions, not hardcoded.
"""

from typing import Dict, Any, Optional, Tuple


class TableNameExtractor:
    """Extracts table name configuration from OpenAPI x-dynamodb extensions"""

    # Analytics domains (use ANALYTICS table)
    ANALYTICS_DOMAINS = ["metrics", "observability", "analytics"]

    # Base table entity patterns (use BASE table)
    BASE_TABLE_PATTERNS = ["CONFIG", "CATALOG", "TEMPLATE", "POLICY", "ROUTE", "MODEL"]

    @staticmethod
    def extract_table_config(
        x_dynamodb: Optional[Dict[str, Any]],
        domain_name: str,
        entity_type: str
    ) -> Tuple[str, Optional[str]]:
        """
        Extract table type and optional table name from OpenAPI x-dynamodb extension

        Returns:
            Tuple of (table_type, table_name)
            - table_type: "core", "base", or "analytics"
            - table_name: Optional explicit table name, or None to derive from type
        """
        # Priority 1: Explicit tableType in x-dynamodb extension
        if x_dynamodb and "tableType" in x_dynamodb:
            table_type = x_dynamodb["tableType"]
            table_name = x_dynamodb.get("tableName")
            return (table_type, table_name)

        # Priority 2: Explicit tableName in x-dynamodb extension
        if x_dynamodb and "tableName" in x_dynamodb:
            table_name = x_dynamodb["tableName"]
            # Infer tableType from tableName pattern
            if "-core-" in table_name:
                return ("core", table_name)
            elif "-base-" in table_name:
                return ("base", table_name)
            elif "-analytics-" in table_name:
                return ("analytics", table_name)
            # Default to core if pattern doesn't match
            return ("core", table_name)

        # Priority 3: Infer from domain name
        if domain_name.lower() in TableNameExtractor.ANALYTICS_DOMAINS:
            return ("analytics", None)

        # Priority 4: Infer from entity type patterns
        if any(pattern in entity_type for pattern in TableNameExtractor.BASE_TABLE_PATTERNS):
            return ("base", None)

        # Priority 5: Default to CORE table (most entities)
        return ("core", None)

    @staticmethod
    def get_table_name_function(table_type: str) -> str:
        """
        Get the table name function name based on table type

        Args:
            table_type: "core", "base", or "analytics"

        Returns:
            Function name string (e.g., "getCoreTableName")
        """
        function_map = {
            "core": "getCoreTableName",
            "base": "getBaseTableName",
            "analytics": "getAnalyticsTableName"
        }
        return function_map.get(table_type, "getCoreTableName")

    @staticmethod
    def generate_table_name_code(
        table_type: str,
        table_name: Optional[str],
        domain_name: str,
        entity_type: str
    ) -> Tuple[str, str]:
        """
        Generate TypeScript code to get table name from OpenAPI config.

        Returns (property_declaration, constructor_body):
        - property_declaration: Class property for TABLE_NAME
        - constructor_body: Code to add inside constructor (empty for explicit table name)
        """
        if table_name:
            # Explicit table name from x-dynamodb.tableName - use it directly
            return (f'private readonly TABLE_NAME = "{table_name}";', "")

        # Dynamic function selection based on tableType - assign in constructor
        constructor_body = f"""    const tableTypeFromMetadata = "{table_type}";
    const tableTypeMap = {{
      core: getCoreTableName,
      base: getBaseTableName,
      analytics: getAnalyticsTableName,
    }};
    const tableNameFn = tableTypeMap[tableTypeFromMetadata] || getCoreTableName;
    this.TABLE_NAME = tableNameFn();"""
        return ("private readonly TABLE_NAME: string;", constructor_body)
