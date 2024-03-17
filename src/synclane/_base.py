""""Defines base Rpc and Procedure classes."""

import abc
import asyncio
import inspect
from io import BytesIO
from typing import Any, Awaitable, Callable, Optional, Sequence, Type

from pydantic import BaseModel, RootModel
from pydantic_core import to_json


class BaseRpcException(Exception):
    pass


class ProcedureNotFound(BaseRpcException):
    pass


def ensure_pydantic_model(some_type: Type[Any]):
    return (
        some_type if isinstance(some_type, type) and issubclass(some_type, BaseModel) else RootModel[some_type]  # type: ignore
    )


class ProcedureMeta(abc.ABCMeta):
    """Meta class, which creates AbstractProcedure and AbstractAsyncProcedure."""

    name: str
    in_type: Type[Any]
    out_type: Type[Any]

    def __new__(mcs, name, bases, dict_):
        cls = super().__new__(mcs, name, bases, dict_)
        cls.name = name
        if hasattr(cls, "call"):
            if asyncio.iscoroutinefunction(cls.call):
                raise TypeError(
                    "either make 'call' sync or inherit AbstractAsyncProcedure"
                )
            cls.in_type, cls.out_type = mcs.get_in_n_out_models(cls.call)
        if hasattr(cls, "call_async"):
            if not asyncio.iscoroutinefunction(cls.call_async):
                raise TypeError(
                    "either make 'call_async' async or inherit AbstractProcedure"
                )
            cls.in_type, cls.out_type = mcs.get_in_n_out_models(cls.call_async)
        return cls

    @staticmethod
    def get_in_n_out_models(method):
        signature = inspect.signature(method)
        return_annotation = signature.return_annotation
        if return_annotation is inspect.Signature.empty:
            raise ValueError(
                "missing return annotation", method, return_annotation
            )

        in_type = None
        for name, param in signature.parameters.items():
            if name == "self":
                continue
            in_type = param.annotation
            break

        if in_type is None or in_type is inspect.Signature.empty:
            raise ValueError("missing input type annotation", method, in_type)

        return (
            ensure_pydantic_model(in_type),
            ensure_pydantic_model(return_annotation),
        )


class AbstractProcedure(metaclass=ProcedureMeta):
    """Base class of an synchronous RPC procedure."""

    PERMISSIONS: Sequence[Callable[[Any], None]] = ()

    in_type: Type[Any]
    out_type: Type[Any]

    def _call(self, raw_data, context):
        self.check_permissions(context)
        in_ = self.in_type.model_validate(raw_data)
        pump_result = self.call(in_, context)
        return self.out_type.model_validate(pump_result)

    def check_permissions(self, context):
        for permission in self.PERMISSIONS:
            permission(context)

    @abc.abstractmethod
    def call(self, in_: str, context) -> str:
        raise NotImplementedError


class AbstractAsyncProcedure(metaclass=ProcedureMeta):
    """Base class of an asynchronous RPC procedure."""

    PERMISSIONS: Sequence[Callable[[Any], Optional[Awaitable[Any]]]] = ()

    in_type: Type[Any]
    out_type: Type[Any]

    def __init__(self):
        self._permissions = tuple(
            (perm, asyncio.iscoroutinefunction(perm))
            for perm in self.PERMISSIONS
        )

    async def _call(self, raw_data, context):
        await self.check_permissions(context)
        in_ = self.in_type.model_validate(raw_data)
        pump_result = await self.call_async(in_, context)
        return self.out_type.model_validate(pump_result)

    async def check_permissions(self, context):
        for permission, is_async in self._permissions:
            if is_async:
                await permission(context)  # type: ignore
            else:
                permission(context)

    @abc.abstractmethod
    async def call_async(self, in_: str, context) -> str:
        raise NotImplementedError


class RpcRequest(BaseModel):
    # jsonrpc: str
    id: int
    method: str
    params: Any


