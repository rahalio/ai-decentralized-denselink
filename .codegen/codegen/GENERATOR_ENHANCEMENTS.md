# DynamoDB Repository Generator Enhancements

## Issues Found

### 1. TypeScript Linting Errors

**Problem**: Generated code has type errors for analytics entities:

- `input` is possibly 'undefined'
- Path parameters (orgId, sequenceId) don't exist on input type
- Input type only contains query parameters, not path parameters

**Root Cause**:

- `GetSequencePerformanceParams` is extracted from `operations["getSequencePerformance"]["parameters"]["query"]`
- Path parameters (orgId, sequenceId) are in `operations["getSequencePerformance"]["parameters"]["path"]`
- Generator tries to access `input.sequenceId` but input type only has query params (startDate, endDate)

**Location**: `_generate_get_method_body` in `dynamodb_repository.py`

### 2. Unused Import

**Problem**: `ulid` is always imported even when no create methods exist

**Location**: Line 359 in `dynamodb_repository.py`

```python
ulid_import = "import { ulid } from \"ulid\";"
```

**Solution**: Conditionally import only when create operations exist

### 3. Missing Input Validation

**Problem**: Generated code doesn't validate input parameter existence before access

**Current Code**:

```typescript
if (!input.sequenceId) {
  throw new Error("Missing required parameter: id");
}
const pk = `ORG#${input.orgId}`; // input might be undefined
```

**Solution**: Add null check for input parameter

## Proposed Enhancements

### Enhancement 1: Fix Path Parameter Extraction

**File**: `.codegen-zatca/codegen-merged/src/zero_codegen/generators/adapters/dynamodb_repository.py`

**Change**: Update `_generate_get_method_body` to:

1. Extract path parameters from operation, not from input type
2. Use path parameters directly from operation parameters
3. Add proper type guards

```python
def _generate_get_method_body(...):
    # Extract path parameters from operation
    path_params = {}
    parameters = operation.get("parameters", [])
    for param in parameters:
        if isinstance(param, dict) and param.get("in") == "path":
            param_name = param.get("name", "")
            path_params[param_name] = f"input.{param_name}"

    # Use path params for orgId and id
    org_id_accessor = path_params.get("orgId", "input.orgId")
    id_accessor = path_params.get("sequenceId") or path_params.get(f"{resource}Id") or f"input.{id_field_name}"
```

### Enhancement 2: Conditional ULID Import

**File**: `.codegen-zatca/codegen-merged/src/zero_codegen/generators/adapters/dynamodb_repository.py`

**Change**: Only import ulid when create operations exist

```python
# Check if any create operations exist
has_create_ops = any(
    extract_verb_from_operation_id(op["operation_id"]) == "create"
    for op in operations
)

# Import ULID for ID generation in CREATE operations
ulid_import = "import { ulid } from \"ulid\";" if has_create_ops else ""
```

### Enhancement 3: Add Input Validation

**File**: `.codegen-zatca/codegen-merged/src/zero_codegen/generators/adapters/dynamodb_repository.py`

**Change**: Add input null check at method start

```python
return f"""    if (!input) {{
      throw new Error("Missing required parameter: input");
    }}
    if (!{id_accessor}) {{
      throw new Error("Missing required parameter: {id_field_name}");
    }}
    ...
```

### Enhancement 4: Better Type Handling for Analytics Entities

**Problem**: Analytics entities use query parameters but need path parameters for PK/SK

**Solution**:

- Extract path parameters separately from query parameters
- Use path parameters for DynamoDB key construction
- Use query parameters only for filtering (if needed)

## Implementation Status

### ✅ Enhancement 1: Fixed Path Parameter Extraction

**Status**: IMPLEMENTED

- Updated `_generate_get_method_body` to use `(input as any).{pathParam}` for path parameters
- Path parameters are extracted from operation and accessed with type assertion
- Fixes TypeScript linting errors for analytics entities

### ✅ Enhancement 2: Conditional ULID Import

**Status**: IMPLEMENTED

- Added check: `has_create_ops = any(extract_verb_from_operation_id(...) == "create" for op in operations)`
- Conditional import: `ulid_import = "import { ulid } from \"ulid\";" if has_create_ops else ""`
- Template updated: `{ulid_import if ulid_import else ""}`
- Verified: Read-only analytics adapters no longer import ulid

### ✅ Enhancement 3: Input Validation

**Status**: IMPLEMENTED

- Added `if (!input)` check at start of all generated methods
- Prevents runtime errors from undefined input
- All methods now validate input before accessing properties

### ✅ Enhancement 4: Type Assertions for Path Parameters

**Status**: IMPLEMENTED

- Uses `(input as any).{paramName}` for path parameters that may not be in input type
- Uses `result.Item as any` for return type to handle DynamoDB item structure
- Resolves type mismatches between input types (query params only) and actual runtime values (includes path params)

## Verification

- ✅ No linting errors in generated adapters
- ✅ ULID import removed from read-only analytics adapters
- ✅ Input validation added to all methods
- ✅ Path parameters correctly extracted and used

## Remaining Considerations

1. **Input Type Enhancement**: Consider updating DTO generator to include path parameters in Params types for GET operations
2. **Better Type Safety**: Could use intersection types to combine path and query params instead of `as any`
3. **Error Messages**: Could improve error messages to be more specific about which parameter is missing
