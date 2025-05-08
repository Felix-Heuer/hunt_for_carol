import xml.etree.ElementTree as ET
import uuid
import json

IN = "conversation_tree.json"

with open(IN) as fp:
    conversation = json.load(fp)


def export_to_drawio(conversation, filename="conversation_tree.drawio"):
    filename = IN.split(".")[0] + ".drawio"
    mxfile = ET.Element("mxfile", host="app.diagrams.net")
    diagram = ET.SubElement(mxfile, "diagram", name="Conversation")
    graph = ET.Element("mxGraphModel")
    root = ET.SubElement(graph, "root")

    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    node_id_map = {}
    pos = {}
    for idx, (node_key, node) in enumerate(conversation.items()):
        uid = str(uuid.uuid4())
        node_id_map[node_key] = uid

        text = node["text"].replace("\n", "&#xa;")  # draw.io newline
        cell = ET.SubElement(root, "mxCell", {
            "id": uid,
            "value": text,
            "style": "rounded=1;whiteSpace=wrap;html=1;",
            "vertex": "1",
            "parent": "1"
        })
        x = 200 * (idx % 3)
        y = 150 * (idx // 3)
        pos[node_key] = (x, y)
        ET.SubElement(cell, "mxGeometry", {
            "x": str(x),
            "y": str(y),
            "width": "160",
            "height": "80",
            "as": "geometry"
        })

    # Add edges
    for source_key, node in conversation.items():
        for option in node.get("options", []):
            target_key = option.get("goto")
            if target_key in node_id_map:
                edge_id = str(uuid.uuid4())
                ET.SubElement(root, "mxCell", {
                    "id": edge_id,
                    "value": option["text"],
                    "style": "endArrow=block;",
                    "edge": "1",
                    "source": node_id_map[source_key],
                    "target": node_id_map[target_key],
                    "parent": "1"
                }).append(ET.Element("mxGeometry", {"relative": "1", "as": "geometry"}))

    diagram.append(graph)
    tree = ET.ElementTree(mxfile)
    tree.write(filename, encoding="utf-8", xml_declaration=True)

export_to_drawio(conversation)
