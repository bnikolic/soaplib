#
# soaplib - Copyright (C) Soaplib contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

import datetime
import decimal
import re
import pytz

from lxml import etree
from pytz import FixedOffset

import soaplib
from soaplib.serializers import SimpleType
from soaplib.serializers import nillable_element
from soaplib.serializers import nillable_value
from soaplib.serializers import string_to_xml
from soaplib.util.etreeconv import etree_to_dict
from soaplib.util.etreeconv import dict_to_etree

string_encoding = 'utf-8'

_date_pattern = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
_time_pattern = r'(?P<hr>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<sec_frac>\.\d+)?'
_offset_pattern = r'(?P<tz_hr>[+-]\d{2}):(?P<tz_min>\d{2})'
_datetime_pattern = _date_pattern + '[T ]' + _time_pattern

_local_re = re.compile(_datetime_pattern)
_utc_re = re.compile(_datetime_pattern + 'Z')
_offset_re = re.compile(_datetime_pattern + _offset_pattern)

_ns_xs = soaplib.ns_xsd
_ns_xsi = soaplib.ns_xsi

class Any(SimpleType):
    __type_name__ = 'anyType'

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, parent_elt, name='retval'):
        if isinstance(value, str) or isinstance(value, unicode):
            value = etree.fromstring(value)

        e = etree.SubElement(parent_elt, '{%s}%s' % (tns,name))
        e.append(value)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        children = element.getchildren()
        retval = None

        if children:
            retval = element.getchildren()[0]

        return retval

class AnyAsDict(Any):
    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, parent_elt, name='retval'):
        e = etree.SubElement(parent_elt, '{%s}%s' % (tns,name))
        dict_to_etree(e, value)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        children = element.getchildren()
        if children:
            return etree_to_dict(element)

        return None

class String(SimpleType):
    class Attributes(SimpleType.Attributes):
        min_len = 0
        max_len = "unbounded"
        pattern = None

    def __new__(cls, *args, **kwargs):
        assert len(args) <= 1

        if len(args) == 1:
            kwargs['max_len'] = args[0]

        retval = SimpleType.__new__(cls,  ** kwargs)

        return retval

    @staticmethod
    def is_default(cls):
        return (    SimpleType.is_default(cls)
                and cls.Attributes.min_len == String.Attributes.min_len
                and cls.Attributes.max_len == String.Attributes.max_len
                and cls.Attributes.pattern == String.Attributes.pattern)

    @classmethod
    def add_to_schema(cls, schema_entries):
        if not schema_entries.has_class(cls) and not cls.is_default(cls):
            restriction = cls.get_restriction_tag(schema_entries)

            # length
            if cls.Attributes.min_len == cls.Attributes.max_len:
                length = etree.SubElement(restriction, '{%s}length' % _ns_xs)
                length.set('value', str(cls.Attributes.min_len))

            else:
                if cls.Attributes.min_len != String.Attributes.min_len:
                    min_l = etree.SubElement(restriction, '{%s}minLength' % _ns_xs)
                    min_l.set('value', str(cls.Attributes.min_len))

                if cls.Attributes.max_len != String.Attributes.max_len:
                    max_l = etree.SubElement(restriction, '{%s}maxLength' % _ns_xs)
                    max_l.set('value', str(cls.Attributes.max_len))

            # pattern
            if cls.Attributes.pattern != String.Attributes.pattern:
                pattern = etree.SubElement(restriction, '{%s}pattern' % _ns_xs)
                pattern.set('value', cls.Attributes.pattern)

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, parent_elt, name='retval'):
        if not isinstance(value, unicode):
            value = unicode(value, string_encoding)

        string_to_xml(cls, value, tns, parent_elt, name)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        u = element.text or ""
        try:
            u = str(u)
            return u.encode(string_encoding)

        except:
            return u

class AnyUri(String):
    __type_name__ = 'anyURI'

class Integer(SimpleType):
    @classmethod
    @nillable_element
    def from_xml(cls, element):
        i = element.text

        try:
            return int(i)
        except:
            return long(i)

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, parent_elt, name='retval'):
        string_to_xml(cls, str(value), tns, parent_elt, name)

class Decimal(SimpleType):
    @classmethod
    @nillable_element
    def from_xml(cls, element):
        return decimal.Decimal(element.text)

class Date(SimpleType):
    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, parent_elt, name='retval'):
        string_to_xml(cls, value.isoformat(), tns, parent_elt, name)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        """expect ISO formatted dates"""
        text = element.text

        def parse_date(date_match):
            fields = date_match.groupdict(0)
            year, month, day = [int(fields[x]) for x in
                ("year", "month", "day")]
            return datetime.date(year, month, day)

        match = _date_pattern.match(text)
        if not match:
            raise Exception("Date [%s] not in known format" % text)

        return parse_date(match)

class DateTime(SimpleType):
    __type_name__ = 'dateTime'

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, parent_elt, name='retval'):
        string_to_xml(cls, value.isoformat('T'), tns, parent_elt, name)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        """expect ISO formatted dates"""

        text = element.text
        def parse_date(date_match, tz=None):
            fields = date_match.groupdict(0)
            year, month, day, hr, min, sec = [int(fields[x]) for x in
                ("year", "month", "day", "hr", "min", "sec")]
            # use of decimal module here (rather than float) might be better
            # here, if willing to require python 2.4 or higher
            microsec = int(float(fields.get("sec_frac", 0)) * 10 ** 6)
            return datetime.datetime(year, month, day, hr, min, sec, microsec, tz)

        match = _utc_re.match(text)
        if match:
            return parse_date(match, tz=pytz.utc)

        match = _offset_re.match(text)
        if match:
            tz_hr, tz_min = [int(match.group(x)) for x in "tz_hr", "tz_min"]
            return parse_date(match, tz=FixedOffset(tz_hr * 60 + tz_min, {}))

        match = _local_re.match(text)
        if not match:
            raise Exception("DateTime [%s] not in known format" % text)

        return parse_date(match)

class Double(SimpleType):
    @classmethod
    @nillable_element
    def from_xml(cls, element):
        return float(element.text)

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, parent_elt, name='retval'):
        string_to_xml(cls, str(value), tns, parent_elt, name)

class Float(Double):
    pass

class Boolean(SimpleType):
    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, parent_elt, name='retval'):
        string_to_xml(cls, str(bool(value)).lower(), tns, parent_elt, name)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        s = element.text
        return (s and s.lower()[0] == 't')

# a class that is really a namespace
class Mandatory(object):
    String = String(min_len=1, min_occurs=1, nillable=False)
    Integer = Integer(min_occurs=1, nillable=False)
