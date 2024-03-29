import json
from decimal import Decimal
from typing import Dict, Generic, List, Optional, Tuple, TypeVar, Union

import pytest
from pydantic import BaseModel, ValidationError, constr

from synclane import (
    AbstractAsyncProcedure,
    AbstractProcedure,
    AbstractRpc,
    ProcedureNotFound,
)
from synclane._export import TsExporter

from .base import dumb_async_rpc_cls, dumb_rpc_cls, rpc_async_cls, rpc_cls


def test_success(rpc_cls):
    class UserParams(BaseModel):
        uid: str

    class UserDetails(BaseModel):
        uid: str
        name: constr(min_length=1)

    class GetUser(AbstractProcedure):
        def call(self, in_: UserParams, context) -> UserDetails:
            return UserDetails(uid=in_.uid, name="John")

    rpc = rpc_cls().register(GetUser)

    result = json.loads(
        rpc.call(
            {
                "id": 1,
                "method": "GetUser",
                "params": {"uid": "7fa8d"},
            },
            None,
        )
    )
    assert result == {
        "id": 1,
        "jsonrpc": "2.0",
        "result": {"name": "John", "uid": "7fa8d"},
    }

    result = json.loads(
        rpc.call(
            {
                "id": 1,
                "method": "missing",
                "params": {"uid": "7fa8d"},
            },
            None,
        )
    )
    assert result == {
        "error": {"code": -32601, "message": "Method not found"},
        "id": 1,
        "jsonrpc": "2.0",
    }

    result = json.loads(
        rpc.call(
            {
                "id": 1,
                "method": "GetUser",
                "params": {},
            },
            None,
        )
    )
    # fmt: off
    assert result == { "error": { "code": -32600, "details": [ { "input": {}, "loc": ["uid"], "msg": "Field required", "type": "missing", } ], "message": "Validation error", }, "id": 1, "jsonrpc": "2.0", }
    # fmt: on

    result = json.loads(
        rpc.call(
            {},
            None,
        )
    )
    # fmt: off
    assert result == { "error": { "code": -32600, "details": [ { "input": {}, "loc": ["id"], "msg": "Field required", "type": "missing", }, { "input": {}, "loc": ["method"], "msg": "Field required", "type": "missing", }, { "input": {}, "loc": ["params"], "msg": "Field required", "type": "missing", }, ], "message": "Validation error", }, "id": None, "jsonrpc": "2.0", }
    # fmt: on


@pytest.mark.asyncio
async def test_async(rpc_async_cls, dumb_async_rpc_cls):
    class UserParams(BaseModel):
        uid: str

    class UserDetails(BaseModel):
        params: List[UserParams]
        name: str

    def permission1(context):
        pass

    async def permission2(context):
        pass

    class GetUser(AbstractAsyncProcedure):
        PERMISSIONS = (permission1, permission2)

        async def call_async(self, in_: UserParams, context) -> UserDetails:
            return UserDetails(params=[in_], name="John")

    class GetUser2(AbstractProcedure):
        PERMISSIONS = (permission1, permission2)

        def call(self, in_: UserParams, context) -> UserDetails:
            return UserDetails(params=[in_], name="John")

    rpc = rpc_async_cls().register(GetUser, GetUser2)

    result = json.loads(
        await rpc.call_async(
            {
                "id": 1,
                "method": "GetUser",
                "params": {"uid": "7fa8d"},
            },
            None,
        )
    )
    assert result == {
        "id": 1,
        "jsonrpc": "2.0",
        "result": {"name": "John", "params": [{"uid": "7fa8d"}]},
    }
    result = json.loads(
        await rpc.call_async(
            {
                "id": 1,
                "method": "GetUser2",
                "params": {"uid": "7fa8d"},
            },
            None,
        )
    )
    assert result == {
        "id": 1,
        "jsonrpc": "2.0",
        "result": {"name": "John", "params": [{"uid": "7fa8d"}]},
    }
    result = json.loads(
        await rpc.call_async(
            {
                "id": 1,
                "method": "GetUser2",
                "params": {},
            },
            None,
        )
    )
    assert result == {
        "error": {
            "code": -32600,
            "details": [
                {
                    "input": {},
                    "loc": ["uid"],
                    "msg": "Field required",
                    "type": "missing",
                }
            ],
            "message": "Validation error",
        },
        "id": 1,
        "jsonrpc": "2.0",
    }

    result = json.loads(
        await rpc.call_async(
            {"id": 1, "method": "missing", "params": None},
            None,
        )
    )
    assert result == {
        "error": {"code": -32601, "message": "Method not found"},
        "id": 1,
        "jsonrpc": "2.0",
    }

    with pytest.raises(ValidationError):
        await dumb_async_rpc_cls().register(GetUser2).call_async(
            {
                "id": 1,
                "method": "GetUser2",
                "params": {},
            },
            None,
        )

    with pytest.raises(TypeError):

        class A(AbstractAsyncProcedure):
            def call_async(self, in_: UserParams, context) -> UserDetails:
                return UserDetails(params=[in_], name="John")


