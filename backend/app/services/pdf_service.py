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


def _rows_html(data: dict) -> str:
    rows = _flatten(data or {})
    if not rows:
        return "<p><em>No form data recorded.</em></p>"
    cells = "".join(f"<tr><td class='label'>{_esc(label)}</td><td>{_esc(value)}</td></tr>" for label, value in rows)
    return f"<table>{cells}</table>"


_BASE_STYLE = """
@page { size: A4; margin: 2cm; }
body { font-family: sans-serif; color: #111; }
h1 { margin-bottom: 0; }
h2 { color: #444; font-weight: normal; margin-top: 0.2cm; }
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
      </body>
    </html>
    """
