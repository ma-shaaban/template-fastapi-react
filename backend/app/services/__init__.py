# Business logic lives here — plain modules the routers call (notifications,
# scheduling, external APIs, domain rules). Keep routers thin: parse/validate
# the request, call a service, shape the response. Services are where the
# testable logic goes.
