"""Minimal Markdown-to-DOCX converter for project documentation.

This avoids external dependencies such as pandoc or python-docx. It supports
the subset used by the LexiFlow architecture document: headings, paragraphs,
bullets, tables, fenced code blocks, horizontal rules, and page breaks before
major H2 sections.
"""

import html
import re
import sys
import zipfile
from pathlib import Path


NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def run(text: str, bold: bool = False, font: str = None) -> str:
    props = []
    if bold:
        props.append("<w:b/>")
    if font:
        props.append(f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>')
    prop_xml = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f"<w:r>{prop_xml}<w:t xml:space=\"preserve\">{esc(text)}</w:t></w:r>"


def paragraph(text: str = "", style: str = None, bold: bool = False, font: str = None) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}{run(text, bold=bold, font=font)}</w:p>"


def page_break() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def table(rows) -> str:
    xml = [
        "<w:tbl>",
        '<w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/>',
        '<w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>',
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>',
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>',
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>',
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>',
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/></w:tblBorders></w:tblPr>',
    ]
    for row_index, row in enumerate(rows):
        xml.append("<w:tr>")
        for cell in row:
            bold = row_index == 0
            xml.append("<w:tc><w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>")
            xml.append(paragraph(cell.strip(), bold=bold))
            xml.append("</w:tc>")
        xml.append("</w:tr>")
    xml.append("</w:tbl>")
    return "".join(xml)


def parse_table(lines, start):
    rows = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        line = lines[index].strip()
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            rows.append(cells)
        index += 1
    return rows, index


def markdown_to_body(markdown: str) -> str:
    lines = markdown.splitlines()
    body = []
    index = 0
    in_code = False
    code_buffer = []

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                if code_buffer:
                    for code_line in code_buffer:
                        body.append(paragraph(code_line, style="Code", font="Courier New"))
                code_buffer = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue

        if in_code:
            code_buffer.append(line)
            index += 1
            continue

        if not stripped:
            body.append(paragraph(""))
            index += 1
            continue

        if stripped == "---":
            body.append(paragraph(""))
            index += 1
            continue

        if stripped.startswith("|"):
            rows, index = parse_table(lines, index)
            if rows:
                body.append(table(rows))
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            if level == 1:
                body.append(paragraph(text, style="Title", bold=True))
            elif level == 2:
                body.append(page_break())
                body.append(paragraph(text, style="Heading1", bold=True))
            elif level == 3:
                body.append(paragraph(text, style="Heading2", bold=True))
            else:
                body.append(paragraph(text, style="Heading3", bold=True))
            index += 1
            continue

        if stripped.startswith("- "):
            body.append(paragraph("• " + stripped[2:], style="ListParagraph"))
            index += 1
            continue

        ordered = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ordered:
            body.append(paragraph(ordered.group(0), style="ListParagraph"))
            index += 1
            continue

        body.append(paragraph(stripped))
        index += 1

    return "".join(body)


def document_xml(body: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{NS}">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>'''


def styles_xml() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{NS}">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:rPr><w:b/><w:sz w:val="36"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:rPr><w:b/><w:sz w:val="30"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:rPr><w:b/><w:sz w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/>
    <w:rPr><w:b/><w:sz w:val="23"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph">
    <w:name w:val="List Paragraph"/>
    <w:pPr><w:ind w:left="720"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Code">
    <w:name w:val="Code"/>
    <w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/><w:sz w:val="18"/></w:rPr>
  </w:style>
  <w:style w:type="table" w:styleId="TableGrid">
    <w:name w:val="Table Grid"/>
    <w:tblPr><w:tblBorders>
      <w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      <w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      <w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      <w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      <w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>
      <w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>
    </w:tblBorders></w:tblPr>
  </w:style>
</w:styles>'''


def write_docx(markdown_path: Path, docx_path: Path) -> None:
    body = markdown_to_body(markdown_path.read_text(encoding="utf-8"))
    with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>''')
        docx.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>''')
        docx.writestr("word/_rels/document.xml.rels", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>''')
        docx.writestr("word/document.xml", document_xml(body))
        docx.writestr("word/styles.xml", styles_xml())
        docx.writestr("docProps/core.xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Package 1 - Executive Architecture Document</dc:title>
  <dc:creator>LexiFlow</dc:creator>
</cp:coreProperties>''')
        docx.writestr("docProps/app.xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>LexiFlow Documentation Generator</Application>
</Properties>''')


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python scripts/markdown_to_docx.py input.md output.docx")
        raise SystemExit(2)
    write_docx(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
