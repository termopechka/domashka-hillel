from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User
from .permissions import IsSuperUser
from .serializer import UserSerializer


class UserViewSet(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        match self.action:
            case "retrieve" | "update" | "partial_update" | "destroy":
                return [IsSuperUser()]
            case "create":
                return [permissions.AllowAny()]
            case _:
                return [permissions.IsAuthenticated()]

    @action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
