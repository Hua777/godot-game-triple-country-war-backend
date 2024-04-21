from twisted.web import resource


class HttpHealthResource(resource.Resource):
    def render_GET(self, request):
        return b"OK"


def install(root: resource.Resource):
    root.putChild(b"health", HttpHealthResource())
