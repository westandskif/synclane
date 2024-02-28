import subprocess

import pytest
from pydantic import ValidationError

from synclane import AbstractAsyncRpc, AbstractRpc


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
def rpc_async_cls():
    class Rpc(AbstractAsyncRpc):
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


@pytest.fixture
def dumb_async_rpc_cls():
    class AsyncRpc(AbstractAsyncRpc):
        def prepare_exception(self, raw_data, context, exc):
            pass

    return AsyncRpc


TSC_EXECUTABLE_CHECKED = False


def check_ts(ts_file):
    global TSC_EXECUTABLE_CHECKED
    if not TSC_EXECUTABLE_CHECKED:
        completed_process = subprocess.run(f"tsc --version", shell=True)
        assert completed_process.returncode == 0, "tsc is not available"
        TSC_EXECUTABLE_CHECKED = True

    completed_process = subprocess.run(
        f"tsc --lib es2015,dom --strict --noEmit {ts_file}", shell=True
    )
    return completed_process.returncode == 0
