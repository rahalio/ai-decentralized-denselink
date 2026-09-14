"""
Policy Generator - Generates application policies

Per DDD: Policies belong in services layer (application layer).
Policies contain business rules and validations.
"""

from pathlib import Path
from typing import Dict, Any, List

from ...base.generator import BaseGenerator, GenerateResult
from ...base.context import GenerationContext
from ...utils.openapi import extract_operations
from ...utils.naming import NamingConvention
from ...utils.file import ensure_directory, write_file
from ...utils.string import pascal_case, kebab_case, extract_verb_from_operation_id


class PolicyGenerator(BaseGenerator):
    """
    Generates policy objects
    
    Pattern: export const CanPublishPolicy = {
      allow(account: { status?: string }, _providerType: string): boolean {
        return account.status !== "disabled" && account.status !== "blocked";
      }
    };
    """
    
    @property
    def name(self) -> str:
        return "Policy Generator"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
    @property
    def type(self) -> str:
        return "policy"
    
    def generate(self, context: GenerationContext) -> GenerateResult:
        """Generate policy files"""
        self.validate_context(context)
        
        files: List[Path] = []
        warnings: List[str] = []
        
        # Get output directory
        project_root = context.config.paths.project_root
        output_dir = project_root / "platform" / "services" / "src" / context.domain_name / "policies"
        ensure_directory(output_dir)
        
        # Extract operations and identify policies
        operations = extract_operations(context.spec)
        if not operations:
            warnings.append("No operations found in OpenAPI spec")
            return GenerateResult(files=files, warnings=warnings)
        
        # Identify policies from operations
        policies = self._identify_policies(operations, context)
        
        # Generate policy file for each identified policy
        for policy_name, policy_operations in policies.items():
            # Use kebab-case for filename ending with .policy.ts (e.g., CanCreate -> can-create.policy.ts)
            policy_file_name = kebab_case(policy_name)
            policy_file = output_dir / f"{policy_file_name}.policy.ts"
            
            header = self.generate_header(
                context,
                f"{policy_name} Policy - Business rule"
            )
            
            policy_content = self._generate_policy_content(
                context,
                policy_name,
                policy_operations,
                header
            )
            
            write_file(policy_file, policy_content)
            files.append(policy_file)
        
        # Generate policies index
        index_file = output_dir / "index.ts"
        index_content = self._generate_index(context, list(policies.keys()))
        write_file(index_file, index_content)
        files.append(index_file)
        
        context.logger.info(f"Generated {len(files)} policy files for domain: {context.domain_name}")
        
        return GenerateResult(files=files, warnings=warnings)
    
    def _identify_policies(
        self,
        operations: List[Dict[str, Any]],
        context: GenerationContext
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Identify policies from operations"""
        policies: Dict[str, List[Dict[str, Any]]] = {}
        
        for op_data in operations:
            operation_id = op_data["operation_id"]
            verb = extract_verb_from_operation_id(operation_id)
            
            # Identify policies based on verbs
            if verb in ["publish", "create", "update", "delete"]:
                policy_name = f"Can{pascal_case(verb)}"
                
                if policy_name not in policies:
                    policies[policy_name] = []
                policies[policy_name].append(op_data)
        
        return policies
    
    def _generate_policy_content(
        self,
        context: GenerationContext,
        policy_name: str,
        operations: List[Dict[str, Any]],
        header: str
    ) -> str:
        """Generate policy object content"""
        # Extract verb from policy name (e.g., CanPublish -> publish)
        verb = policy_name.replace("Can", "").lower()
        
        # Generate policy object
        return f"""{header}/**
 * {policy_name} Policy
 *
 * DDD: Application policy for determining if {verb} operations are allowed.
 */

export const {policy_name} = {{
  allow(account: {{ status?: string }}, _providerType: string): boolean {{
    // Business rule: Allow if account is not disabled or blocked
    return account.status !== "disabled" && account.status !== "blocked";
  }}
}};
"""
    
    def _generate_index(self, context: GenerationContext, policy_names: List[str]) -> str:
        """Generate policies index file"""
        # Use kebab-case filenames with .policy.ts extension
        exports = "\n".join([f"export * from \"./{kebab_case(name)}.policy.js\";" for name in policy_names])
        if not exports.strip():
            exports = "export {};"
        
        return f"""/**
 * {pascal_case(context.domain_name)} Policies
 *
 * DDD: Application policies for {context.domain_name} domain.
 */

{exports}
"""