class AbstractRpc(abc.ABC):
    """Abstract class of a synchronous RPC service."""

    __slots__ = ["procedures"]

    def __init__(self):
        self.procedures = {}

    def register(self, *procedures):
        for procedure in procedures:
            if issubclass(procedure, AbstractAsyncProcedure):
                raise TypeError(
                    "subclass AbstractAsyncRpc to use AbstractAsyncProcedure descendants"
                )
            if not issubclass(procedure, AbstractProcedure):
                raise TypeError("not a procedure", procedure)

            name = procedure.name
            if name in self.procedures:
                raise ValueError(
                    "non unique procedure name",
                    self.procedures[name],
                    procedure,
                )
            self.procedures[name] = procedure()

        return self

    def call(self, raw_data, context) -> bytes:
        buf = BytesIO()
        write_ = buf.write

        request_id = b"null"
        try:
            rpc_request = (
                RpcRequest.model_validate_json(raw_data)
                if isinstance(raw_data, (str, bytes, bytearray))
                else RpcRequest.model_validate(raw_data)
            )
            request_id = str(rpc_request.id).encode("utf-8")
            if rpc_request.method not in self.procedures:
                write_(
                    b'{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": '
                )
                write_(request_id)
                write_(b"}")
                return buf.getvalue()

            result = self.procedures[  # pylint: disable=protected-access
                rpc_request.method
            ]._call(rpc_request.params, context)

            write_(b'{"jsonrpc": "2.0", "result": ')
            write_(result.__pydantic_serializer__.to_json(result))
            write_(b', "id": ')
            write_(request_id)
            write_(b"}")
            return buf.getvalue()

        except Exception as e:  # pylint: disable=broad-exception-caught
            data = self.prepare_exception(raw_data, context, e)
            if data is None:
                raise

            write_(b'{"jsonrpc": "2.0", "error": ')
            write_(to_json(data))
            write_(b', "id": ')
            write_(request_id)
            write_(b"}")
            return buf.getvalue()

    @abc.abstractmethod
    def prepare_exception(self, raw_data, context, exc):
        raise NotImplementedError

    def ts_dump(self, filename):
        """Dumps typescript type definitions and client to a file."""
        from ._export import TsExporter

        return TsExporter(self).write(filename)


class AbstractAsyncRpc(abc.ABC):
    """Abstract class of a asynchronous RPC service."""

    __slots__ = ["procedures"]

    def __init__(self):
        self.procedures = {}

    def register(self, *procedures):
        for procedure in procedures:
            if not issubclass(
                procedure, (AbstractProcedure, AbstractAsyncProcedure)
            ):
                raise TypeError("not a procedure", procedure)

            name = procedure.name
            if name in self.procedures:
                raise ValueError(
                    "non unique procedure name",
                    self.procedures[name],
                    procedure,
                )
            self.procedures[name] = procedure()
        return self

    async def call_async(self, raw_data, context) -> bytes:
        buf = BytesIO()
        write_ = buf.write
        request_id = b"null"
        try:
            rpc_request = (
                RpcRequest.model_validate_json(raw_data)
                if isinstance(raw_data, (str, bytes, bytearray))
                else RpcRequest.model_validate(raw_data)
            )

            request_id = str(rpc_request.id).encode("utf-8")
            if rpc_request.method not in self.procedures:
                write_(
                    b'{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": '
                )
                write_(request_id)
                write_(b"}")
                return buf.getvalue()

            procedure = self.procedures[rpc_request.method]
            if isinstance(procedure, AbstractAsyncProcedure):
                result = (
                    await procedure._call(  # pylint: disable=protected-access
                        rpc_request.params, context
                    )
                )
            else:
                result = procedure._call(  # pylint: disable=protected-access
                    rpc_request.params, context
                )

            write_(b'{"jsonrpc": "2.0", "result": ')
            write_(result.__pydantic_serializer__.to_json(result))
            write_(b', "id": ')
            write_(request_id)
            write_(b"}")
            return buf.getvalue()

        except Exception as e:  # pylint: disable=broad-exception-caught
            data = self.prepare_exception(raw_data, context, e)
            if data is None:
                raise
            write_(b'{"jsonrpc": "2.0", "error": ')
            write_(to_json(data))
            write_(b', "id": ')
            write_(request_id)
            write_(b"}")
            return buf.getvalue()

    @abc.abstractmethod
    def prepare_exception(self, raw_data, context, exc):
        raise NotImplementedError

    def ts_dump(self, filename):
        """Dumps typescript type definitions and client to a file."""
        from ._export import TsExporter

        return TsExporter(self).write(filename)
