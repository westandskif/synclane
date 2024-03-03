import logging
from datetime import date, datetime
from enum import Enum
from typing import List

from fastapi import FastAPI, Request
from pydantic import BaseModel, ValidationError, constr

from synclane import (
    AbstractAsyncProcedure,
    AbstractAsyncRpc,
    AbstractProcedure,
    TsExporter,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


############################################################
############# DEFINE PROCEDURES ############################
class UserParams(BaseModel):
    uid: constr(min_length=1)
    created_after: datetime
    dob_after: date


class AccessLevel(Enum):
    BASIC = 1
    ADMIN = 2


class UserDetails(BaseModel):
    uid: str
    name: str
    created: datetime
    dob: date
    access_level: AccessLevel


def is_authorized(context):
    # context can be anything; let it be a request here
    if context.headers.get("x-jwt-token", "") != "secret":
        raise UnauthorizedError


class GetUsers(AbstractProcedure):
    PERMISSIONS = (is_authorized,)

    def call(self, in_: UserParams, context) -> List[UserDetails]:
        return [
            UserDetails(
                uid=in_.uid,
                name="John",
                created=in_.created_after,
                dob=in_.dob_after,
                access_level=AccessLevel.BASIC,
            )
        ]


# an example of async one
class GetUsers2(AbstractAsyncProcedure):
    PERMISSIONS = (is_authorized,)

    async def call_async(self, in_: UserParams, context) -> List[UserDetails]:
        return [
            UserDetails(
                uid=in_.uid,
                name="John",
                created=in_.created_after,
                dob=in_.dob_after,
                access_level=AccessLevel.BASIC,
            )
        ]


############################################################
######## DEFINE RPC AND REGISTER PROCEDURES ################
class UnauthorizedError(Exception):
    pass


class Rpc(AbstractAsyncRpc):
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


rpc = Rpc().register(GetUsers, GetUsers2)


############################################################
############# DUMP TS ######################################
rpc.ts_dump("src/out.ts")

############################################################
############# CONNECT TO API ENDPOINT ######################
app = FastAPI()


@app.post("/")
async def read_root(request: Request):
    return await rpc.call_async(await request.body(), request)
