import re
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any, Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import Prefetch, Q

from acl.models import ACLBase
from airone.lib import auto_complement
from airone.lib.acl import ACLObjType, ACLType
from airone.lib.elasticsearch import (
    ESS,
    execute_query,
    is_date_check,
    make_query,
    make_query_for_simple,
    make_search_results,
    make_search_results_for_simple,
)
from airone.lib.types import (
    AttrDefaultValue,
    AttrTypeArrObj,
    AttrTypeArrStr,
    AttrTypeObj,
    AttrTypeStr,
    AttrTypeText,
    AttrTypeValue,
)
from entity.models import Entity, EntityAttr
from group.models import Group
from role.models import Role
from user.models import User

from .settings import CONFIG


class AttributeValue(models.Model):
    # This is a constant that indicates target object binds multiple AttributeValue objects.
    STATUS_DATA_ARRAY_PARENT = 1 << 0

    MAXIMUM_VALUE_SIZE = 1 << 16

    value = models.TextField()
    referral = models.ForeignKey(
        ACLBase,
        null=True,
        related_name="referred_attr_value",
        on_delete=models.SET_NULL,
    )
    data_array = models.ManyToManyField("AttributeValue")
    created_time = models.DateTimeField(auto_now_add=True)
    created_user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    parent_attr = models.ForeignKey("Attribute", on_delete=models.DO_NOTHING)
    status = models.IntegerField(default=0)
    boolean = models.BooleanField(default=False)
    date = models.DateField(null=True)

    # This parameter means that target AttributeValue is the latest one. This is usefull to
    # find out enabled AttributeValues by Attribute or EntityAttr object. And separating this
    # parameter from status is very meaningful to reduce query at clearing this flag (If this
    # flag is a value of status paramete, you have to send at least two query to set it down,
    # because you have to check current value by SELECT, after that you calculate new value
    # then update it).
    is_latest = models.BooleanField(default=True)

    # The reason why the 'data_type' parameter is also needed in addition to the Attribute is that
    # the value of 'type' in Attribute may be changed dynamically.
    #
    # If that value is changed after making AttributeValue, we can't know the old type of Attribute.
    # So it's necessary to save the value of AttrTypeVelue for each AttributeValue instance.
    # And this value is constract, this parameter will never be changed after creating.
    data_type = models.IntegerField(default=0)

    # This indicates the parent AttributeValue object, this parameter is usefull to identify
    # leaf AttriuteValue objects.
    parent_attrv = models.ForeignKey(
        "AttributeValue", null=True, related_name="child", on_delete=models.SET_NULL
    )

    @classmethod
    def get_default_value(kls, attr):
        """
        Returns the default value for each attribute type.
        Used when there is no attribute value.
        """
        return AttrDefaultValue[attr.schema.type]

    def set_status(self, val):
        self.status |= val
        self.save(update_fields=["status"])

    def del_status(self, val):
        self.status &= ~val
        self.save(update_fields=["status"])

    def get_status(self, val):
        return self.status & val

    def clone(self, user, **extra_params):
        cloned_value = AttributeValue.objects.get(id=self.id)

        # By removing the primary key, we can clone a django model instance
        cloned_value.pk = None

        # set extra configure
        for (k, v) in extra_params.items():
            setattr(cloned_value, k, v)

        # update basic parameters to new one
        cloned_value.created_user = user
        cloned_value.created_time = datetime.now()
        cloned_value.save()

        cloned_value.data_array.clear()

        return cloned_value

    def get_value(self, with_metainfo=False, serialize=False, is_active=True):
        """
        This returns registered value according to the type of Attribute
        """

        def _get_named_value(attrv, is_active=True):
            if attrv.referral and (attrv.referral.is_active or not is_active):
                if with_metainfo:
                    return {
                        attrv.value: {
                            "id": attrv.referral.id,
                            "name": attrv.referral.name,
                        }
                    }
                else:
                    return {attrv.value: attrv.referral.name}
            else:
                return {attrv.value: None}

        def _get_object_value(attrv, is_active=True):
            if attrv.referral and (attrv.referral.is_active or not is_active):
                if with_metainfo:
                    return {"id": attrv.referral.id, "name": attrv.referral.name}
                else:
                    return attrv.referral.name

        def _get_model_value(attrv, model):
            instance = model.objects.filter(id=attrv.value, is_active=True).first()
            if not instance:
                return None

            if with_metainfo:
                return {"id": instance.id, "name": instance.name}
            else:
                return instance.name

        value = None
        if (
            self.parent_attr.schema.type == AttrTypeValue["string"]
            or self.parent_attr.schema.type == AttrTypeValue["text"]
        ):
            value = self.value

        elif self.parent_attr.schema.type == AttrTypeValue["boolean"]:
            value = self.boolean

        elif self.parent_attr.schema.type == AttrTypeValue["date"]:
            if serialize:
                value = str(self.date)
            else:
                value = self.date

        elif self.parent_attr.schema.type == AttrTypeValue["object"]:
            value = _get_object_value(self, is_active)

        elif self.parent_attr.schema.type == AttrTypeValue["named_object"]:
            value = _get_named_value(self, is_active)

        elif self.parent_attr.schema.type == AttrTypeValue["group"] and self.value:
            value = _get_model_value(self, Group)

        elif self.parent_attr.schema.type == AttrTypeValue["role"] and self.value:
            value = _get_model_value(self, Role)

        elif self.parent_attr.schema.type & AttrTypeValue["array"]:
            if self.parent_attr.schema.type & AttrTypeValue["named"]:
                value = [_get_named_value(x, is_active) for x in self.data_array.all()]

            elif self.parent_attr.schema.type & AttrTypeValue["string"]:
                value = [x.value for x in self.data_array.all()]

            elif self.parent_attr.schema.type & AttrTypeValue["object"]:
                value = [
                    _get_object_value(x, is_active) for x in self.data_array.all() if x.referral
                ]

            elif self.parent_attr.schema.type & AttrTypeValue["group"]:
                value = [
                    x for x in [_get_model_value(y, Group) for y in self.data_array.all()] if x
                ]

            elif self.parent_attr.schema.type & AttrTypeValue["role"]:
                value = [x for x in [_get_model_value(y, Role) for y in self.data_array.all()] if x]

        if with_metainfo:
            value = {"type": self.parent_attr.schema.type, "value": value}

        return value

    def format_for_history(self):
        def _get_group_value(attrv):
            return Group.objects.filter(id=attrv.value, is_active=True).first()

        def _get_role_value(attrv):
            return Role.objects.filter(id=attrv.value, is_active=True).first()

        if self.data_type == AttrTypeValue["array_string"]:
            return [x.value for x in self.data_array.all()]
        elif self.data_type == AttrTypeValue["array_object"]:
            return [x.referral for x in self.data_array.all()]
        elif self.data_type == AttrTypeValue["object"]:
            return self.referral
        elif self.data_type == AttrTypeValue["boolean"]:
            return self.boolean
        elif self.data_type == AttrTypeValue["date"]:
            return self.date
        elif self.data_type == AttrTypeValue["named_object"]:
            return {
                "value": self.value,
                "referral": self.referral,
            }
        elif self.data_type == AttrTypeValue["array_named_object"]:
            return sorted(
                [
                    {
                        "value": x.value,
                        "referral": x.referral,
                    }
                    for x in self.data_array.all()
                ],
                key=lambda x: x["value"],
            )

        elif self.data_type == AttrTypeValue["group"] and self.value:
            return _get_group_value(self)

        elif self.data_type == AttrTypeValue["array_group"]:
            return [y for y in [_get_group_value(x) for x in self.data_array.all()] if y]

        elif self.data_type == AttrTypeValue["role"] and self.value:
            return _get_role_value(self)

        elif self.data_type == AttrTypeValue["array_role"]:
            return [y for y in [_get_role_value(x) for x in self.data_array.all()] if y]

        else:
            return self.value

    @classmethod
    def search(kls, query):
        results = []
        for obj in kls.objects.filter(value__icontains=query):
            attr = obj.parent_attr
            entry = attr.parent_entry

            results.append(
                {
                    "type": entry.__class__.__name__,
                    "object": entry,
                    "hint": "attribute '%s' has '%s'" % (attr.name, obj.value),
                }
            )

        return results

    @classmethod
    def create(kls, user, attr, **params):
        return kls.objects.create(
            created_user=user, parent_attr=attr, data_type=attr.schema.type, **params
        )

    # These are helper methods that changes input value to storable value for each
    # data type (e.g. case group type, this allows Group instance and int and str
    # value that indicate specific group instance, and it returns id of its instance)
    @classmethod
    def uniform_storable(kls, val, model):
        """
        This converts input to group id value(str) to be able to store at AttributeValue.
        And this expects input value as Group type instance, int value that indicate
        ID of specific Group instance and name(str) value of specific Group instance.
        """
        obj = None
        if isinstance(val, Group) and val.is_active:
            obj = val
        if isinstance(val, Role) and val.is_active:
            obj = val

        elif isinstance(val, str):
            if val.isdigit():
                obj = model.objects.filter(id=val, is_active=True).first()
            else:
                obj = model.objects.filter(name=val, is_active=True).first()

        elif isinstance(val, int):
            obj = model.objects.filter(id=val, is_active=True).first()

        # when value is invalid value (e.g. False, empty string) set 0
        # not to cause ValueError exception at other retrieval processing.
        return str(obj.id) if obj else ""

    @classmethod
    def validate_attr_value(
        kls, type: int, input_value: Any, is_mandatory: bool
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if to add_value is a possible value.
        Returns: (is_valid, msg)
            is_valid(bool): result of validate
            msg(str): error message(Optional)
        """

        def _is_validate_attr_str(value) -> bool:
            if not isinstance(value, str):
                raise Exception("value(%s) is not str" % value)
            if len(str(value).encode("utf-8")) > AttributeValue.MAXIMUM_VALUE_SIZE:
                raise Exception("value(%s) is exceeded the limit" % value)
            if is_mandatory and value == "":
                return False
            return True

        def _is_validate_attr_object(value) -> bool:
            try:
                if value and not Entry.objects.filter(id=value, is_active=True).exists():
                    raise Exception("value(%s) is not entry id" % value)
                if is_mandatory and not value:
                    return False
                return True
            except (ValueError, TypeError):
                raise Exception("value(%s) is not int" % value)

        def _is_validate_attr(value) -> bool:
            if type & AttrTypeValue["string"] or type & AttrTypeValue["text"]:
                return _is_validate_attr_str(value)

            if type & AttrTypeValue["object"]:
                if type & AttrTypeValue["named"]:
                    if not isinstance(value, dict):
                        raise Exception("value(%s) is not dict" % value)
                    if not ("name" in value.keys() and "id" in value.keys()):
                        raise Exception("value(%s) is not key('name', 'id')" % value)
                    if not any(
                        [
                            _is_validate_attr_str(value["name"]),
                            _is_validate_attr_object(value["id"]),
                        ]
                    ):
                        return False
                else:
                    if not _is_validate_attr_object(value):
                        return False

            if type & AttrTypeValue["group"]:
                try:
                    if value and not Group.objects.filter(id=value, is_active=True).exists():
                        raise Exception("value(%s) is not group id" % value)
                    if is_mandatory and not value:
                        return False
                except (ValueError, TypeError):
                    raise Exception("value(%s) is not int" % value)

            if type & AttrTypeValue["boolean"]:
                if not isinstance(value, bool):
                    raise Exception("value(%s) is not bool" % value)

            if type & AttrTypeValue["date"]:
                try:
                    if value:
                        datetime.strptime(value, "%Y-%m-%d").date()
                    if is_mandatory and not value:
                        return False
                except (ValueError, TypeError):
                    raise Exception("value(%s) is not format(YYYY-MM-DD)" % value)

            if type & AttrTypeValue["role"]:
                try:
                    if value and (
                        (
                            isinstance(value, int)
                            and not Role.objects.filter(id=value, is_active=True).exists()
                        )
                        or (
                            isinstance(value, str)
                            and not Role.objects.filter(name=value, is_active=True).exists()
                        )
                    ):
                        raise Exception("value(%s) is not Role id" % value)

                    if is_mandatory and not value:
                        return False
                except (ValueError, TypeError):
                    raise Exception("value(%s) is not int" % value)

            return True

        try:
            if type & AttrTypeValue["array"]:
                if not isinstance(input_value, list):
                    raise Exception("value(%s) is not list" % input_value)
                if is_mandatory and input_value == []:
                    raise Exception("mandatory attrs value is not specified")
                _is_mandatory = False
                for val in input_value:
                    if _is_validate_attr(val):
                        _is_mandatory = True
                if is_mandatory and not _is_mandatory:
                    raise Exception("mandatory attrs value is not specified")
            else:
                if not _is_validate_attr(input_value):
                    raise Exception("mandatory attrs value is not specified")
        except Exception as e:
            return (False, str(e))

        return (True, None)


class Attribute(ACLBase):
    values = models.ManyToManyField(AttributeValue)

    # This parameter is needed to make a relationship with corresponding EntityAttr
    schema = models.ForeignKey(EntityAttr, on_delete=models.DO_NOTHING)
    parent_entry = models.ForeignKey("Entry", on_delete=models.DO_NOTHING)

    def __init__(self, *args, **kwargs):
        super(Attribute, self).__init__(*args, **kwargs)
        self.objtype = ACLObjType.EntryAttr

    # This checks whether each specified attribute needs to update
    def is_updated(self, recv_value):
        def _is_updated_for_array_value(last_value, model):
            # This is the case when input value is None, this returns True when
            # any available values are already exists.
            if not recv_value:
                return any(
                    [
                        model.objects.filter(id=x.value, is_active=True).exists()
                        for x in last_value.data_array.all()
                    ]
                )

            return sorted(
                [AttributeValue.uniform_storable(v, model) for v in recv_value if v]
            ) != sorted(
                [
                    x.value
                    for x in last_value.data_array.all()
                    if model.objects.filter(id=x.value, is_active=True).exists()
                ]
            )

        # the case new attribute-value is specified
        if not self.values.exists():
            # the result depends on the specified value
            if isinstance(recv_value, bool):
                # the case that first value is 'False' at the boolean typed parameter
                return True
            else:
                return recv_value

        last_value = self.values.last()
        if self.schema.type == AttrTypeStr or self.schema.type == AttrTypeText:
            # the case that specified value is empty or invalid
            if not recv_value:
                # Value would be changed as empty when there is valid value
                # in the latest AttributeValue
                return last_value.value
            else:
                return last_value.value != recv_value

        elif self.schema.type == AttrTypeObj:
            # formalize recv_value type
            if isinstance(recv_value, Entry):
                recv_value = recv_value.id
            elif recv_value and isinstance(recv_value, str):
                recv_value = int(recv_value)

            if not last_value.referral and not recv_value:
                return False
            elif last_value.referral and not recv_value:
                return True
            elif not last_value.referral and recv_value:
                return True
            elif last_value.referral.id != recv_value:
                return True

        elif self.schema.type == AttrTypeArrStr:
            # the case that specified value is empty or invalid
            if not recv_value:
                # Value would be changed as empty when there are any values
                # in the latest AttributeValue
                return last_value.data_array.count() > 0

            # the case of changing value
            if last_value.data_array.count() != len(recv_value):
                return True
            # the case of appending or deleting
            for value in recv_value:
                if not last_value.data_array.filter(value=value).exists():
                    return True

        elif self.schema.type == AttrTypeArrObj:
            # the case that specified value is empty or invalid
            if not recv_value:
                # Value would be changed as empty when there are any values
                # in the latest AttributeValue
                return last_value.data_array.count() > 0

            # the case of changing value
            if last_value.data_array.count() != len(recv_value):
                return True

            # the case of appending or deleting
            for value in recv_value:
                # formalize value type
                if isinstance(value, Entry):
                    value = value.id

                if not last_value.data_array.filter(referral__id=value).exists():
                    return True

        elif self.schema.type == AttrTypeValue["boolean"]:
            return last_value.boolean != bool(recv_value)

        elif self.schema.type == AttrTypeValue["group"]:
            return last_value.value != AttributeValue.uniform_storable(recv_value, Group)

        elif self.schema.type == AttrTypeValue["role"]:
            return last_value.value != AttributeValue.uniform_storable(recv_value, Role)

        elif self.schema.type == AttrTypeValue["date"]:
            if isinstance(recv_value, str):
                try:
                    return last_value.date != datetime.strptime(recv_value, "%Y-%m-%d").date()
                except ValueError:
                    return last_value.date is not None

            return last_value.date != recv_value

        elif self.schema.type == AttrTypeValue["named_object"]:
            # the case that specified value is empty or invalid
            if not recv_value:
                # Value would be changed as empty when there is valid value
                # in the latest AttributeValue
                return last_value.value or (last_value.referral and last_value.referral.is_active)

            if last_value.value != recv_value["name"]:
                return True

            # formalize recv_value['id'] type
            if isinstance(recv_value["id"], Entry):
                recv_value["id"] = recv_value["id"].id

            if not last_value.referral and recv_value["id"]:
                return True

            if (
                last_value.referral
                and recv_value["id"]
                and last_value.referral.id != int(recv_value["id"])
            ):
                return True

        elif self.schema.type == AttrTypeValue["array_named_object"]:

            def get_entry_id(value):
                if not value:
                    return None
                if isinstance(value, Entry):
                    return value.id
                elif isinstance(value, str):
                    return int(value)
                else:
                    return value

            # the case that specified value is empty or invalid
            if not recv_value:
                # Value would be changed as empty
                # when there are any values in the latest AttributeValue
                return last_value.data_array.count() > 0

            cmp_curr = last_value.data_array.values("value", "referral_id", "boolean")

            cmp_recv = [
                {
                    "value": info.get("name", ""),
                    "referral_id": get_entry_id(info.get("id")),
                    "boolean": info.get("boolean", False),
                }
                for info in recv_value
            ]

            if sorted(cmp_curr, key=lambda x: x["value"]) != sorted(
                cmp_recv, key=lambda x: x["value"]
            ):
                return True

        elif self.schema.type == AttrTypeValue["array_group"]:
            is_updated = _is_updated_for_array_value(last_value, Group)
            if is_updated is not None:
                return is_updated

        elif self.schema.type == AttrTypeValue["array_role"]:
            is_updated = _is_updated_for_array_value(last_value, Role)
            if is_updated is not None:
                return is_updated

        return False

    # These are helper funcitons to get differental AttributeValue(s) by an update request.
    def _validate_attr_values_of_array(self):
        if not int(self.schema.type) & AttrTypeValue["array"]:
            return False
        return True

    def get_values(self, where_extra=[]):
        where_cond = [] + where_extra

        if self.schema.type & AttrTypeValue["array"]:
            where_cond.append("status & %d > 0" % AttributeValue.STATUS_DATA_ARRAY_PARENT)
        else:
            where_cond.append("status & %d = 0" % AttributeValue.STATUS_DATA_ARRAY_PARENT)

        return self.values.extra(where=where_cond).order_by("created_time")

    def get_latest_values(self):
        params = {
            "where_extra": ["is_latest > 0"],
        }
        return self.get_values(**params)

    def get_latest_value(self, is_readonly=False):
        def _create_new_value():
            params = {
                "value": "",
                "created_user": self.created_user,
                "parent_attr": self,
                "data_type": self.schema.type,
                "status": 0,
            }
            if self.schema.type & AttrTypeValue["array"]:
                params["status"] |= AttributeValue.STATUS_DATA_ARRAY_PARENT

            attrv = AttributeValue.objects.create(**params)
            self.values.add(attrv)

            return attrv

        attrv = self.values.filter(is_latest=True).last()
        if attrv:
            # When a type of attribute value is clear, a new Attribute value will be created
            if attrv.data_type != self.schema.type:
                if is_readonly:
                    return None
                else:
                    return _create_new_value()
            else:
                return attrv

        elif self.values.count() > 0:
            # During the processing of updating attribute-value, a short period of time
            # that the latest attribute value is vanished might happen. This condition
            # prevents creating new blank AttributeValue when user get latest-value of
            # this Attribute at that time.
            attrv = self.values.last()

            # When a type of attribute value is clear, a new Attribute value will be created
            if attrv.data_type != self.schema.type:
                if is_readonly:
                    return None
                else:
                    return _create_new_value()
            else:
                return attrv

        else:
            if is_readonly:
                return None
            else:
                return _create_new_value()

    def get_last_value(self):
        attrv = self.values.last()
        if not attrv:
            attrv = AttributeValue.objects.create(
                **{
                    "value": "",
                    "created_user": self.created_user,
                    "parent_attr": self,
                    "status": 1 if self.schema.type & AttrTypeValue["group"] else 0,
                    "data_type": self.schema.type,
                }
            )
            self.values.add(attrv)

        return attrv

    # NOTE: Type-Write
    def clone(self, user, **extra_params):
        if not user.has_permission(self, ACLType.Readable) or not user.has_permission(
            self.schema, ACLType.Readable
        ):
            return None

        # We can't clone an instance by the way (.pk=None and save) like AttributeValue,
        # since the subclass instance refers to the parent_link's primary key during save.
        params = {
            "name": self.name,
            "created_user": user,
            "schema": self.schema,
            "parent_entry": self.parent_entry,
        }
        params.update(extra_params)
        cloned_attr = Attribute.objects.create(**params)

        attrv = self.get_latest_value()
        if attrv:
            new_attrv = attrv.clone(user, parent_attr=cloned_attr)

            # When the Attribute is array, this method also clone co-AttributeValues
            if self.schema.type & AttrTypeValue["array"]:
                for co_attrv in attrv.data_array.all():
                    new_co_attrv = co_attrv.clone(
                        user, parent_attr=cloned_attr, parent_attrv=new_attrv
                    )
                    new_attrv.data_array.add(new_co_attrv)

            cloned_attr.values.add(new_attrv)

        return cloned_attr

    def unset_latest_flag(self, exclude_id=None):
        exclude = Q()
        if exclude_id:
            exclude = Q(id=exclude_id)
        self.values.filter(is_latest=True).exclude(exclude).update(is_latest=False)

    def _validate_value(self, value):
        def _is_group_object(val, model):
            return isinstance(val, model) or isinstance(val, int) or isinstance(val, str) or not val

        if self.schema.type & AttrTypeValue["array"]:
            if value is None:
                return True

            if self.schema.type & AttrTypeValue["named"]:
                return all(
                    [x for x in value if isinstance(x, dict) or isinstance(x, type({}.values()))]
                )

            if self.schema.type & AttrTypeValue["object"]:
                return all(
                    [
                        isinstance(x, str)
                        or isinstance(x, int)
                        or isinstance(x, Entry)
                        or x is None
                        for x in value
                    ]
                )

            if self.schema.type & AttrTypeValue["string"]:
                return True

            if self.schema.type & AttrTypeValue["group"]:
                return all([_is_group_object(x, Group) for x in value])

            if self.schema.type & AttrTypeValue["role"]:
                return all([_is_group_object(x, Role) for x in value])

        if self.schema.type & AttrTypeValue["named"]:
            return isinstance(value, dict)

        if self.schema.type & AttrTypeValue["string"] or self.schema.type & AttrTypeValue["text"]:
            return True

        if self.schema.type & AttrTypeValue["object"]:
            return (
                isinstance(value, str)
                or isinstance(value, int)
                or isinstance(value, Entry)
                or value is None
            )

        if self.schema.type & AttrTypeValue["boolean"]:
            return isinstance(value, bool)

        if self.schema.type & AttrTypeValue["date"]:
            try:
                return (
                    not value
                    or isinstance(value, date)
                    or (
                        isinstance(value, str)
                        and isinstance(datetime.strptime(value, "%Y-%m-%d"), date)
                    )
                )
            except ValueError:
                return False

        if self.schema.type & AttrTypeValue["group"]:
            return _is_group_object(value, Group)

        if self.schema.type & AttrTypeValue["role"]:
            return _is_group_object(value, Role)

        return False

    def add_value(self, user, value, boolean=False):
        """This method make AttributeValue and set it as the latest one"""

        # This is a helper method to set AttributeType
        def _set_attrv(attr_type, val, attrv=None, params={}):
            if not attrv:
                attrv = AttributeValue(**params)

            # set attribute value according to the attribute-type
            if attr_type == AttrTypeValue["string"] or attr_type == AttrTypeValue["text"]:
                attrv.boolean = boolean
                attrv.value = str(val)
                if not attrv.value:
                    return None

            if attr_type == AttrTypeValue["group"]:
                attrv.boolean = boolean
                attrv.value = AttributeValue.uniform_storable(val, Group)
                if not attrv.value:
                    return None

            if attr_type == AttrTypeValue["role"]:
                attrv.boolean = boolean
                attrv.value = AttributeValue.uniform_storable(val, Role)
                if not attrv.value:
                    return None

            elif attr_type == AttrTypeValue["object"]:
                attrv.boolean = boolean
                # set None if the referral entry is not specified
                attrv.referral = None
                if not val:
                    pass
                elif isinstance(val, Entry):
                    attrv.referral = val
                elif isinstance(val, str) or isinstance(val, int):
                    ref_entry = Entry.objects.filter(id=val, is_active=True).first()
                    if ref_entry:
                        attrv.referral = ref_entry

                if not attrv.referral:
                    return

            elif attr_type == AttrTypeValue["boolean"]:
                attrv.boolean = val

            elif attr_type == AttrTypeValue["date"]:
                if isinstance(val, str) and val:
                    attrv.date = datetime.strptime(val, "%Y-%m-%d").date()
                elif isinstance(val, date):
                    attrv.date = val

                attrv.boolean = boolean

            elif attr_type == AttrTypeValue["named_object"]:
                attrv.value = val["name"] if "name" in val else ""
                if "boolean" in val:
                    attrv.boolean = val["boolean"]
                else:
                    attrv.boolean = boolean

                attrv.referral = None
                if "id" not in val or not val["id"]:
                    pass
                elif isinstance(val["id"], str) or isinstance(val["id"], int):
                    ref_entry = Entry.objects.filter(id=val["id"], is_active=True).first()
                    if ref_entry:
                        attrv.referral = ref_entry
                elif isinstance(val["id"], Entry):
                    attrv.referral = val["id"]
                else:
                    attrv.referral = None

                if not attrv.referral and not attrv.value:
                    return

            return attrv

        # checks the type of specified value is acceptable for this Attribute object
        if not self._validate_value(value):
            raise TypeError(
                '[%s] "%s" is not acceptable [attr_type:%d]'
                % (self.schema.name, str(value), self.schema.type)
            )

        # Initialize AttrValue as None, because this may not created
        # according to the specified parameters.
        attr_value = AttributeValue.create(user, self)
        if self.schema.type & AttrTypeValue["array"]:
            attr_value.boolean = boolean

            # set status of parent data_array
            attr_value.set_status(AttributeValue.STATUS_DATA_ARRAY_PARENT)

            if value and isinstance(value, Iterable):
                co_attrv_params = {
                    "created_user": user,
                    "parent_attr": self,
                    "data_type": self.schema.type,
                    "parent_attrv": attr_value,
                    "is_latest": False,
                    "boolean": boolean,
                }

                # create and append updated values
                attrv_bulk = []
                for v in value:
                    # set AttributeValue for each values
                    co_attrv = _set_attrv(
                        (self.schema.type & ~AttrTypeValue["array"]),
                        v,
                        params=co_attrv_params,
                    )
                    if co_attrv:
                        attrv_bulk.append(co_attrv)

                # Create each leaf AttributeValue in bulk.
                # This processing send only one query to the DB
                # for making all AttributeValue objects.
                AttributeValue.objects.bulk_create(attrv_bulk)

                # set created leaf AttribueValues to the data_array parameter of
                # parent AttributeValue
                attr_value.data_array.add(*AttributeValue.objects.filter(parent_attrv=attr_value))

        else:
            _set_attrv(self.schema.type, value, attrv=attr_value)

        attr_value.save()

        # append new AttributeValue
        self.values.add(attr_value)

        # Clear the flag that means target AttrValues are latet from the Values
        # that are already created.
        self.unset_latest_flag(exclude_id=attr_value.id)

        return attr_value

    def convert_value_to_register(self, value):
        """
        This absorbs difference values according to the type of Attributes
        """

        def get_entry(schema, name):
            return Entry.objects.get(is_active=True, schema=schema, name=name)

        def is_entry(schema, name):
            return Entry.objects.filter(is_active=True, schema=schema, name=name)

        def get_named_object(data):
            (key, value) = list(data.items())[0]

            ret_value = {"name": key, "id": None}
            if isinstance(value, ACLBase):
                ret_value["id"] = value

            elif isinstance(value, str):
                entryset = [
                    get_entry(r, value) for r in self.schema.referral.all() if is_entry(r, value)
                ]

                if any(entryset):
                    ret_value["id"] = entryset[0]
                else:
                    ret_value["id"] = None

            return ret_value

        if self.schema.type == AttrTypeValue["string"] or self.schema.type == AttrTypeValue["text"]:
            return value

        elif self.schema.type == AttrTypeValue["object"]:
            if isinstance(value, ACLBase):
                return value
            elif isinstance(value, str):
                entryset = [
                    get_entry(r, value) for r in self.schema.referral.all() if is_entry(r, value)
                ]

                if any(entryset):
                    return entryset[0]

        elif self.schema.type == AttrTypeValue["group"]:
            # This avoids to return 0 when invaild value is specified because
            # uniform_storable() returns 0. By this check processing,
            # this returns None whe it happens.
            val = AttributeValue.uniform_storable(value, Group)
            if val:
                return val

        elif self.schema.type == AttrTypeValue["role"]:
            val = AttributeValue.uniform_storable(value, Role)
            if val:
                return val

        elif self.schema.type == AttrTypeValue["boolean"]:
            return value

        elif self.schema.type == AttrTypeValue["date"]:
            return value

        elif self.schema.type == AttrTypeValue["named_object"]:
            if not isinstance(value, dict):
                return None

            return get_named_object(value)

        elif self.schema.type & AttrTypeValue["array"]:
            if not isinstance(value, list):
                return None

            if self.schema.type & AttrTypeValue["named"]:
                if not all([isinstance(x, dict) for x in value]):
                    return None

                return [get_named_object(x) for x in value]

            elif self.schema.type & AttrTypeValue["string"]:
                return value

            elif self.schema.type & AttrTypeValue["object"]:
                return sum(
                    [
                        [get_entry(r, v) for r in self.schema.referral.all() if is_entry(r, v)]
                        for v in value
                    ],
                    [],
                )

            elif self.schema.type & AttrTypeValue["group"]:
                return [x for x in [AttributeValue.uniform_storable(y, Group) for y in value] if x]

            elif self.schema.type & AttrTypeValue["role"]:
                return [x for x in [AttributeValue.uniform_storable(y, Role) for y in value] if x]

        return None

    # NOTE: Type-Write
    def remove_from_attrv(self, user, referral=None, value=""):
        """
        This method removes target entry from specified attribute
        """

        # This helper methods is implemented for Group or Role. The model parameter
        # should be set Group or Role.
        def _remove_specific_object(attrv, value, model):
            if not value:
                return

            return [
                x.value
                for x in attrv.data_array.all()
                if (
                    x.value != AttributeValue.uniform_storable(value, model)
                    and model.objects.filter(id=x.value, is_active=True).exists()
                )
            ]

        attrv = self.get_latest_value()
        if self.schema.type & AttrTypeValue["array"]:

            if self.schema.type & AttrTypeValue["named"]:
                if referral is None:
                    return

                updated_data = [
                    {
                        "name": x.value,
                        "id": x.referral.id if x.referral else None,
                        "boolean": x.boolean,
                    }
                    for x in attrv.data_array.filter(~Q(referral__id=referral.id))
                ]

            elif self.schema.type & AttrTypeValue["string"]:
                if not value:
                    return

                updated_data = [x.value for x in attrv.data_array.all() if x.value != value]

            elif self.schema.type & AttrTypeValue["object"]:
                if referral is None:
                    return

                updated_data = [
                    x.referral.id
                    for x in attrv.data_array.all()
                    if x.referral and x.referral.id != referral.id
                ]

            elif self.schema.type & AttrTypeValue["group"]:
                updated_data = _remove_specific_object(attrv, value, Group)
                if updated_data is None:
                    return

            elif self.schema.type & AttrTypeValue["role"]:
                updated_data = _remove_specific_object(attrv, value, Role)
                if updated_data is None:
                    return

            if self.is_updated(updated_data):
                self.add_value(user, updated_data, boolean=attrv.boolean)

    # NOTE: Type-Write
    def add_to_attrv(self, user, referral=None, value="", boolean=False):
        """
        This method adds target entry to specified attribute with referral_key
        """
        attrv = self.get_latest_value()
        if self.schema.type & AttrTypeValue["array"]:

            updated_data = None
            if self.schema.type & AttrTypeValue["named"]:
                if value or referral:
                    updated_data = [
                        {
                            "name": x.value,
                            "boolean": x.boolean,
                            "id": x.referral.id if x.referral else None,
                        }
                        for x in attrv.data_array.all()
                    ] + [{"name": str(value), "boolean": boolean, "id": referral}]

            elif self.schema.type & AttrTypeValue["string"]:
                if value:
                    updated_data = [x.value for x in attrv.data_array.all()] + [value]

            elif self.schema.type & AttrTypeValue["object"]:
                if referral:
                    updated_data = [x.referral.id for x in attrv.data_array.all()] + [referral]

            elif self.schema.type & AttrTypeValue["group"]:
                group_id = AttributeValue.uniform_storable(value, Group)
                if group_id:
                    updated_data = [x.value for x in attrv.data_array.all()] + [group_id]

            elif self.schema.type & AttrTypeValue["role"]:
                role_id = AttributeValue.uniform_storable(value, Role)
                if role_id:
                    updated_data = [x.value for x in attrv.data_array.all()] + [role_id]

            if updated_data and self.is_updated(updated_data):
                self.add_value(user, updated_data, boolean=attrv.boolean)

    # NOTE: Type-Write
    def delete(self):
        super(Attribute, self).delete()

        def _may_remove_referral(referral):
            if not referral:
                # the case this refers no entry, do nothing
                return

            entry = Entry.objects.filter(id=referral.id, is_active=True).first()
            if not entry:
                # the case referred entry is already deleted, do nothing
                return

            if entry.get_referred_objects().count() > 0:
                # the case other entries also refer target referral, do nothing
                return

            entry.delete()

        # delete referral object that isn't referred from any objects if it's necessary
        if self.schema.is_delete_in_chain and self.schema.type & AttrTypeValue["object"]:
            attrv = self.get_latest_value()

            if self.schema.type & AttrTypeValue["array"]:
                [_may_remove_referral(x.referral) for x in attrv.data_array.all()]
            else:
                _may_remove_referral(attrv.referral)

    # implementation for Attribute
    def check_duplication_entry_at_restoring(self, entry_chain):
        def _check(referral):
            if referral and not referral.is_active:
                entry = Entry.objects.filter(id=referral.id, is_active=False).first()
                if entry:
                    if entry in entry_chain:
                        # It means it's safe to restore this Entry.
                        return False
                    dup_entry = Entry.objects.filter(
                        schema=entry.schema.id,
                        name=re.sub(r"_deleted_[0-9_]*$", "", entry.name),
                        is_active=True,
                    ).first()
                    if dup_entry:
                        return True

                    entry_chain.append(entry)

                    return entry.check_duplication_entry_at_restoring(entry_chain)

            # It means it's safe to restore this Entry.
            return False

        if self.schema.is_delete_in_chain and self.schema.type & AttrTypeValue["object"]:
            attrv = self.get_latest_value()

            if self.schema.type & AttrTypeValue["array"]:
                ret = [_check(x.referral) for x in attrv.data_array.all()]
                if True in ret:
                    return True
                else:
                    return False
            else:
                return _check(attrv.referral)

    # NOTE: Type-Write
    def restore(self):
        super(Attribute, self).restore()

        def _may_restore_referral(referral):
            if not referral:
                # the case this refers no entry, do nothing
                return

            entry = Entry.objects.filter(id=referral.id, is_active=False).first()
            if not entry:
                # the case referred entry is already restored, do nothing
                return

            entry.restore()

        # restore referral object that isn't referred from any objects if it's necessary
        if self.schema.is_delete_in_chain and self.schema.type & AttrTypeValue["object"]:
            attrv = self.get_latest_value()

            if self.schema.type & AttrTypeValue["array"]:
                [_may_restore_referral(x.referral) for x in attrv.data_array.all()]
            else:
                _may_restore_referral(attrv.referral)


class Entry(ACLBase):
    # This flag is set just after created or edited, then cleared at completion of the processing
    STATUS_CREATING = 1 << 0
    STATUS_EDITING = 1 << 1
    STATUS_COMPLEMENTING_ATTRS = 1 << 2

    attrs = models.ManyToManyField(Attribute)
    schema = models.ForeignKey(Entity, on_delete=models.DO_NOTHING)

    def __init__(self, *args, **kwargs):
        super(Entry, self).__init__(*args, **kwargs)
        self.objtype = ACLObjType.Entry

    def get_cache(self, cache_key):
        return cache.get("%s_%s" % (self.id, cache_key))

    def set_cache(self, cache_key, value):
        cache.set("%s_%s" % (self.id, cache_key), value)

    def clear_cache(self, cache_key):
        cache.delete("%s_%s" % (self.id, cache_key))

    def add_attribute_from_base(self, base, request_user):
        if not isinstance(base, EntityAttr):
            raise TypeError('Variable "base" is incorrect type')

        if not isinstance(request_user, User):
            raise TypeError('Variable "user" is incorrect type')

        # While an Attribute object which corresponding to base EntityAttr has been already
        # registered, a request to create same Attribute might be here when multiple request
        # invoked and make requests simultaneously. That request may call this method after
        # previous processing is finished.
        # In this case, we have to prevent to create new Attribute object.
        attr = Attribute.objects.filter(schema=base, parent_entry=self, is_active=True).first()
        if attr:
            self.may_append_attr(attr)
            return

        # This processing may avoid to run following more one time from mutiple request
        cache_key = "add_%d" % base.id
        if self.get_cache(cache_key):
            return

        # set lock status
        self.set_cache(cache_key, 1)

        attr = Attribute.objects.create(
            name=base.name, schema=base, created_user=request_user, parent_entry=self
        )

        self.attrs.add(attr)

        # release lock status
        self.clear_cache(cache_key)

        return attr

    def get_referred_objects(self, filter_entities=[], exclude_entities=[]):
        """
        This returns objects that refer current Entry in the AttributeValue
        """
        ids = AttributeValue.objects.filter(
            Q(referral=self, is_latest=True) | Q(referral=self, parent_attrv__is_latest=True)
        ).values_list("parent_attr__parent_entry", flat=True)

        # if entity_name param exists, add schema name to reduce filter execution time
        query = Q(pk__in=ids, is_active=True)
        if filter_entities:
            query &= Q(schema__name__in=filter_entities)

        return Entry.objects.filter(query).exclude(schema__name__in=exclude_entities)

    def may_append_attr(self, attr):
        """
        This appends Attribute object to attributes' array of entry when it's entitled to be there.
        """
        if (
            attr
            and attr.is_active
            and attr.parent_entry == self
            and attr.id not in [x.id for x in self.attrs.filter(is_active=True)]
        ):
            self.attrs.add(attr)

    def may_remove_duplicate_attr(self, attr):
        """
        This removes speicified Attribute object if an Attribute object which refers same
        EntityAttr at schema parameter is registered to prevent saving duplicate one.
        """
        if self.attrs.filter(Q(schema=attr.schema, is_active=True), ~Q(id=attr.id)).exists():
            # remove attribute from Attribute list of this entry
            self.attrs.remove(attr)

            # update target attribute will be inactive
            attr.is_active = False
            attr.save(update_fields=["is_active"])

    def complement_attrs(self, user):
        """
        This method complements Attributes which are appended after creation of Entity
        """

        # Get auto complement user
        user = auto_complement.get_auto_complement_user(user)

        for attr_id in set(
            self.schema.attrs.filter(is_active=True).values_list("id", flat=True)
        ) - set(self.attrs.filter(is_active=True).values_list("schema", flat=True)):

            entity_attr = self.schema.attrs.get(id=attr_id)
            if not user.has_permission(entity_attr, ACLType.Readable):
                continue

            newattr = self.add_attribute_from_base(entity_attr, user)
            if not newattr:
                continue

            if entity_attr.type & AttrTypeValue["array"]:
                # Create a initial AttributeValue for editing processing
                attr_value = AttributeValue.objects.create(
                    **{
                        "created_user": user,
                        "parent_attr": newattr,
                        "data_type": entity_attr.type,
                    }
                )

                # Set status of parent data_array
                attr_value.set_status(AttributeValue.STATUS_DATA_ARRAY_PARENT)

                newattr.values.add(attr_value)

            # When multiple requests to add new Attribute came here, multiple Attriutes
            # might be existed. If there were, this would delete new one.
            self.may_remove_duplicate_attr(newattr)

    # NOTE: Type-Read
    def get_available_attrs(self, user, permission=ACLType.Readable):
        # To avoid unnecessary DB access for caching referral entries
        ret_attrs = []
        attrv_prefetch = Prefetch(
            "values",
            queryset=AttributeValue.objects.filter(is_latest=True)
            .select_related("referral")
            .prefetch_related("data_array__referral"),
            to_attr="attrv_list",
        )
        attr_prefetch = Prefetch(
            "attribute_set",
            queryset=Attribute.objects.filter(parent_entry=self, is_active=True).prefetch_related(
                attrv_prefetch
            ),
            to_attr="attr_list",
        )
        for entity_attr in (
            self.schema.attrs.filter(is_active=True)
            .prefetch_related(attr_prefetch)
            .order_by("index")
        ):
            attrinfo = {}
            attrinfo["id"] = ""
            attrinfo["entity_attr_id"] = entity_attr.id
            attrinfo["name"] = entity_attr.name
            attrinfo["type"] = entity_attr.type
            attrinfo["is_mandatory"] = entity_attr.is_mandatory
            attrinfo["index"] = entity_attr.index
            attrinfo["is_readble"] = True
            attrinfo["last_value"] = AttrDefaultValue[entity_attr.type]

            # check that attribute exists
            attr = entity_attr.attr_list[0] if entity_attr.attr_list else None
            if not attr:
                attrinfo["is_readble"] = user.has_permission(entity_attr, permission)
                ret_attrs.append(attrinfo)
                continue
            attrinfo["id"] = attr.id

            # check permission of attributes
            if not user.has_permission(attr, permission):
                attrinfo["is_readble"] = False
                ret_attrs.append(attrinfo)
                continue

            # set last-value of current attributes
            last_value = attr.attrv_list[-1] if attr.attrv_list else None
            if last_value is None:
                ret_attrs.append(attrinfo)
                continue

            if last_value.data_type == AttrTypeStr or last_value.data_type == AttrTypeText:
                attrinfo["last_value"] = last_value.value

            elif last_value.data_type == AttrTypeObj:
                if last_value.referral and last_value.referral.is_active:
                    attrinfo["last_value"] = last_value.referral
                else:
                    attrinfo["last_value"] = None

            elif last_value.data_type == AttrTypeArrStr:
                # this dict-key 'last_value' is uniformed with all array types
                attrinfo["last_value"] = [x.value for x in last_value.data_array.all()]

            elif last_value.data_type == AttrTypeArrObj:
                attrinfo["last_value"] = [
                    x.referral
                    for x in last_value.data_array.all()
                    if x.referral and x.referral.is_active
                ]

            elif last_value.data_type == AttrTypeValue["boolean"]:
                attrinfo["last_value"] = last_value.boolean

            elif last_value.data_type == AttrTypeValue["date"]:
                attrinfo["last_value"] = last_value.date

            elif last_value.data_type == AttrTypeValue["named_object"]:
                attrinfo["last_value"] = {"value": last_value.value}

                if last_value.referral and last_value.referral.is_active:
                    attrinfo["last_value"]["id"] = last_value.referral.id
                    attrinfo["last_value"]["name"] = last_value.referral.name

            elif last_value.data_type == AttrTypeValue["array_named_object"]:
                values = []
                for attrv in last_value.data_array.all():
                    value = {"value": attrv.value}
                    if attrv.referral and attrv.referral.is_active:
                        value["id"] = attrv.referral.id
                        value["name"] = attrv.referral.name
                    values.append(value)

                attrinfo["last_value"] = sorted(
                    values,
                    key=lambda x: x["value"],
                )

            elif last_value.data_type == AttrTypeValue["group"] and last_value.value:
                attrinfo["last_value"] = Group.objects.filter(
                    id=last_value.value, is_active=True
                ).first()

            elif last_value.data_type == AttrTypeValue["array_group"]:
                attrinfo["last_value"] = [
                    x
                    for x in [
                        Group.objects.filter(id=v.value, is_active=True).first()
                        for v in last_value.data_array.all()
                    ]
                    if x
                ]

            elif last_value.data_type == AttrTypeValue["role"] and last_value.value:
                attrinfo["last_value"] = Role.objects.filter(
                    id=last_value.value, is_active=True
                ).first()

            elif last_value.data_type == AttrTypeValue["array_role"]:
                attrinfo["last_value"] = [
                    x
                    for x in [
                        Role.objects.filter(id=v.value, is_active=True).first()
                        for v in last_value.data_array.all()
                    ]
                    if x
                ]

            ret_attrs.append(attrinfo)

        return ret_attrs

    # NOTE: Type-Read
    def to_dict(self, user, with_metainfo=False):
        # check permissions for each entry, entity and attrs
        if not user.has_permission(self.schema, ACLType.Readable) or not user.has_permission(
            self, ACLType.Readable
        ):
            return None

        attr_prefetch = Prefetch(
            "attribute_set",
            queryset=Attribute.objects.filter(
                parent_entry=self, is_active=True, schema__is_active=True
            ),
            to_attr="attr_list",
        )
        sorted_attrs = [
            x.attr_list[0]
            for x in self.schema.attrs.filter(is_active=True)
            .prefetch_related(attr_prefetch)
            .order_by("index")
            if x.attr_list
        ]

        attrs = [
            x
            for x in sorted_attrs
            if (
                user.has_permission(x.schema, ACLType.Readable)
                and user.has_permission(x, ACLType.Readable)
            )
        ]

        returning_attrs = []
        for attr in attrs:
            attrv = attr.get_latest_value(is_readonly=True)
            if attrv is None:
                returning_attrs.append(
                    {
                        "name": attr.schema.name,
                        "value": AttributeValue.get_default_value(attr),
                    }
                )

            else:
                returning_attrs.append(
                    {
                        "name": attr.schema.name,
                        "value": attrv.get_value(serialize=True, with_metainfo=with_metainfo),
                    }
                )

        return {
            "id": self.id,
            "name": self.name,
            "entity": {
                "id": self.schema.id,
                "name": self.schema.name,
            },
            "attrs": returning_attrs,
        }

    def delete(self, *args, **kwargs):
        super(Entry, self).delete(*args, **kwargs)

        # update Elasticsearch index info which refered this entry not to refer this link
        es_object = ESS()
        for entry in [x for x in self.get_referred_objects() if x.id != self.id]:
            entry.register_es(es=es_object)

        # also delete each attributes
        for attr in self.attrs.filter(is_active=True):

            # delete Attribute object
            attr.delete()

        if settings.ES_CONFIG:
            self.unregister_es()

    # implementation for Entry
    def check_duplication_entry_at_restoring(self, entry_chain=[]):
        """This method returns true when this Entry has referral that is
           same name with other entry at restoring Entry.
        - case True: there is an Entry(at least) that is same name with same Entity.
        - case False: there is no Entry that is same name with same Entity.
        """
        for attr in self.attrs.filter(is_active=False):
            ret = attr.check_duplication_entry_at_restoring(entry_chain)
            if ret:
                return True

        # It means it's safe to restore this Entry.
        return False

    def restore(self):
        super(Entry, self).restore()

        # also restore each attributes
        for attr in self.attrs.filter(is_active=False):

            # restore Attribute object
            attr.restore()

        # update Elasticsearch index info which refered this entry to refer this link
        es_object = ESS()
        for entry in [x for x in self.get_referred_objects()]:
            entry.register_es(es=es_object)

        # update entry information to Elasticsearch
        self.register_es()

    def clone(self, user, **extra_params):
        if not user.has_permission(self, ACLType.Readable) or not user.has_permission(
            self.schema, ACLType.Readable
        ):
            return None

        # set STATUS_CREATING flag until all related parameters are set
        status = Entry.STATUS_CREATING
        if "status" in extra_params:
            status |= extra_params.pop("status")

        # We can't clone an instance by the way (.pk=None and save) like AttributeValue,
        # since the subclass instance refers to the parent_link's primary key during save.
        params = {
            "name": self.name,
            "created_user": user,
            "schema": self.schema,
            "status": status,
        }
        params.update(extra_params)
        cloned_entry = Entry.objects.create(**params)

        for attr in self.attrs.filter(is_active=True):
            cloned_attr = attr.clone(user, parent_entry=cloned_entry)

            if cloned_attr:
                cloned_entry.attrs.add(cloned_attr)

        cloned_entry.del_status(Entry.STATUS_CREATING)
        return cloned_entry

    # NOTE: Type-Write
    def export(self, user):
        attrinfo = {}

        # This calling of complement_attrs is needed to take into account the case of the Attributes
        # that are added after creating this entry.
        self.complement_attrs(user)

        for attr in self.attrs.filter(is_active=True, schema__is_active=True):
            if not user.has_permission(attr, ACLType.Readable):
                continue

            latest_value = attr.get_latest_value()
            if latest_value:
                attrinfo[attr.schema.name] = latest_value.get_value()
            else:
                attrinfo[attr.schema.name] = None

        return {"name": self.name, "attrs": attrinfo}

    # NOTE: Type-Write
    def get_es_document(self, es=None):
        """This processing registers entry information to Elasticsearch"""
        # This innner method truncates value in taking multi-byte in account
        def truncate(value):
            while len(value.encode("utf-8")) > ESS.MAX_TERM_SIZE:
                value = value[:-1]
            return value

        def _set_attrinfo(entity_attr, attr, attrv, container, is_recursive=False):
            attrinfo = {
                "name": entity_attr.name,
                "type": entity_attr.type,
                "key": "",
                "value": "",
                "date_value": None,
                "referral_id": "",
                "is_readble": True
                if (not attr or attr.is_public or attr.default_permission >= ACLType.Readable.id)
                else False,
            }

            def _set_attrinfo_data(model):
                if attrv.value:
                    obj = model.objects.filter(id=attrv.value, is_active=True).first()
                    if obj:
                        attrinfo["value"] = truncate(obj.name)
                        attrinfo["referral_id"] = obj.id

            # Convert data format for mapping of Elasticsearch according to the data type
            if attrv is None:
                # This is the processing to be safe even if the empty AttributeValue was passed.
                pass

            elif (
                entity_attr.type & AttrTypeValue["string"]
                or entity_attr.type & AttrTypeValue["text"]
            ):
                # When the value was date format, Elasticsearch detect it date type
                # automatically. This processing explicitly set value to the date typed
                # parameter.
                ret = is_date_check(attrv.value)
                if ret and isinstance(ret[1], date):
                    attrinfo["date_value"] = ret[1]
                else:
                    attrinfo["value"] = truncate(attrv.value)

            elif entity_attr.type & AttrTypeValue["boolean"]:
                attrinfo["value"] = str(attrv.boolean)

            elif entity_attr.type & AttrTypeValue["date"]:
                attrinfo["date_value"] = attrv.date

            elif entity_attr.type & AttrTypeValue["named"]:
                attrinfo["key"] = attrv.value

                if attrv.referral and attrv.referral.is_active:
                    attrinfo["value"] = truncate(attrv.referral.name)
                    attrinfo["referral_id"] = attrv.referral.id

            elif entity_attr.type & AttrTypeValue["object"]:
                if attrv.referral and attrv.referral.is_active:
                    attrinfo["value"] = truncate(attrv.referral.name)
                    attrinfo["referral_id"] = attrv.referral.id

            elif entity_attr.type & AttrTypeValue["group"]:
                _set_attrinfo_data(Group)

            elif entity_attr.type & AttrTypeValue["role"]:
                _set_attrinfo_data(Role)

            # Basically register attribute information whatever value doesn't exist
            if not (entity_attr.type & AttrTypeValue["array"] and not is_recursive):
                container.append(attrinfo)

            elif (
                entity_attr.type & AttrTypeValue["array"] and not is_recursive and attrv is not None
            ):
                # Here is the case of parent array, set each child values
                [
                    _set_attrinfo(entity_attr, attr, x, container, True)
                    for x in attrv.data_array.all()
                ]

                # If there is no value in container,
                # this set blank value for maching blank search request
                if not [x for x in container if x["name"] == entity_attr.name]:
                    container.append(attrinfo)

        document = {
            "entity": {"id": self.schema.id, "name": self.schema.name},
            "name": self.name,
            "attr": [],
            "is_readble": True
            if (self.is_public or self.default_permission >= ACLType.Readable.id)
            else False,
        }

        # The reason why this is a beat around the bush processing is for the case that Attibutes
        # objects are not existed in attr parameter because of delay processing. If this entry
        # doesn't have an Attribute object associated with an EntityAttr, this registers blank
        # value to the Elasticsearch.
        for entity_attr in self.schema.attrs.filter(is_active=True):
            attrv = None

            attr = self.attrs.filter(schema=entity_attr, is_active=True).first()
            if attr:
                attrv = attr.get_latest_value()

            _set_attrinfo(entity_attr, attr, attrv, document["attr"])

        return document

    def register_es(self, es=None, skip_refresh=False):
        if not es:
            es = ESS()

        es.index(doc_type="entry", id=self.id, body=self.get_es_document(es))
        if not skip_refresh:
            es.refresh()

    def unregister_es(self, es=None):
        if not es:
            es = ESS()

        es.delete(doc_type="entry", id=self.id, ignore=[404])
        es.refresh(ignore=[404])

    def get_value_history(self, user, count=CONFIG.MAX_HISTORY_COUNT, index=0):
        def _get_values(attrv):
            return {
                "attrv_id": attrv.id,
                "value": attrv.format_for_history(),
                "created_time": attrv.created_time,
                "created_user": attrv.created_user.username,
            }

        ret_values = []
        all_attrv = AttributeValue.objects.filter(
            parent_attr__in=self.attrs.all(), parent_attrv__isnull=True
        ).order_by("-created_time")[index:]

        for (i, attrv) in enumerate(all_attrv):
            if len(ret_values) >= count:
                break

            attr = attrv.parent_attr
            if (
                attr.is_active
                and attr.schema.is_active
                and user.has_permission(attr, ACLType.Readable)
                and user.has_permission(attr.schema, ACLType.Readable)
            ):

                # try to get next attrv
                next_attrv = None
                for _attrv in all_attrv[(i + 1) :]:
                    if _attrv.parent_attr == attr:
                        next_attrv = _attrv
                        break

                ret_values.append(
                    {
                        "attr_id": attr.id,
                        "attr_name": attr.schema.name,
                        "attr_type": attr.schema.type,
                        "curr": _get_values(attrv),
                        "prev": _get_values(next_attrv) if next_attrv else None,
                    }
                )

        return ret_values

    @classmethod
    def search_entries(
        kls,
        user,
        hint_entity_ids,
        hint_attrs=None,
        limit=CONFIG.MAX_LIST_ENTRIES,
        entry_name=None,
        hint_referral=False,
        is_output_all=False,
    ):
        """Main method called from advanced search.

        Do the following:
        1. Create a query for Elasticsearch search. (make_query)
        2. Execute the created query. (execute_query)
        3. Search the reference entry, Check permissions,
           process the search results, and return. (make_search_results)

        Args:
            user (:obj:`str`, optional): User who executed the process
            hint_entity_ids (list(str)): Entity ID specified in the search condition input
            hint_attrs (list(dict[str, str])): Defaults to Empty list.
                A list of search strings and attribute sets
            limit (int): Defaults to 100.
                Maximum number of search results to return
            entry_name (str): Search string for entry name
            hint_referral (str): Defaults to False.
                Input value used to refine the reference entry.
                Use only for advanced searches.
            is_output_all (bool): Defaults to False.
                Flag to output all attribute values.

        Returns:
            dict[str, any]: As a result of the search,
                the acquired entry and the attribute value of the entry are returned.
            {
                'ret_count': (int),
                'ret_values': [
                    'entity': {'id': (int), 'name': (str)},
                    'entry': {'id': (int), 'name': (str)},
                    'attrs': {
                        'Name of Attribute': {
                            'type': (int),
                            'value': (any),
                            'is_readble': (bool),
                        }
                    }
                    'is_readble': (bool),
                ],
            }
        """
        if not hint_attrs:
            hint_attrs = []

        results = {
            "ret_count": 0,
            "ret_values": [],
        }
        for hint_entity_id in hint_entity_ids:
            # Check for has permission to Entity
            entity = Entity.objects.filter(id=hint_entity_id, is_active=True).first()
            if not (entity and user.has_permission(entity, ACLType.Readable)):
                continue

            # Check for has permission to EntityAttr
            for hint_attr in hint_attrs:
                if "name" not in hint_attr:
                    continue

                hint_entity_attr = entity.attrs.filter(
                    name=hint_attr["name"], is_active=True
                ).first()
                hint_attr["is_readble"] = (
                    True
                    if (
                        hint_entity_attr and user.has_permission(hint_entity_attr, ACLType.Readable)
                    )
                    else False
                )

            # make query for elasticsearch to retrieve data user wants
            query = make_query(entity, hint_attrs, entry_name)

            # sending request to elasticsearch with making query
            resp = execute_query(query)

            if "status" in resp and resp["status"] == 404:
                continue

            # Check for has permission to EntityAttr, when is_output_all flag
            if is_output_all:
                for entity_attr in entity.attrs.filter(is_active=True):
                    if entity_attr.name not in [x["name"] for x in hint_attrs if "name" in x]:
                        hint_attrs.append(
                            {
                                "name": entity_attr.name,
                                "is_readble": True
                                if (user.has_permission(entity_attr, ACLType.Readable))
                                else False,
                            }
                        )

            # retrieve data from database on the basis of the result of elasticsearch
            search_result = make_search_results(user, resp, hint_attrs, limit, hint_referral)
            results["ret_count"] += search_result["ret_count"]
            results["ret_values"].extend(search_result["ret_values"])
            limit -= search_result["ret_count"]

        return results

    @classmethod
    def search_entries_for_simple(
        kls,
        hint_attr_value,
        hint_entity_name=None,
        exclude_entity_names=[],
        limit=CONFIG.MAX_LIST_ENTRIES,
        offset=0,
    ):
        """Method called from simple search.
        Returns the count and values of entries with hint_attr_value.

        Do the following:
        1. Create a query for Elasticsearch search. (make_query_for_attrv)
        2. Execute the created query. (execute_query)
        3. Process the search results, and return. (make_search_results_for_attrv)

        Args:
            hint_attr_value (str): Required.
                Search string for AttributeValue
            hint_entity_name (str): Defaults to None.
                Search string for Entity Name
            exclude_entity_names (list[str]): Defaults to [].
                Entity name string list to exclude from search
            limit (int): Defaults to 100.
                Maximum number of search results to return
            offset (int): Defaults to 0.
                Number of offset

        Returns:
            dict[str, any]: As a result of the search,
                the acquired entry and the attribute value of the entry are returned.
            {
                'ret_count': (int),
                'ret_values': [
                    'id': (str),
                    'name': (str),
                    'attr': (str),
                ],
            }

        """
        # by elasticsearch limit, from + size must be less than or equal to max_result_window
        if offset + limit > settings.ES_CONFIG["MAXIMUM_RESULTS_NUM"]:
            return {
                "ret_count": 0,
                "ret_values": [],
            }

        query = make_query_for_simple(
            hint_attr_value, hint_entity_name, exclude_entity_names, offset
        )

        resp = execute_query(query, limit)

        if "status" in resp and resp["status"] == 404:
            return {
                "ret_count": 0,
                "ret_values": [],
            }

        return make_search_results_for_simple(resp)

    @classmethod
    def get_all_es_docs(kls):
        return ESS().search(body={"query": {"match_all": {}}}, ignore=[404])

    @classmethod
    def is_importable_data(kls, data):
        """This method confirms import data has following data structure
        Entity:
            - name: entry_name
            - attrs:
                attr_name1: attr_value
                attr_name2: attr_value
                ...
        """
        if not isinstance(data, dict):
            return False

        if not all([isinstance(x, list) for x in data.values()]):
            return False

        for entry_data in sum(data.values(), []):
            if not isinstance(entry_data, dict):
                return False

            if not ("attrs" in entry_data and "name" in entry_data):
                return False

            if not isinstance(entry_data["name"], str):
                return False

            if not isinstance(entry_data["attrs"], dict):
                return False

        return True

    def get_attrv(self, attr_name):
        """This returns specified attribute's value without permission check. Because
        this prioritizes performance (less frequency of sending query to Database) over
        authorization safety.

        CAUTION: Don't use this before permissoin check of specified attribute.
        """
        return AttributeValue.objects.filter(
            is_latest=True,
            parent_attr__name=attr_name,
            parent_attr__schema__is_active=True,
            parent_attr__parent_entry=self,
        ).last()
