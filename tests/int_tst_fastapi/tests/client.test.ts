import { callGetUser, AccessLevel, RPC_CONTEXT } from "../src/out";

test("API client", async () => {
    let start_ts = new Date();
    let dob = new Date(2000, 0, 1);
    RPC_CONTEXT.initFetch = (init: RequestInit) => {
        let headers = init.headers = init.headers || {};
        headers["X-Jwt-Token"] = "secret";
        return init;
    };
    expect(callGetUser({ uid: "dasd", start_ts: start_ts, dob: dob }).$promise)
        .resolves
        .toEqual({ uid: "dasd", name: "John", start_ts: start_ts, dob: dob, access_level: AccessLevel.BASIC });

    expect(callGetUser({ uid: "", start_ts: start_ts, dob: dob }).$promise).rejects.toEqual({
        code: -32600,
        message: 'Validation error',
        details: [
            {
                type: 'string_too_short',
                msg: 'String should have at least 1 character',
                input: '',
                loc: ["uid"],
            }
        ]
    });

    RPC_CONTEXT.initFetch = (init: RequestInit) => {
        let headers = init.headers = init.headers || {};
        headers["X-Jwt-Token"] = "secret-bad";
        return init;
    };
    expect(callGetUser({ uid: "dasd", start_ts: start_ts, dob: dob }).$promise)
        .rejects.toEqual({ code: -32000, message: 'unauthorized' });

});
