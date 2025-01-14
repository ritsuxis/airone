import re

from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

import custom_view
from airone.lib.acl import ACLType
from airone.lib.drf import YAMLParser
from airone.lib.types import AttrTypeValue
from entity.models import Entity, EntityAttr
from entry.api_v2.pagination import EntryReferralPagination
from entry.api_v2.serializers import (
    EntryBaseSerializer,
    EntryCopySerializer,
    EntryExportSerializer,
    EntryImportSerializer,
    EntryRetrieveSerializer,
    EntryUpdateSerializer,
    GetEntryAttrReferralSerializer,
    GetEntrySimpleSerializer,
)
from entry.models import Attribute, AttributeValue, Entry
from entry.settings import CONFIG
from entry.settings import CONFIG as ENTRY_CONFIG
from group.models import Group
from job.models import Job
from role.models import Role
from user.models import User


class EntryPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        user: User = request.user
        permisson = {
            "retrieve": ACLType.Readable,
            "update": ACLType.Writable,
            "destroy": ACLType.Full,
            "restore": ACLType.Full,
            "copy": ACLType.Full,
        }

        if not user.has_permission(obj, permisson.get(view.action)):
            return False

        return True


class EntryAPI(viewsets.ModelViewSet):
    queryset = Entry.objects.all()
    permission_classes = [IsAuthenticated & EntryPermission]

    def get_serializer_class(self):
        serializer = {
            "retrieve": EntryRetrieveSerializer,
            "update": EntryUpdateSerializer,
            "copy": EntryCopySerializer,
        }
        return serializer.get(self.action, EntryBaseSerializer)

    def destroy(self, request, pk):
        entry: Entry = self.get_object()
        if not entry.is_active:
            raise ValidationError("specified entry has already been deleted")

        user: User = request.user

        if custom_view.is_custom("before_delete_entry_v2", entry.schema.name):
            custom_view.call_custom("before_delete_entry_v2", entry.schema.name, user, entry)

        # register operation History for deleting entry
        user.seth_entry_del(entry)

        # delete entry
        entry.delete(deleted_user=user)

        if custom_view.is_custom("after_delete_entry_v2", entry.schema.name):
            custom_view.call_custom("after_delete_entry_v2", entry.schema.name, user, entry)

        # Send notification to the webhook URL
        job_notify: Job = Job.new_notify_delete_entry(user, entry)
        job_notify.run()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def restore(self, request, pk):
        entry: Entry = self.get_object()

        if entry.is_active:
            raise ValidationError("specified entry has not deleted")

        # checks that a same name entry corresponding to the entity is existed, or not.
        if Entry.objects.filter(
            schema=entry.schema, name=re.sub(r"_deleted_[0-9_]*$", "", entry.name), is_active=True
        ).exists():
            raise ValidationError("specified entry has already exist other")

        user: User = request.user

        if custom_view.is_custom("before_restore_entry_v2", entry.schema.name):
            custom_view.call_custom("before_restore_entry_v2", entry.schema.name, user, entry)

        entry.set_status(Entry.STATUS_CREATING)

        # restore entry
        entry.restore()

        if custom_view.is_custom("after_restore_entry_v2", entry.schema.name):
            custom_view.call_custom("after_restore_entry_v2", entry.schema.name, user, entry)

        # remove status flag which is set before calling this
        entry.del_status(Entry.STATUS_CREATING)

        # Send notification to the webhook URL
        job_notify_event = Job.new_notify_create_entry(user, entry)
        job_notify_event.run()

        return Response(status=status.HTTP_201_CREATED)

    def copy(self, request, pk):
        src_entry: Entry = self.get_object()

        if not src_entry.is_active:
            raise ValidationError("specified entry is not active")

        # validate post parameter
        serializer = self.get_serializer(src_entry, data=request.data)
        serializer.is_valid(raise_exception=True)

        # TODO Conversion to support the old UI
        params = {
            "new_name_list": request.data["copy_entry_names"],
            "post_data": request.data,
        }

        # run copy job
        job = Job.new_copy(request.user, src_entry, text="Preparing to copy entry", params=params)
        job.run()

        return Response({}, status=status.HTTP_200_OK)


@extend_schema(
    parameters=[
        OpenApiParameter("query", OpenApiTypes.STR, OpenApiParameter.QUERY),
    ],
)
class searchAPI(viewsets.ReadOnlyModelViewSet):
    serializer_class = EntryBaseSerializer

    def get_queryset(self):
        queryset = []
        query = self.request.query_params.get("query", None)

        if not query:
            return queryset

        results = Entry.search_entries_for_simple(query, limit=ENTRY_CONFIG.MAX_SEARCH_ENTRIES)
        return results["ret_values"]


