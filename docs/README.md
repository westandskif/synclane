# Welcome to synclane

`synclane` simplifies development of systems with Python backend and TypeScript
frontend.

[![License](https://img.shields.io/github/license/westandskif/synclane.svg)](https://github.com/westandskif/synclane/blob/master/LICENSE.txt)
[![codecov](https://codecov.io/gh/westandskif/synclane/branch/master/graph/badge.svg)]( https://codecov.io/gh/westandskif/synclane)
[![Tests status](https://github.com/westandskif/synclane/workflows/tests/badge.svg)](https://github.com/westandskif/synclane/actions/workflows/pytest.yml)
[![Docs status](https://readthedocs.org/projects/synclane/badge/?version=latest)](https://synclane.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://badge.fury.io/py/synclane.svg)](https://pypi.org/project/synclane/)
[![Downloads](https://static.pepy.tech/badge/synclane)](https://pepy.tech/project/synclane)
[![Python versions](https://img.shields.io/pypi/pyversions/synclane.svg)](https://pypi.org/project/synclane/)

## Usage

1. define procedures
1. define RPC instance, its error handling method and register procedures
1. dump typescript, making sure procedure in/out types are browser friendly
1. connect RPC to an API
1. on TypeScript side: import `rpcConfig` and initialize:
   - `rpcConfig.url`: url where RPC is listening
   - `rpcConfig.initFetch` (optional): function, which accepts and can mutate
     [fetch options](https://developer.mozilla.org/en-US/docs/Web/API/fetch)
     as needed

## Benefits

#### Automated typescript client generation

Of course, it's possible to annotate your API, export an OpenAPI schema and
generate a typescript client from it. However it will lack the below nice bits.

#### Browser Dates done right

Javascript doesn't have a separate `date` type, so it uses `Date` for both
python's `date` and `datetime`.

Hence when you pass `2000-01-01` to a browser in New York, the browser will
read it as UTC datetime and then convert it to the local timezone, so it will
give you Dec 31, 1991 7:00PM, which is fine if you wanted to work with a
particular moment in time, but what if you wanted to display someone's date of
birth? That's why lacking date type is a problem.

`synclane` will see that you wanted to pass python's `date` to the browser and
will automatically prepare it in the browser, so that Jan 1st is preserved in
the case above.

#### Browser friendly types only

`synclane` raises an exception if you use types, which browser won't be able to
understand.

#### No need to define URLs

Once you name a procedure, e.g. `AddUser`, you just get `callAddUser` function
in the typescript client. You don't need to define any other identifier like
API endpoint url.

#### Enums

If your procedure in/out types include enums, they will become available in the
typescript client.

## Installation

```bash
pip install synclane
```

[pydantic](https://github.com/pydantic/pydantic) is the only dependency.

## Example

/// tab | main.py

```python
{!../tests/int_tst_fastapi/main.py!}
```

///

/// tab | client.test.ts

```typescript
{!../tests/int_tst_fastapi/tests/client.test.ts!}
```

///
