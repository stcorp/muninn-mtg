import os
import re
from datetime import datetime

from muninn.struct import Struct
from muninn.schema import Mapping, Text


# Namespaces

class MTGNamespace(Mapping):
    # filename components
    spacecraft = Text(index=True)  # e.g. MTI1
    coverage = Text(index=True)
    facility_or_tool = Text(index=True)
    environment = Text(index=True)  # OPE|VAL|IV|DEV|REP
    disposition_mode = Text(index=True)  # T|t|C|c|O|o|V|v
    processing_mode = Text(index=True)  # N|F|R|V|B


def namespaces():
    return ['mtg']


def namespace(name):
    return MTGNamespace


# Product types

MUNINN_PRODUCT_TYPES = [
    'UVN-1B-EARTH-NIR',
    'UVN-1B-EARTH-UVVIS',
    'UVN-1B-IRR',
    'UVN-2-ALH',
    'UVN-2-AUI',
    'UVN-2-CLD',
    'UVN-2-FCS-CMA',
    'UVN-2-FCS-HET',
    'UVN-2-FCS-OCA',
    'UVN-2-FDY',
    'UVN-2-GLY',
    'UVN-2-NO2',
    'UVN-2-O3',
    'UVN-2-O3-TSC',
    'UVN-2-RI-ECA',
    'UVN-2-SO2',
]


class MTGProduct(object):

    def __init__(self, product_type, path_prefix=None):
        self.product_type = product_type
        self.path_prefix = path_prefix
        locationindicator = "-".join([r"(?P<country>.{2})", r"(?P<organisation>[a-zA-Z]+)", r"(?P<location>[a-zA-Z]+)"])
        locationindicator += "-*"  # allow for trailing '-'
        components = product_type.split("-")
        if len(components) == 3:
            components.append("")
        if components[0] in ["UVN", "IRS"]:
            datadesignator = r"SND\+SAT"
        elif components[0] in ["FCI", "LI"]:
            datadesignator = r"IMG\+SAT"
        else:
            datadesignator = r"(IMG|SND)\+SAT"
        freedescription = "-".join([
            r"(?P<spacecraftid>MT(I|S)[\d])\+(?P<data_source>%s)" % components[0],
            r"(?P<processing_level>%s)" % components[1],
            r"(?P<type>%s)" % components[2],
            r"(?P<subtype>%s)" % components[3],
            r"(?P<coverage>.{2})",
            r"(?P<subsetting>[^-]*)",
            r"(?P<component1>[^-]*)",
            r"(?P<component2>[^-]*)",
            r"(?P<component3>[^-]*)",
            r"(?P<purpose>[^-]*)",
            r"(?P<format>NC(3|4)E?)",
        ])
        productidentifier = ",".join([locationindicator, datadesignator, freedescription])
        freeformat = "_".join([
            r"(?P<facility_or_tool>[^-]+)",
            r"(?P<environment>[^-]+)",
            r"(?P<sensing_start>[\d]{14})",
            r"(?P<sensing_end>[\d]{14})",
            r"(?P<processing_mode>[NFRVB])",
            r"(?P<special_compression>[^-]*)",
            r"(?P<disposition_mode>[TCOX])",
            r"(?P<repeat_cycle_in_day>[\d]{4})",
            r"(?P<count_in_repeat_cycle>[\d]{4})",
        ])
        pattern = [
            r"^W",
            productidentifier,
            r"(?P<oflag>C)",
            r"(?P<originator>EUMT)",
            r"(?P<creation_time>[\d]{14})",
            freeformat,
        ]
        self.filename_pattern = "_".join(pattern) + r"\.nc$"

    @property
    def namespaces(self):
        return ["mtg"]

    @property
    def use_enclosing_directory(self):
        return False

    def parse_filename(self, filename):
        match = re.match(self.filename_pattern, os.path.basename(filename))
        if match:
            return match.groupdict()
        return None

    def identify(self, paths):
        if len(paths) != 1:
            return False
        return re.match(self.filename_pattern, os.path.basename(paths[0])) is not None

    def archive_path(self, properties):
        validity_start = properties.core.validity_start
        path = os.path.join(
            self.product_type,
            validity_start.strftime("%Y"),
            validity_start.strftime("%m"),
            validity_start.strftime("%d")
        )
        if self.path_prefix is not None:
            return os.path.join(self.path_prefix, path)
        return path

    def analyze(self, paths, filename_only=False):
        inpath = paths[0]
        name_attrs = self.parse_filename(inpath)

        properties = Struct()

        core = properties.core = Struct()
        core.product_name = os.path.splitext(os.path.basename(inpath))[0]
        core.creation_date = datetime.strptime(name_attrs['creation_time'], "%Y%m%d%H%M%S")
        core.validity_start = datetime.strptime(name_attrs['sensing_start'], "%Y%m%d%H%M%S")
        core.validity_stop = datetime.strptime(name_attrs['sensing_end'], "%Y%m%d%H%M%S")

        mtg = properties.mtg = Struct()
        mtg.spacecraft = name_attrs['spacecraftid']
        mtg.facility_or_tool = name_attrs['facility_or_tool']
        mtg.coverage = name_attrs['coverage']
        mtg.environment = name_attrs['environment']
        mtg.disposition_mode = name_attrs['disposition_mode']
        mtg.processing_mode = name_attrs['processing_mode']

        return properties


def product_types():
    return MUNINN_PRODUCT_TYPES


def product_type_plugin(product_type, config):
    path_prefix = None
    if config is not None:
        path_prefix = config.get('path_prefix')
    return MTGProduct(product_type, path_prefix)
