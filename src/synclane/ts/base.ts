const ANY_DATE: Date = new Date();
const TIMEZONE_OFFSET_IN_MS: number = ANY_DATE.getTimezoneOffset() * 60000;

function strToDate(d: string): Date {
    let dt = new Date(d);
    return new Date(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate());
}
function dateToStr(d: Date): string {
    return new Date(d.getTime() - TIMEZONE_OFFSET_IN_MS).toISOString().split("T")[0]
}
interface RpcContext {
    url: string;
    initFetch?: (init: RequestInit) => RequestInit;
}
class AbortableRequest<T> {
    public $promise: Promise<T>;
    private controller: AbortController;
    public abort() {
        this.controller.abort();
    }

    constructor($promise: Promise<T>, controller: AbortController) {
        this.$promise = $promise;
        this.controller = controller;
    }
}
export function abortableFetch<T, U>(
    params: T,
    rpcContext: RpcContext,
    paramsToPrimitive: (params: T) => any,
    primitiveToResult: (data: any) => U,
): AbortableRequest<U> {
    let controller = new AbortController();
    let init: RequestInit = {
        method: "POST",
        headers: {
            Accept: "application/json",
            "Content-Type": "application/json;charset=UTF-8",
        },
        signal: controller.signal,
        body: JSON.stringify(paramsToPrimitive(params)),
    };

    init.signal = controller.signal;
    if (rpcContext.initFetch !== undefined) {
        init = rpcContext.initFetch(init);
    }

    return new AbortableRequest<U>(
        fetch(rpcContext.url, init).then((response) => response.json()).then(primitiveToResult),
        controller,
    );
}

// ===========================================================================
// ===========================================================================

