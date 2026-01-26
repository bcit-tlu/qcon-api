# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import xml.etree.cElementTree as ET

NS_D2L = "http://desire2learn.com/xsd/d2lcp_v2p0"
NS_IMS = "http://www.imsglobal.org/xsd/imscp_v1p1"


class ManifestEntity(object):
    resources = []

    def __init__(self):
        del self.resources[:]
        
    def add_resource(self, manifest_resource_entity):
        self.resources.append(manifest_resource_entity)


class ManifestResourceEntity(object):
    def __init__(self, identifier, resource_type, material_type, href, title = '', link_target = ''):
        self.identifier = identifier
        self.resource_type = resource_type
        self.material_type = material_type
        self.href = href
        self.title = title
        self.link_target = link_target


def build_manifest_tree(manifest_entity: ManifestEntity, identifier: str = "MANIFEST_1") -> ET.ElementTree:
    """
    Build an imsmanifest.xml tree using shared namespaces/constants.
    """
    root = ET.Element(
        "manifest",
        {"xmlns:d2l_2p0": NS_D2L, "xmlns": NS_IMS, "identifier": identifier},
    )
    resources_el = ET.SubElement(root, "resources")
    for resource in manifest_entity.resources:
        ET.SubElement(
            resources_el,
            "resource",
            {
                "identifier": resource.identifier,
                "type": resource.resource_type,
                "d2l_2p0:material_type": resource.material_type,
                "href": resource.href,
                "d2l_2p0:link_target": resource.link_target,
                "title": resource.title,
            },
        )
    return ET.ElementTree(root)


def parse_manifest_tree(tree: ET.ElementTree) -> dict:
    """
    Parse an imsmanifest.xml ElementTree into a simple dict structure
    consistent with XmlReader.parse_manifest output.
    """
    root = tree.getroot()
    manifest_data = {
        "identifier": root.get("identifier", ""),
        "resources": [],
    }
    resources_el = root.find("resources")
    if resources_el is not None:
        for resource_el in resources_el.findall("resource"):
            manifest_data["resources"].append(
                {
                    "identifier": resource_el.get("identifier", ""),
                    "type": resource_el.get("type", ""),
                    "material_type": resource_el.get(f"{{{NS_D2L}}}material_type", ""),
                    "href": resource_el.get("href", ""),
                    "link_target": resource_el.get(f"{{{NS_D2L}}}link_target", ""),
                    "title": resource_el.get("title", ""),
                }
            )
    return manifest_data