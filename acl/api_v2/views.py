from rest_framework import mixins, viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated

from acl.api_v2.serializers import ACLSerializer
from acl.models import ACLBase
from airone.lib.acl import ACLType


class ACLFullPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, ACLBase):
            return False
        if not request.user.has_permission(obj, ACLType.Full):
            return False
        return True


class ACLAPI(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = ACLBase.objects.all()
    serializer_class = ACLSerializer

    permission_classes = [IsAuthenticated & ACLFullPermission]
