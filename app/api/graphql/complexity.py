"""Query cost estimation, independent of `QueryDepthLimiter`.

Depth alone doesn't catch an expensive query: `patients(first: 500) {
encounters(first: 500) { ... } }` has depth 2 but can touch up to
250,000 rows. This extension walks the operation's AST before execution
and multiplies each field's cost by any `first`/`limit` argument on it,
so a shallow-but-wide query is penalized the same way a deep one is.

Implemented as a `SchemaExtension.on_execute` hook rather than a
`graphql-core` `ValidationRule` (the mechanism `QueryDepthLimiter` uses)
because validation rules run against the AST and type info only —
variable *values* (`first: $first`) aren't bound yet at that point.
`on_execute` runs after variables are coerced, so `first: $pageSize`
counts correctly whether the caller passed a literal or a variable.

This is a deliberate simplification relative to a full field-weighted
analyzer (e.g. a `@complexity` directive with a hand-tuned cost per
field): every field costs 1 point regardless of what it computes. For
this schema, cost is concentrated in row fan-out, not per-field
computation, so that's the dimension worth guarding without having to
maintain per-field weights alongside the schema.
"""

from collections.abc import Iterator
from typing import Any

from graphql import ExecutionResult as GraphQLExecutionResult
from graphql import GraphQLError
from graphql.language import (
    DocumentNode,
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    InlineFragmentNode,
    IntValueNode,
    SelectionSetNode,
    VariableNode,
)
from strawberry.extensions import SchemaExtension
from strawberry.extensions.utils import is_introspection_key

_LIST_ARGUMENT_NAMES = ("first", "limit")


class QueryComplexityLimiter(SchemaExtension):
    def __init__(self, max_complexity: int) -> None:
        self.max_complexity = max_complexity

    def on_execute(self) -> Iterator[None]:
        document = self.execution_context.graphql_document
        if document is not None:
            variables = self.execution_context.variables or {}
            cost = _estimate_document_cost(document, variables)
            if cost > self.max_complexity:
                self.execution_context.result = GraphQLExecutionResult(
                    data=None,
                    errors=[
                        GraphQLError(
                            f"Query is too complex: estimated cost {cost} exceeds "
                            f"the limit of {self.max_complexity}. Reduce nesting or "
                            f"request smaller pages (lower `first`/`limit`)."
                        )
                    ],
                )
        yield


def _estimate_document_cost(document: DocumentNode, variables: dict[str, Any]) -> int:
    fragments = {
        definition.name.value: definition
        for definition in document.definitions
        if isinstance(definition, FragmentDefinitionNode)
    }
    total = 0
    for definition in document.definitions:
        selection_set = getattr(definition, "selection_set", None)
        if selection_set is not None:
            total += _cost_of_selection_set(selection_set, variables, fragments)
    return total


def _cost_of_selection_set(
    selection_set: SelectionSetNode,
    variables: dict[str, Any],
    fragments: dict[str, FragmentDefinitionNode],
) -> int:
    total = 0
    for selection in selection_set.selections:
        if isinstance(selection, FieldNode):
            if is_introspection_key(selection.name.value):
                continue
            total += _cost_of_field(selection, variables, fragments)
        elif isinstance(selection, InlineFragmentNode):
            total += _cost_of_selection_set(selection.selection_set, variables, fragments)
        elif isinstance(selection, FragmentSpreadNode):
            fragment = fragments.get(selection.name.value)
            if fragment is not None:
                total += _cost_of_selection_set(fragment.selection_set, variables, fragments)
    return total


def _cost_of_field(
    field: FieldNode, variables: dict[str, Any], fragments: dict[str, FragmentDefinitionNode]
) -> int:
    children_cost = 0
    if field.selection_set is not None:
        children_cost = _cost_of_selection_set(field.selection_set, variables, fragments)
    return 1 + _list_multiplier(field, variables) * children_cost


def _list_multiplier(field: FieldNode, variables: dict[str, Any]) -> int:
    for argument in field.arguments:
        if argument.name.value not in _LIST_ARGUMENT_NAMES:
            continue
        value_node = argument.value
        if isinstance(value_node, IntValueNode):
            return int(value_node.value)
        if isinstance(value_node, VariableNode):
            resolved = variables.get(value_node.name.value)
            if isinstance(resolved, int):
                return resolved
    return 1
