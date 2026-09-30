from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Checagem de saúde para o healthcheck do container e para o proxy.

    Confirma que o processo responde E que o banco está alcançável — um
    endpoint que só devolve 200 não distingue "app de pé" de "app de pé sem
    banco", que é justamente o estado em que não se deve mandar tráfego.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    @extend_schema(
        responses={
            200: inline_serializer(
                name='Health',
                fields={
                    'status': serializers.CharField(),
                    'banco': serializers.BooleanField(),
                },
            )
        },
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except Exception:
            return Response({'status': 'degradado', 'banco': False}, status=503)

        return Response({'status': 'ok', 'banco': True})
