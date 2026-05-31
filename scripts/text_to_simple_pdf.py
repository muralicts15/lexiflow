"""Create a simple text PDF without third-party dependencies."""

import textwrap
from pathlib import Path


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_page(lines) -> bytes:
    commands = ["BT", "/F1 10 Tf", "50 760 Td", "14 TL"]
    for line in lines:
        commands.append(f"({pdf_escape(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    return stream


def write_pdf(text_path: Path, pdf_path: Path) -> None:
    text = text_path.read_text(encoding="utf-8")
    wrapped_lines = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(textwrap.wrap(paragraph, width=92))

    lines_per_page = 50
    pages = [
        wrapped_lines[index : index + lines_per_page]
        for index in range(0, len(wrapped_lines), lines_per_page)
    ]

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    page_refs = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{page_refs}] /Count {len(pages)} >>".encode())

    for page_index, page_lines in enumerate(pages):
        page_obj_id = 3 + page_index * 2
        content_obj_id = page_obj_id + 1
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> "
                f"/Contents {content_obj_id} 0 R >>"
            ).encode()
        )
        stream = build_page(page_lines)
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    pdf_path.write_bytes(output)


if __name__ == "__main__":
    write_pdf(
        Path("samples/lexiflow_customer_care_business_rules.txt"),
        Path("samples/lexiflow_customer_care_business_rules.pdf"),
    )