class AdvancedSearchAPI(APIView):
    """
    NOTE for now it's just copied from /api/v1/entry/search, but it should be
    rewritten with DRF components.
    """

    MAX_LIST_ENTRIES = 100
    MAX_QUERY_SIZE = 64

    def post(self, request, format=None):
        hint_entities = request.data.get("entities")
        hint_entry_name = request.data.get("entry_name", "")
        hint_attrs = request.data.get("attrinfo")
        hint_has_referral = request.data.get("has_referral", False)
        hint_referral_name = request.data.get("referral_name", "")
        is_output_all = request.data.get("is_output_all", True)
        entry_limit = request.data.get("entry_limit", self.MAX_LIST_ENTRIES)

        hint_referral = False
        if hint_has_referral:
            hint_referral = hint_referral_name

        if (
            not isinstance(hint_entities, list)
            or not isinstance(hint_entry_name, str)
            or not isinstance(hint_attrs, list)
            or not isinstance(is_output_all, bool)
            or not isinstance(hint_referral, (str, bool))
            or not isinstance(entry_limit, int)
        ):
            return Response(
                "The type of parameter is incorrect", status=status.HTTP_400_BAD_REQUEST
            )

        # forbid to input large size request
        if len(hint_entry_name) > self.MAX_QUERY_SIZE:
            return Response("Sending parameter is too large", status=400)

        # check attribute params
        for hint_attr in hint_attrs:
            if "name" not in hint_attr:
                return Response("The name key is required for attrinfo parameter", status=400)
            if not isinstance(hint_attr["name"], str):
                return Response("Invalid value for attrinfo parameter", status=400)
            if hint_attr.get("keyword"):
                if not isinstance(hint_attr["keyword"], str):
                    return Response("Invalid value for attrinfo parameter", status=400)
                # forbid to input large size request
                if len(hint_attr["keyword"]) > self.MAX_QUERY_SIZE:
                    return Response("Sending parameter is too large", status=400)

        # check entities params
        if not hint_entities:
            return Response("The entities parameters are required", status=400)
        hint_entity_ids = []
        for hint_entity in hint_entities:
            entity = None
            if isinstance(hint_entity, int):
                entity = Entity.objects.filter(id=hint_entity, is_active=True).first()
            elif isinstance(hint_entity, str):
                if hint_entity.isnumeric():
                    entity = Entity.objects.filter(
                        Q(id=hint_entity) | Q(name=hint_entity), Q(is_active=True)
                    ).first()
                else:
                    entity = Entity.objects.filter(name=hint_entity, is_active=True).first()

            if entity and request.user.has_permission(entity, ACLType.Readable):
                hint_entity_ids.append(entity.id)

        resp = Entry.search_entries(
            request.user,
            hint_entity_ids,
            hint_attrs,
            entry_limit,
            hint_entry_name,
            hint_referral,
            is_output_all,
        )

        # convert field values to fit entry retrieve API data type, as a workaround.
        # FIXME should be replaced with DRF serializer etc
        for entry in resp["ret_values"]:
            for name, attr in entry["attrs"].items():

                def _get_typed_value(type: int) -> str:
                    if type & AttrTypeValue["array"]:
                        if type & AttrTypeValue["string"]:
                            return "asArrayString"
                        elif type & AttrTypeValue["named"]:
                            return "asArrayNamedObject"
                        elif type & AttrTypeValue["object"]:
                            return "asArrayObject"
                        elif type & AttrTypeValue["group"]:
                            return "asArrayGroup"
                        elif type & AttrTypeValue["role"]:
                            return "asArrayRole"
                    elif type & AttrTypeValue["string"] or type & AttrTypeValue["text"]:
                        return "asString"
                    elif type & AttrTypeValue["named"]:
                        return "asNamedObject"
                    elif type & AttrTypeValue["object"]:
                        return "asObject"
                    elif type & AttrTypeValue["boolean"]:
                        return "asBoolean"
                    elif type & AttrTypeValue["date"]:
                        return "asString"
                    elif type & AttrTypeValue["group"]:
                        return "asGroup"
                    elif type & AttrTypeValue["role"]:
                        return "asRole"
                    raise ValidationError(f"unexpected type: {type}")

                entry["attrs"][name] = {
                    "is_readble": attr["is_readble"],
                    "type": attr["type"],
                    "value": {
                        _get_typed_value(attr["type"]): attr.get("value", ""),
                    },
                }

        return Response({"result": resp})


