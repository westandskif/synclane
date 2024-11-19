# --8<-- [start:def_procedures]
import logging
from datetime import date, datetime
from enum import Enum
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError, conint

from synclane import (
    AbstractAsyncProcedure,
    AbstractAsyncRpc,
    AbstractProcedure,
    AbstractRpc,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class GetObjectParams(BaseModel):
    uid: UUID


class AccessLevel(Enum):
    BASIC = 1
    ADMIN = 2


class UserDetails(BaseModel):
    uid: UUID
    name: str
    created: datetime
    dob: date
    access_level: AccessLevel


def is_authorized(context):
    # context can be anything; let it be a request here
    if context.headers.get("x-jwt-token", "") != "secret":
        raise UnauthorizedError


class GetUser(AbstractProcedure):
    PERMISSIONS = (is_authorized,)

    def call(self, in_: GetObjectParams, context) -> UserDetails:
        return UserDetails(
            uid=in_.uid,
            name="John",
            created=datetime.fromtimestamp(0),
            dob=date(1970, 1, 1),
            access_level=AccessLevel.BASIC,
        )


# LET'S ADD FAKE PAGINATION AND MAKE IT ASYNC JUST FOR EXAMPLE
class Params(BaseModel):
    page: conint(gt=0) = 1
    created_after: Optional[datetime] = None
    dob_after: Optional[date] = None


T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    has_next: bool
    has_prev: bool
    data: List[T]


class GetUsers(AbstractAsyncProcedure):
    PERMISSIONS = (is_authorized,)

    async def call_async(self, in_: Params, context) -> Paginated[UserDetails]:
        return {
            "has_next": True,
            "has_prev": False,
            "data": [
                UserDetails(
                    uid="4eeb24a4-ecc1-4d9a-a43c-7263c6c60a07",
                    name="John",
                    created=in_.created_after,
                    dob=in_.dob_after,
                    access_level=AccessLevel.BASIC,
                )
            ],
        }


# --8<-- [end:def_procedures]


# --8<-- [start:def_rpc]
class UnauthorizedError(Exception):
    pass


class Rpc(AbstractAsyncRpc):  # OR AbstractRpc for sync only procedures
    def prepare_exception(self, raw_data, context, exc):
        # it can be anything, but the below tries to adhere to
        # https://www.jsonrpc.org/specification
        if isinstance(exc, ValidationError):
            return {
                "code": -32600,
                "message": "Validation error",
                "details": exc.errors(
                    include_url=False,
                    include_context=False,
                    include_input=True,
                ),
            }
        if isinstance(exc, UnauthorizedError):
            return {
                "code": -32000,
                "message": "unauthorized",
            }
        logger.exception(exc)
        return {
            "code": -1,
            "message": "Internal server error",
        }


rpc = Rpc().register(GetUsers, GetUser)


# dump TypeScript client
rpc.ts_dump("src/out.ts")
# --8<-- [end:def_rpc]


import sys

from django.conf import settings
from django.core.asgi import get_asgi_application
from django.core.management import execute_from_command_line
from django.http import HttpResponse
from django.urls import path


settings.configure(
    DEBUG=True,
    SECRET_KEY="8fashd9f87has8d7fh0a9shdf098asd098fja09sdf",
    ROOT_URLCONF=sys.modules[__name__],
)


# --8<-- [start:django_async]
from django.http import HttpResponse


async def index(request):
    return HttpResponse(
        await rpc.call_async(request.body, request),
        content_type="application/json",
    )


# --8<-- [end:django_async]

"""
# --8<-- [start:django_sync]
from django.http import HttpResponse


def index(request):
    return HttpResponse(
        rpc.call(request.body, request),
        content_type="application/json",
    )


# --8<-- [end:django_sync]
"""


urlpatterns = [
    path(r"", index),
]


app_django = get_asgi_application()


# --8<-- [start:fastapi_async]
from fastapi import FastAPI, Request, Response


app_fast_api = FastAPI()


@app_fast_api.post("/")
async def read_root(request: Request):
    return Response(
        await rpc.call_async(
            await request.body(),  # always full body as is
            request,  # anything to be passed to procedures as context
        ),
        media_type="application/json",
    )


# --8<-- [end:fastapi_async]
"""
# --8<-- [start:fastapi_sync]
from fastapi import FastAPI, Request, Response


app_fast_api = FastAPI()


@app_fast_api.post("/")
async def read_root(request: Request):
    return Response(
        rpc.call(
            await request.body(),  # always full body as is
            request,  # anything to be passed to procedures as context
        ),
        media_type="application/json",
    )


# --8<-- [end:fastapi_sync]
"""
