import {
    callGetUsers,
    callGetUsers2,
    AccessLevel,
    rpcConfig,
} from "../src/out";

test("API client", async () => {
    rpcConfig.url = "http://backend:8000";
    let created_after = new Date();
    let dob_after = new Date(2000, 0, 1);

    // example of adding authentication
    // init is fetch options - https://developer.mozilla.org/en-US/docs/Web/API/fetch
    rpcConfig.initFetch = (init: RequestInit) => {
        let headers = (init.headers = init.headers || {});
        headers["X-Jwt-Token"] = "secret";
        return init;
    };

    expect(
        callGetUsers({ uid: "dasd", created_after: created_after, dob_after: dob_after }).$promise,
    ).resolves.toEqual([{
        uid: "dasd",
        name: "John",
        created: created_after,
        dob: dob_after,
        access_level: AccessLevel.BASIC,
    }]);
    expect(
        callGetUsers2({ uid: "dasd", created_after: created_after, dob_after: dob_after }).$promise,
    ).resolves.toEqual([{
        uid: "dasd",
        name: "John",
        created: created_after,
        dob: dob_after,
        access_level: AccessLevel.BASIC,
    }]);

    // validation error
    expect(
        callGetUsers({ uid: "", created_after: created_after, dob_after: dob_after }).$promise,
    ).rejects.toEqual({
        code: -32600,
        message: "Validation error",
        details: [
            {
                type: "string_too_short",
                msg: "String should have at least 1 character",
                input: "",
                loc: ["uid"],
            },
        ],
    });

    // breaking authentication
    rpcConfig.initFetch = (init: RequestInit) => {
        let headers = (init.headers = init.headers || {});
        headers["X-Jwt-Token"] = "secret-bad";
        return init;
    };
    expect(
        callGetUsers({ uid: "dasd", created_after: created_after, dob_after: dob_after }).$promise,
    ).rejects.toEqual({ code: -32000, message: "unauthorized" });
});
