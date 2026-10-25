import html

from weasyprint import HTML


def render_application_pdf(context: dict) -> bytes:
    """Render the formatted A4 application PDF: institution header, applicant photo,
    every field saved across the form steps, payment reference, declaration, and
    signature (FR-8)."""
    return HTML(string=_application_template(context)).write_pdf()


def render_receipt_pdf(context: dict) -> bytes:
    """Render a short A4 payment receipt, sent as a separate attachment (FR-9)."""
    return HTML(string=_receipt_template(context)).write_pdf()


def _esc(value) -> str:
    """Escape a value before interpolating it into the HTML template. Form field
    values come from applicant input, so this prevents a field like a name or address
    containing '<' or '&' from breaking the generated layout."""
    if value is None or value == "":
        return "—"
    return html.escape(str(value))


def _flatten(data, prefix: str = ""):
    """Turn a possibly-nested dict of form-step data into flat (label, value) rows.

    The field names inside each step's JSONB blob belong to whoever builds Steps 1-6
    (Person 2 — see IMPLEMENTATION_PLAN.md) and may still be in flux. Flattening
    generically here means this renderer never has to know those field names and
    won't break as that work lands or changes.
    """
    rows = []
    if not isinstance(data, dict):
        return [(prefix or "value", data)]
    for key, value in data.items():
        label = f"{prefix} / {key}" if prefix else key
        if isinstance(value, dict):
            rows.extend(_flatten(value, label))
        else:
            rows.append((label, value))
    return rows


_WORDS = {
    "ews": "EWS", "ug": "UG", "id": "ID", "cgpa": "CGPA", "x": "Class X", "xii": "Class XII",
    "comm": "Communication", "perm": "Permanent", "line1": "line 1", "line2": "line 2",
}


def _humanize(label: str) -> str:
    """'father_name' -> 'Father name', 'comm_line1' -> 'Communication line 1', 'ews' -> 'EWS'."""
    parts = []
    for part in str(label).split(" / "):
        words = [_WORDS.get(word.lower(), word) for word in part.replace("_", " ").split()]
        text = " ".join(words)
        parts.append(text[:1].upper() + text[1:])
    return " / ".join(parts)


def _rows_html(data: dict) -> str:
    """One titled table per step. `data` maps a step title to that step's saved fields."""
    sections = []
    for title, fields in (data or {}).items():
        rows = _flatten(fields) if isinstance(fields, dict) else [(title, fields)]
        if not rows:
            continue
        cells = "".join(
            f"<tr><td class='label'>{_esc(_humanize(label))}</td><td>{_esc(value)}</td></tr>" for label, value in rows
        )
        sections.append(f"<h3>{_esc(title)}</h3><table>{cells}</table>")
    return "".join(sections) or "<p><em>No form data recorded.</em></p>"


# Printed at the foot of every page of every PDF (application, receipt, export). These files are emailed
# and downloaded, so they travel without the website's own notice and must say what they are.
DEMO_FOOTER = ("AdmitFlow is an academic project: AdmitFlow Institute is fictional. "
               "This document is not issued by any real college and is not an offer of admission.")

_BASE_STYLE = """
@page { size: A4; margin: 2cm;
        @bottom-center { content: "%s"; font-size: 8px; color: #777; } }""" % DEMO_FOOTER + """
body { font-family: sans-serif; color: #111; }
h1 { margin-bottom: 0; }
h2 { color: #444; font-weight: normal; margin-top: 0.2cm; }
h3 { margin: 0.6cm 0 0; font-size: 14px; color: #222; }
table { width: 100%; border-collapse: collapse; margin-top: 0.5cm; }
td { padding: 4px 8px; border-bottom: 1px solid #ddd; font-size: 12px; }
td.label { font-weight: bold; width: 40%; }
"""


