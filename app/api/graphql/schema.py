import strawberry

from app.api.graphql.mutations import Mutation
from app.api.graphql.queries import Query

schema = strawberry.Schema(query=Query, mutation=Mutation)
