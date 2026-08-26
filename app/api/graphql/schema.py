import strawberry
from strawberry.extensions import MaxAliasesLimiter, QueryDepthLimiter

from app.api.graphql.complexity import QueryComplexityLimiter
from app.api.graphql.mutations import Mutation
from app.api.graphql.queries import Query
from app.core.config import get_settings

settings = get_settings()

# Three independent, cheap-to-evaluate guards run before any resolver
# touches the database: depth (a pathological `{ a { b { a { b ... } } } }`
# cycle), alias count (the classic "alias-bombing" DoS, where one query
# repeats an expensive field hundreds of times under different aliases to
# multiply its cost past what depth/complexity alone would catch), and
# the cost estimate in `complexity.py` that accounts for pagination
# arguments depth-limiting can't see.
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        QueryDepthLimiter(max_depth=settings.graphql_max_query_depth),
        MaxAliasesLimiter(max_alias_count=15),
        QueryComplexityLimiter(max_complexity=settings.graphql_max_query_complexity),
    ],
)
