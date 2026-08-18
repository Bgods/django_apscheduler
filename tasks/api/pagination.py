from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class FlexiblePagination(PageNumberPagination):
    """页码超出范围时返回空结果而非 404"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 10000

    def paginate_queryset(self, queryset, request, view=None):
        # 先尝试标准分页
        try:
            return super().paginate_queryset(queryset, request, view)
        except Exception:
            # 页码超出范围，返回空列表
            self.page = None
            self.paginator = super().django_paginator_class(
                self.get_page_size(request) or 20
            )
            return []

    def get_paginated_response(self, data):
        if self.page is None:
            return Response({
                'count': 0,
                'next': None,
                'previous': None,
                'results': data,
            })
        return super().get_paginated_response(data)
