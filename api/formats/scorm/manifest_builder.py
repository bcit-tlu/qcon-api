import xml.etree.cElementTree as ET


def build_manifest(manifest_entity):
    root = ET.Element(
        "manifest",
        {
            "xmlns:d2l_2p0": "http://desire2learn.com/xsd/d2lcp_v2p0",
            "xmlns": "http://www.imsglobal.org/xsd/imscp_v1p1",
            "identifier": "MANIFEST_1",
        },
    )
    doc = ET.SubElement(root, "resources")

    for resource in manifest_entity.resources:
        ET.SubElement(
            doc,
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