def test_complex_types(rpc_cls):
    class UserParams(BaseModel):
        uid: str

    class UserDetails(BaseModel):
        params: UserParams
        name: str

    class GetUser(AbstractProcedure):
        def call(self, in_: UserParams, context) -> UserDetails:
            return UserDetails(params=in_, name="John")

    rpc = rpc_cls().register(GetUser)

    result = json.loads(
        rpc.call(
            {
                "id": 1,
                "method": "GetUser",
                "params": {"uid": "7fa8d"},
            },
            None,
        )
    )
    assert result == {
        "id": 1,
        "jsonrpc": "2.0",
        "result": {"name": "John", "params": {"uid": "7fa8d"}},
    }


def test_exceptions(dumb_rpc_cls, dumb_async_rpc_cls, rpc_cls, rpc_async_cls):
    class UserParams(BaseModel):
        uid: str

    class UserDetails(BaseModel):
        uid: str
        name: str

    class GetUser(AbstractProcedure):
        def call(self, in_: UserParams, context) -> UserDetails:
            return dict(uid=in_.uid, name="John")

    class GetUser2(AbstractAsyncProcedure):
        @staticmethod
        async def call_async(in_: UserParams, context) -> UserDetails:
            return dict(uid=in_.uid, name="John")

    rpc = dumb_rpc_cls().register(GetUser)
    async_rpc = rpc_async_cls().register(GetUser)

    with pytest.raises(ValueError):
        rpc.register(GetUser)
    with pytest.raises(ValueError):
        async_rpc.register(GetUser)

    with pytest.raises(ValidationError):
        result = rpc.call(
            {
                "id": 1,
                "method": "GetUser",
                "params": {},
            },
            None,
        )

    for p in (GetUser2, bool):
        with pytest.raises(TypeError):
            rpc.register(p)

    with pytest.raises(TypeError):
        async_rpc.register(bool)

    result = json.loads(
        rpc.call(
            {
                "id": 1,
                "method": "GetUser",
                "params": {"uid": "7fa8d"},
            },
            None,
        )
    )
    assert result == {
        "id": 1,
        "jsonrpc": "2.0",
        "result": {"name": "John", "uid": "7fa8d"},
    }

    class GetBad(AbstractProcedure):
        def call(self, in_: UserParams, context) -> UserDetails:
            return {}

    rpc.register(GetBad)
    with pytest.raises(ValidationError):
        result = rpc.call(
            {
                "id": 1,
                "method": "GetBad",
                "params": {"uid": "7fa8d"},
            },
            None,
        )

    class UnauthorizedException(Exception):
        pass

    def is_authorized(context):
        if "user" not in context:
            raise UnauthorizedException

    class AuthorizedGet(AbstractProcedure):
        PERMISSIONS = (is_authorized,)

        @classmethod
        def call(cls, in_: UserParams, context) -> dict:
            return {}

    rpc.register(AuthorizedGet)

    with pytest.raises(ValueError):
        rpc.register(AuthorizedGet)

    with pytest.raises(UnauthorizedException):
        rpc.call(
            {
                "id": 1,
                "method": "AuthorizedGet",
                "params": {"uid": "7fa8d"},
            },
            {},
        )

    assert json.loads(
        rpc.call(
            {
                "id": 1,
                "method": "AuthorizedGet",
                "params": {"uid": "7fa8d"},
            },
            {"user": 1},
        )
    ) == {"id": 1, "jsonrpc": "2.0", "result": {}}

    with pytest.raises(ValueError):

        class GetBad2(AbstractProcedure):
            def call(self, in_: UserParams, context):
                return {}

    with pytest.raises(ValueError):

        class GetBad3(AbstractProcedure):
            def call(self, in_, context) -> dict:
                return {}

    with pytest.raises(ValueError):

        class GetBad4(AbstractProcedure):
            def call(self):
                return {}

    with pytest.raises(ValueError):

        class GetBad5(AbstractProcedure):
            @staticmethod
            def call() -> dict:
                return {}

    with pytest.raises(TypeError):

        class A(AbstractProcedure):
            async def call():
                pass

    with pytest.raises(TypeError):

        class A(AbstractAsyncProcedure):
            def call_async():
                pass
