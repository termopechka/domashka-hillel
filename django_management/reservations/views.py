from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.authentication import ServiceAPIKeyAuthentication

from .exceptions import ReservationStateConflict
from .models import Reservation
from .serializer import (
    InsufficientStockResponseSerializer,
    ReservationCancelSerializer,
    ReservationCreateSerializer,
    ReservationSerializer,
)
from .services import (
    cancel_reservation,
    confirm_reservation,
    create_reservation,
)


class ReservationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ReservationSerializer
    lookup_field = 'public_id'
    lookup_url_kwarg = 'reservation_id'
    http_method_names = ['get', 'post', 'head', 'options']
    authentication_classes = [JWTAuthentication, ServiceAPIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Reservation.objects.prefetch_related('items__book')
        order_id = self.request.query_params.get('order_id')
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        return queryset

    @extend_schema(
        summary=_("List reservations"),
        parameters=[
            OpenApiParameter(
                name='order_id',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter reservations by the Project A order UUID.',
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary=_("Create a stock reservation"),
        request=ReservationCreateSerializer,
        responses={
            200: ReservationSerializer,
            201: ReservationSerializer,
            409: InsufficientStockResponseSerializer,
        },
    )
    def create(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        idempotency_key = request.headers.get('Idempotency-Key', '')
        if len(idempotency_key) > 255:
            raise ReservationStateConflict(
                'Idempotency-Key cannot exceed 255 characters.'
            )

        result = create_reservation(
            order_id=serializer.validated_data['order_id'],
            requested_items=serializer.validated_data['items'],
            idempotency_key=idempotency_key,
        )
        output = ReservationSerializer(
            result.reservation,
            context=self.get_serializer_context(),
        )
        response_status = (
            status.HTTP_201_CREATED
            if result.created
            else status.HTTP_200_OK
        )
        return Response(output.data, status=response_status)

    @extend_schema(
        summary=_("Confirm a paid reservation"),
        request=None,
        responses={200: ReservationSerializer},
    )
    @action(detail=True, methods=['post'])
    def confirm(self, request, reservation_id=None):
        get_object_or_404(self.get_queryset(), public_id=reservation_id)
        reservation = confirm_reservation(reservation_id)
        if reservation.status == Reservation.Status.EXPIRED:
            raise ReservationStateConflict(
                'Reservation expired before it could be confirmed.'
            )
        return Response(ReservationSerializer(reservation).data)

    @extend_schema(
        summary=_("Cancel a reservation"),
        request=ReservationCancelSerializer,
        responses={200: ReservationSerializer},
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, reservation_id=None):
        get_object_or_404(self.get_queryset(), public_id=reservation_id)
        serializer = ReservationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = cancel_reservation(
            reservation_id,
            serializer.validated_data['reason'],
        )
        return Response(ReservationSerializer(reservation).data)