def _application_template(context: dict) -> str:
    photo_html = f"<img class='photo' src='{context['photo_url']}' />" if context.get("photo_url") else ""
    signature_html = (
        f"<img class='signature' src='{context['signature_url']}' />" if context.get("signature_url") else ""
    )
    programme_line = _esc(context.get("programme"))
    if context.get("specialisation"):
        programme_line += f" / {_esc(context.get('specialisation'))}"

    return f"""
    <html>
      <head>
        <style>
          {_BASE_STYLE}
          .photo {{ float: right; width: 3cm; height: 4cm; object-fit: cover; border: 1px solid #999; }}
          .signature {{ width: 4cm; margin-top: 0.5cm; }}
          .declaration {{ margin-top: 1cm; font-size: 11px; color: #333; }}
        </style>
      </head>
      <body>
        {photo_html}
        <h1>{_esc(context.get('institution_name', 'AdmitFlow'))}</h1>
        <h2>Application Summary — {programme_line}</h2>
        <p><strong>Applicant:</strong> {_esc(context.get('full_name'))}</p>
        <p><strong>Payment Reference:</strong> {_esc(context.get('payment_reference'))}</p>

        {_rows_html(context.get('form_data', {}))}

        <p class="declaration">
          I declare that the information provided above is true and accurate to the best of my knowledge.
        </p>
        {signature_html}
      </body>
    </html>
    """


def render_applicants_pdf(context: dict) -> bytes:
    """Render the admin's applicant export as a landscape A4 table (FR-11).

    Args:
        context: institution_name, generated_at (text), filters (text describing the filters),
            headers (column titles) and rows (lists of cell values, in header order).
    Returns:
        The PDF as bytes. Every value is HTML-escaped: applicant names come from applicants.
    """
    return HTML(string=_applicants_template(context)).write_pdf()


def _applicants_template(context: dict) -> str:
    head = "".join(f"<th>{_esc(h)}</th>" for h in context.get("headers", []))
    body = "".join(
        "<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in row) + "</tr>" for row in context.get("rows", [])
    ) or f"<tr><td colspan='{max(len(context.get('headers', [])), 1)}'><em>No applicants match these filters.</em></td></tr>"
    return f"""
    <html>
      <head>
        <style>
          {_BASE_STYLE}
          @page {{ size: A4 landscape; margin: 1.2cm; @bottom-right {{ content: "Page " counter(page) " of " counter(pages); font-size: 9px; }} }}
          .meta {{ font-size: 11px; color: #444; margin: 0.1cm 0; }}
          th {{ text-align: left; font-size: 10px; padding: 4px 6px; border-bottom: 2px solid #333; background: #f2f2f2; }}
          td {{ font-size: 10px; padding: 3px 6px; }}
          thead {{ display: table-header-group; }}
          tr {{ page-break-inside: avoid; }}
        </style>
      </head>
      <body>
        <h1>{_esc(context.get('institution_name', 'AdmitFlow'))}</h1>
        <h2>Applicant export</h2>
        <p class="meta">Generated {_esc(context.get('generated_at'))} &middot; {len(context.get('rows', []))} applicant(s)</p>
        <p class="meta">Filters: {_esc(context.get('filters'))}</p>
        <table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
      </body>
    </html>
    """


def _receipt_template(context: dict) -> str:
    return f"""
    <html>
      <head><style>{_BASE_STYLE}</style></head>
      <body>
        <h1>{_esc(context.get('institution_name', 'AdmitFlow'))}</h1>
        <h2>Payment Receipt</h2>
        <table>
          <tr><td class="label">Applicant</td><td>{_esc(context.get('full_name'))}</td></tr>
          <tr><td class="label">Programme</td><td>{_esc(context.get('programme'))}</td></tr>
          <tr><td class="label">Amount Paid</td><td>Rs. {_esc(context.get('amount'))}</td></tr>
          <tr><td class="label">Razorpay Payment ID</td><td>{_esc(context.get('payment_id'))}</td></tr>
          <tr><td class="label">Razorpay Order ID</td><td>{_esc(context.get('order_id'))}</td></tr>
          <tr><td class="label">Paid On</td><td>{_esc(context.get('paid_on'))}</td></tr>
        </table>
        {"<p><strong>Test mode:</strong> this payment was made in the payment gateway's test mode. No real money was charged, and this receipt is not proof of any real payment.</p>" if context.get("test_mode") else ""}
      </body>
    </html>
    """
