from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Literal

from airflow.models import BaseOperator

if TYPE_CHECKING:
    from airflow.utils.context import Context
    from great_expectations import ExpectationSuite
    from great_expectations.core.batch import BatchParameters
    from great_expectations.core.batch_definition import BatchDefinition
    from great_expectations.data_context import AbstractDataContext
    from great_expectations.expectations import Expectation


class GXValidateBatchOperator(BaseOperator):
    def __init__(
        self,
        configure_batch_definition: Callable[[AbstractDataContext], BatchDefinition],
        expect: Expectation | ExpectationSuite,
        batch_parameters: BatchParameters | None = None,
        context_type: Literal["ephemeral", "cloud"] = "ephemeral",
        result_format: Literal["BOOLEAN_ONLY", "BASIC", "SUMMARY", "COMPLETE"]
        | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        if batch_parameters is None:
            self.batch_parameters = {}
        else:
            self.batch_parameters = batch_parameters
        self.context_type = context_type
        self.configure_batch_definition = configure_batch_definition
        self.expect = expect
        self.result_format = result_format

    def execute(self, context: Context) -> dict:
        import great_expectations as gx

        gx_context = gx.get_context(mode=self.context_type)
        batch_definition = self.configure_batch_definition(gx_context)
        if isinstance(self.expect, gx.expectations.Expectation):
            suite = gx.ExpectationSuite(name=self.task_id, expectations=[self.expect])
        else:
            suite = self.expect
        validation_definition = gx_context.validation_definitions.add_or_update(
            validation=gx.ValidationDefinition(
                name=self.task_id,
                suite=suite,
                data=batch_definition,
            ),
        )
        if self.result_format:
            result = validation_definition.run(
                batch_parameters=self.batch_parameters,
                result_format=self.result_format,
            )
        else:
            result = validation_definition.run(
                batch_parameters=self.batch_parameters,
            )

        return result.describe_dict()
