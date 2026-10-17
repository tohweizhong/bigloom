"""Workbook targets: WorldLoom `render/xlsx.py`, then a picture sheet added at ZIP level.

openpyxl drops native charts when it saves a workbook it loaded, so BigLoom edits the
package parts directly.
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from typing import ClassVar
from xml.sax.saxutils import escape

from ..evidence import pad_ooxml
from .base import Format, FormatHandler, Target

_SHEET_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>{caption}</t></is></c></row></sheetData>'
    '<drawing r:id="rId1"/></worksheet>'
)
_DRAWING_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<xdr:oneCellAnchor><xdr:from><xdr:col>0</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>2</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>'
    '<xdr:ext cx="7315200" cy="4572000"/><xdr:pic><xdr:nvPicPr><xdr:cNvPr id="2" name="Chart"/><xdr:cNvPicPr/></xdr:nvPicPr>'
    '<xdr:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill>'
    '<xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="7315200" cy="4572000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr>'
    '</xdr:pic><xdr:clientData/></xdr:oneCellAnchor></xdr:wsDr>'
)
_REL = '<Relationship Id="{rid}" Type="{type}" Target="{target}"/>'
_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{body}</Relationships>'
)
_T_SHEET = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
_T_DRAWING = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing"
_T_IMAGE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"


def xlsx_add_picture_sheet(data: bytes, png: bytes, sheet_name: str, caption: str) -> bytes:
    """Add a worksheet that shows a picture, by editing the package parts.

    openpyxl drops native charts when it saves a workbook it loaded, so this edits the ZIP
    parts directly and leaves every WorldLoom part as it was.
    """
    src = zipfile.ZipFile(BytesIO(data))
    names = src.namelist()
    sheet_nums = [int(m.group(1)) for n in names if (m := re.match(r"xl/worksheets/sheet(\d+)\.xml$", n))]
    sheet_n = max(sheet_nums, default=0) + 1
    drawing_nums = [int(m.group(1)) for n in names if (m := re.match(r"xl/drawings/drawing(\d+)\.xml$", n))]
    drawing_n = max(drawing_nums, default=0) + 1
    image_n = sum(1 for n in names if n.startswith("xl/media/")) + 1
    workbook = src.read("xl/workbook.xml").decode("utf-8")
    wb_rels = src.read("xl/_rels/workbook.xml.rels").decode("utf-8")
    types = src.read("[Content_Types].xml").decode("utf-8")
    rid_nums = [int(x) for x in re.findall(r'Id="rId(\d+)"', wb_rels)]
    rid = f"rId{max(rid_nums, default=0) + 1}"
    sheet_ids = [int(x) for x in re.findall(r'sheetId="(\d+)"', workbook)]
    safe_name = escape(sheet_name[:31]).replace('"', "&quot;")
    root_tag = re.search(r"<workbook\b[^>]*>", workbook)
    if root_tag and "xmlns:r=" not in root_tag.group(0):
        # Declare the relationships prefix on the root element when the writer left it out.
        workbook = re.sub(
            r"<workbook\b",
            '<workbook xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"',
            workbook,
            count=1,
        )
    workbook = workbook.replace(
        "</sheets>", f'<sheet name="{safe_name}" sheetId="{max(sheet_ids, default=0) + 1}" r:id="{rid}"/></sheets>'
    )
    wb_rels = wb_rels.replace(
        "</Relationships>", _REL.format(rid=rid, type=_T_SHEET, target=f"worksheets/sheet{sheet_n}.xml") + "</Relationships>"
    )
    overrides = (
        f'<Override PartName="/xl/worksheets/sheet{sheet_n}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        f'<Override PartName="/xl/drawings/drawing{drawing_n}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
    )
    if 'Extension="png"' not in types:
        overrides += '<Default Extension="png" ContentType="image/png"/>'
    types = types.replace("</Types>", overrides + "</Types>")
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == "xl/workbook.xml":
                dst.writestr(info, workbook)
            elif info.filename == "xl/_rels/workbook.xml.rels":
                dst.writestr(info, wb_rels)
            elif info.filename == "[Content_Types].xml":
                dst.writestr(info, types)
            else:
                dst.writestr(info, src.read(info.filename))
        dst.writestr(f"xl/worksheets/sheet{sheet_n}.xml", _SHEET_XML.format(caption=escape(caption)))
        dst.writestr(
            f"xl/worksheets/_rels/sheet{sheet_n}.xml.rels",
            _RELS.format(body=_REL.format(rid="rId1", type=_T_DRAWING, target=f"../drawings/drawing{drawing_n}.xml")),
        )
        dst.writestr(f"xl/drawings/drawing{drawing_n}.xml", _DRAWING_XML)
        dst.writestr(
            f"xl/drawings/_rels/drawing{drawing_n}.xml.rels",
            _RELS.format(body=_REL.format(rid="rId1", type=_T_IMAGE, target=f"../media/image{image_n}.png")),
        )
        dst.writestr(f"xl/media/image{image_n}.png", png)
    return out.getvalue()


class XlsxHandler(FormatHandler):
    fmt: ClassVar[Format] = "xlsx"

    def add_picture(self, t: Target, payload: bytes, seed: int) -> bytes:
        return xlsx_add_picture_sheet(payload, t.chart(seed), "Chart", t.caption)

    def pad(self, payload: bytes, size_bytes: int, seed: int) -> bytes:
        return pad_ooxml(payload, size_bytes, seed)
