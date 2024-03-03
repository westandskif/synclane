import logging
import sys
from datetime import date, datetime
from enum import Enum
from typing import List

from fastapi import FastAPI, Request
from pydantic import BaseModel, ValidationError, constr

from synclane import (
    AbstractAsyncProcedure,
    AbstractAsyncRpc,
    AbstractProcedure,
    AbstractRpc,
    TsExporter,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


######## ERROR HANDLING #########################
class UnauthorizedError(Exception):
    pass


def is_authorized(context):
    if context.headers.get("x-jwt-token", "") != "secret":
        raise UnauthorizedError


class Rpc(AbstractAsyncRpc):
    def prepare_exception(self, raw_data, context, exc):
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


############# PROCEDURE #########################
class UserParams(BaseModel):
    uid: constr(min_length=1)
    start_ts: List[datetime]
    dob: date


class AccessLevel(Enum):
    BASIC = 1
    ADMIN = 2


class UserDetails(BaseModel):
    uid: str
    name: str
    start_ts: List[datetime]
    dob: date
    access_level: AccessLevel


class GetUser(AbstractAsyncProcedure):
    PERMISSIONS = (is_authorized,)

    async def call_async(self, in_: UserParams, context) -> UserDetails:
        return UserDetails(
            name="John", access_level=AccessLevel.BASIC, **in_.dict()
        )


class GetUser2(AbstractProcedure):
    PERMISSIONS = (is_authorized,)

    def call(self, in_: UserParams, context) -> UserDetails:
        return UserDetails(
            name="John", access_level=AccessLevel.BASIC, **in_.dict()
        )


rpc = Rpc().register(GetUser, GetUser2)


############# EXPORTING TS ######################
TsExporter(rpc).write("src/out.ts")


app = FastAPI()


@app.post("/")
async def read_root(request: Request):
    return await rpc.call_async(await request.body(), request)