@extend_schema(
    parameters=[
        OpenApiParameter("keyword", OpenApiTypes.STR, OpenApiParameter.QUERY),
    ],
)
class EntryReferralAPI(viewsets.ReadOnlyModelViewSet):
    serializer_class = GetEntrySimpleSerializer
    pagination_class = EntryReferralPagination

    def get_queryset(self):
        entry_id = self.kwargs["pk"]
        keyword = self.request.query_params.get("keyword", None)

        entry = Entry.objects.filter(pk=entry_id).first()
        if not entry:
            return []

        ids = AttributeValue.objects.filter(
            Q(referral=entry, is_latest=True) | Q(referral=entry, parent_attrv__is_latest=True)
        ).values_list("parent_attr__parent_entry", flat=True)

        # if entity_name param exists, add schema name to reduce filter execution time
        query = Q(pk__in=ids, is_active=True)
        if keyword:
            query &= Q(name__iregex=r"%s" % keyword)

        return Entry.objects.filter(query)


class EntryExportAPI(generics.GenericAPIView):
    serializer_class = EntryExportSerializer

    def post(self, request, entity_id: int):
        if not Entity.objects.filter(id=entity_id).exists():
            return Response(
                "Failed to get entity of specified id", status=status.HTTP_400_BAD_REQUEST
            )

        serializer = EntryExportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                "Parameters in post body is invalid", status=status.HTTP_400_BAD_REQUEST
            )

        job_params = {
            "export_format": serializer.validated_data["format"],
            "target_id": entity_id,
        }

        # check whether same job is sent
        job_status_not_finished = [Job.STATUS["PREPARING"], Job.STATUS["PROCESSING"]]
        if (
            Job.get_job_with_params(request.user, job_params)
            .filter(status__in=job_status_not_finished)
            .exists()
        ):
            return Response(
                "Same export processing is under execution", status=status.HTTP_400_BAD_REQUEST
            )

        entity = Entity.objects.get(id=entity_id)
        if not request.user.has_permission(entity, ACLType.Readable):
            return Response(
                'Permission denied to _value "%s"' % entity.name, status=status.HTTP_400_BAD_REQUEST
            )

        # create a job to export search result and run it
        job = Job.new_export(
            request.user,
            **{
                "text": "entry_%s.%s" % (entity.name, job_params["export_format"]),
                "target": entity,
                "params": job_params,
            },
        )
        job.run()

        return Response(
            {"result": "Succeed in registering export processing. " + "Please check Job list."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    parameters=[
        OpenApiParameter("keyword", OpenApiTypes.STR, OpenApiParameter.QUERY),
    ],
)
class EntryAttrReferralsAPI(viewsets.ReadOnlyModelViewSet):
    serializer_class = GetEntryAttrReferralSerializer

    def get_queryset(self):
        attr_id = self.kwargs["attr_id"]
        keyword = self.request.query_params.get("keyword", None)

        attr = Attribute.objects.filter(id=attr_id).first()
        if attr:
            entity_attr = attr.schema
        else:
            entity_attr = EntityAttr.objects.filter(id=attr_id).first()
        if not entity_attr:
            raise NotFound(f"not found matched attribute or entity attr: {attr_id}")

        conditions = {"is_active": True}
        if keyword:
            conditions["name__icontains"] = keyword

        # TODO support natural sort?
        if entity_attr.type & AttrTypeValue["object"]:
            return Entry.objects.filter(
                **conditions, schema__in=entity_attr.referral.all()
            ).order_by("name")[0 : CONFIG.MAX_LIST_REFERRALS]
        elif entity_attr.type & AttrTypeValue["group"]:
            return Group.objects.filter(**conditions).order_by("name")[
                0 : CONFIG.MAX_LIST_REFERRALS
            ]
        elif entity_attr.type & AttrTypeValue["role"]:
            return Role.objects.filter(**conditions).order_by("name")[0 : CONFIG.MAX_LIST_REFERRALS]
        else:
            raise ValidationError(f"unsupported attr type: {entity_attr.type}")


class EntryImportAPI(generics.GenericAPIView):
    parser_classes = [YAMLParser]

    def post(self, request):
        import_datas = request.data
        user: User = request.user
        serializer = EntryImportSerializer(data=import_datas)
        serializer.is_valid(raise_exception=True)

        job_ids = []
        error_list = []
        for import_data in import_datas:
            entity = Entity.objects.filter(name=import_data["entity"], is_active=True).first()
            if not entity:
                error_list.append("%s: Entity does not exists." % import_data["entity"])
                continue

            if not user.has_permission(entity, ACLType.Writable):
                error_list.append("%s: Entity is permission denied." % import_data["entity"])
                continue

            job = Job.new_import_v2(
                user, entity, text="Preparing to import data", params=import_data
            )
            job.run()
            job_ids.append(job.id)

        return Response(
            {"result": {"job_ids": job_ids, "error": error_list}}, status=status.HTTP_200_OK
        )
