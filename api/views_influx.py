from rest_framework.viewsets import ViewSet
from rest_framework.response import Response


class InfluxGenericViewSet(ViewSet):
    """Generic read only viewset"""
    def param_check(self, request):
        missing_query_params = []
        for param in self.required_filter_params:
            if param not in request.GET:
                missing_query_params.append(param)
        if missing_query_params:
            missing_query_params = "/".join(missing_query_params)
            ValueError(f"Missing required query parameters: {missing_query_params}")

    def initial(self, request, *args, **kwargs):
        self.param_check(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        try:
            self.initial(request, *args, **kwargs)
        except ValueError as e:
            return Response(e, status=400)
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        self.response = handler(request, *args, **kwargs)
        return self.response


class ListViewSet(InfluxGenericViewSet):
    additional_filter_params = []
    required_filter_params = []

    def generate_tags(self, request):
        tags = {}
        for param in self.additional_filter_params + self.required_filter_params:
            if param in request.GET:
                value = request.GET[param]
                tags[param] = value
        return tags

    def list(self, request):
        timerange = request.GET
        tags = self.generate_tags(request)
        dataset = self.model(**tags).filter(timerange)
        return Response(dataset)
