from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PaginacaoPadrao(PageNumberPagination):
    """Paginação da API.

    Além dos campos padrão do DRF, devolve `page` e `total_pages` porque o
    frontend precisa saber em que página está sem ter que parsear as URLs de
    `next`/`previous`.
    """

    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })
