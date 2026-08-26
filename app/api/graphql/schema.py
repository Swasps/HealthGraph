import strawberry

from app.api.graphql.queries import Query

schema = strawberry.Schema(query=Query)
