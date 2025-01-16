from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Literal

from airflow.models import BaseOperator

if TYPE_CHECKING:
    from airflow.utils.context import Context
    from great_expectations import Checkpoint
    from great_expectations.checkpoint.checkpoint import CheckpointDescriptionDict
    from great_expectations.core.batch import BatchParameters
    from great_expectations.data_context import AbstractDataContext, FileDataContext


class GXValidateCheckpointOperator(BaseOperator):
    def __init__(
        self,
        configure_checkpoint: Callable[[AbstractDataContext], Checkpoint],
        batch_parameters: BatchParameters | None = None,
        context_type: Literal["ephemeral", "cloud", "file"] = "ephemeral",
        configure_file_data_context: Callable[[], FileDataContext] | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        if batch_parameters is None:
            self.batch_parameters = {}
        else:
            self.batch_parameters = batch_parameters
        if context_type == "file" and not configure_file_data_context:
            raise ValueError(
                "Parameter `configure_file_data_context` must be specified if `context_type` is `file`"
            )
        self.context_type = context_type
        self.configure_file_data_context = configure_file_data_context
        self.configure_checkpoint = configure_checkpoint

    def execute(self, context: Context) -> CheckpointDescriptionDict:
        import great_expectations as gx

        gx_context: AbstractDataContext

        if self.context_type == "file":
            if not self.configure_file_data_context:
                raise ValueError(
                    "Parameter `configure_file_data_context` must be specified if `context_type` is `file`"
                )
            gx_context = self.configure_file_data_context()
        else:
            gx_context = gx.get_context(mode=self.context_type)
        checkpoint = self.configure_checkpoint(gx_context)

        runtime_batch_params = context.get("params", {}).get("gx_batch_parameters")  # type: ignore[call-overload]
        if runtime_batch_params:
            batch_parameters = runtime_batch_params
        else:
            batch_parameters = self.batch_parameters
        result = checkpoint.run(batch_parameters=batch_parameters)
        return result.describe_dict()
