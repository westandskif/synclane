import json

import pytest
from pydantic import BaseModel, ValidationError
import subprocess

from synclane import AbstractProcedure, AbstractRpc, ProcedureNotFound


@pytest.fixture
def rpc_cls():
    class Rpc(AbstractRpc):
        def prepare_exception(self, raw_data, context, exc):
            if isinstance(exc, ValidationError):
                return {
                    "code": -32600,
                    "message": "Validation error",
                    "details": exc.errors(
                        include_url=False,
                        include_context=True,
                        include_input=True,
                    ),
                }

    return Rpc


@pytest.fixture
def dumb_rpc_cls():
    class Rpc(AbstractRpc):
        def prepare_exception(self, raw_data, context, exc):
            pass

    return Rpc


TSC_EXECUTABLE_CHECKED = False


def check_ts(ts_file):
    global TSC_EXECUTABLE_CHECKED
    if not TSC_EXECUTABLE_CHECKED:
        completed_process = subprocess.run(f"tsc --version", shell=True)
        assert completed_process.returncode == 0, "tsc is not available"
        TSC_EXECUTABLE_CHECKED = True

    completed_process = subprocess.run(
        f"tsc --strict --noEmit {ts_file}", shell=True
    )
    return completed_process.returncode == 0
