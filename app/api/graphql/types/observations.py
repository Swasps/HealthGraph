from datetime import datetime

import strawberry

from app.api.graphql.context import GraphQLContext
from app.api.graphql.enums import AbnormalFlag as AbnormalFlagEnum
from app.api.graphql.enums import VitalSignType as VitalSignTypeEnum
from app.api.graphql.types.provider import Provider
from app.models.observations import LabResult as LabResultModel
from app.models.observations import VitalSign as VitalSignModel


@strawberry.type(description="A single lab test result.")
class LabResult:
    id: strawberry.ID
    test_name: str
    test_code: str
    value: str
    unit: str | None
    reference_range: str | None
    abnormal_flag: AbnormalFlagEnum
    resulted_at: datetime

    _ordered_by: strawberry.Private[str]

    @strawberry.field(description="The provider who ordered this test.")
    async def ordered_by(self, info: strawberry.Info[GraphQLContext, None]) -> Provider:
        model = await info.context.loaders.providers_by_id.load(self._ordered_by)
        return Provider.from_model(model)

    @classmethod
    def from_model(cls, lab_result: LabResultModel) -> "LabResult":
        return cls(
            id=strawberry.ID(str(lab_result.id)),
            test_name=lab_result.test_name,
            test_code=lab_result.test_code,
            value=lab_result.value,
            unit=lab_result.unit,
            reference_range=lab_result.reference_range,
            abnormal_flag=lab_result.abnormal_flag,
            resulted_at=lab_result.resulted_at,
            _ordered_by=lab_result.ordered_by,
        )


@strawberry.type(description="A point-in-time vital sign measurement.")
class VitalSign:
    id: strawberry.ID
    vital_type: VitalSignTypeEnum
    value: float
    unit: str
    recorded_at: datetime

    @classmethod
    def from_model(cls, vital_sign: VitalSignModel) -> "VitalSign":
        return cls(
            id=strawberry.ID(str(vital_sign.id)),
            vital_type=vital_sign.vital_type,
            value=float(vital_sign.value),
            unit=vital_sign.unit,
            recorded_at=vital_sign.recorded_at,
        )
