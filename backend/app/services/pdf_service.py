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


def render_brochure_pdf(content: dict, fee_inr: int, demo_footer: str | None = None) -> bytes:
    """Render the information brochure (FR-1) from the site content (content_service.get_content()),
    so it always matches what the site shows. Every value is escaped: the content is admin-edited.

    Args:
        content: the site content sections.
        fee_inr: the application fee, used to fill {fee} placeholders.
        demo_footer: the disclaimer for the page footer ("" for none, None for the default text).
    """
    return HTML(string=_brochure_template(content, fee_inr, demo_footer)).write_pdf()


def _brochure_template(content: dict, fee_inr: int, demo_footer) -> str:
    fill = lambda s: _esc(str(s).replace("{fee}", f"₹{fee_inr:,}"))  # noqa: E731
    lis = lambda items: "".join(f"<li>{fill(x)}</li>" for x in items)  # noqa: E731
    context = {} if demo_footer is None else {"demo_footer": demo_footer}
    inst, contact, dates = content["institution"], content["contact"], content["dates"]
    programmes = "".join(
        f"<li><b>{_esc(p['name'])}</b> ({'undergraduate' if p['level'] == 'UG' else 'postgraduate'}): "
        f"{_esc(', '.join(p['specialisations']))}</li>" for p in content["programmes"])
    date_rows = "".join(f"<tr><td>{_esc(d['label'])}</td><td><b>{_esc(d['value'])}</b></td></tr>" for d in dates["items"])
    about = "".join(f"<p>{fill(p)}</p>" for p in inst.get("about", []))
    contact_lines = "<br>".join(_esc(v) for v in (contact.get("email"), contact.get("phone"), contact.get("address"),
                                                  contact.get("hours")) if v)
    note = f"<p>{_esc(contact['note'])}</p>" if contact.get("note") else ""
    dates_note = f"<p class='sub'>{_esc(dates['note'])}</p>" if dates.get("note") else ""
    documents = f"<h2>Original documents checked at admission</h2><ul>{lis(content['documents'])}</ul>" if content["documents"] else ""
    about_box = f"<div class='about'>{about}</div>" if about else ""
    return f"""
    <html><head><style>
      {_style(context)}
      body {{ font-size: 12px; line-height: 1.45; }}
      h2 {{ font-size: 15px; margin: 18px 0 6px; border-bottom: 1px solid #ccc; padding-bottom: 3px; color: #111; font-weight: bold; }}
      .sub {{ color: #555; margin: 2px 0 12px; }}
      .about {{ border: 1px solid #ccc; background: #f7f7f7; padding: 4px 10px; border-radius: 4px; }}
      td {{ padding: 3px 14px 3px 0; vertical-align: top; border: none; }} li {{ margin: 2px 0; }}
    </style></head><body>
      <h1>{_esc(inst['name'])}</h1>
      <p class="sub">Information brochure: admissions</p>
      {about_box}
      <h2>Programmes</h2><ul>{programmes}</ul>
      <h2>Eligibility</h2><ul>{lis(content['eligibility'])}</ul>
      <h2>Important dates</h2><table>{date_rows}</table>{dates_note}
      <h2>Application fee</h2><p>{_esc(f"Rs. {fee_inr:,}")} (non-refundable), paid online after the application form is complete.</p>
      <h2>How to apply</h2><ol>{lis([g for g in content['guidelines'] if 'I Agree' not in g])}</ol>
      {documents}
      <h2>Contact</h2><p>{contact_lines}</p>{note}
    </body></html>
    """


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
    """One titled table per step. `data` maps a step title to that step's saved fields: either
    (label, value) rows already in order (form_fields.ordered_rows), or a raw dict to flatten."""
    sections = []
    for title, fields in (data or {}).items():
        if isinstance(fields, list):
            rows, label_of = fields, str
        else:
            rows = _flatten(fields) if isinstance(fields, dict) else [(title, fields)]
            label_of = _humanize
        if not rows:
            continue
        cells = "".join(
            f"<tr><td class='label'>{_esc(label_of(label))}</td><td>{_esc(value)}</td></tr>" for label, value in rows
        )
        sections.append(f"<h3>{_esc(title)}</h3><table>{cells}</table>")
    return "".join(sections) or "<p><em>No form data recorded.</em></p>"


# Printed at the foot of every page of every PDF (application, receipt, export, brochure). These files
# are emailed and downloaded, so they travel without the website's own notice and must say what they
# are. Callers pass context["demo_footer"] (content_service.demo_footer(): the institution's name,
# or "" on a real deployment); this is the text used when a caller passes none.
DEMO_FOOTER = ("AdmitFlow is an academic project: AdmitFlow Institute is fictional. "
               "This document is not issued by any real college and is not an offer of admission.")


def _css_string(value: str) -> str:
    """Text safe inside a CSS "..." string inside an HTML <style> element. The institution name in it
    is admin-editable, so a quote, a backslash or a '</style>' must not end the string or the element."""
    out = []
    for ch in str(value):
        if ch in '"\\<>' or ord(ch) < 0x20:
            out.append(f"\\{ord(ch):x} ")
        else:
            out.append(ch)
    return "".join(out)


def _style(context: dict) -> str:
    """The shared page style, with the disclaimer footer unless the caller turned it off."""
    footer = context.get("demo_footer", DEMO_FOOTER)
    page = "@page { size: A4; margin: 2cm; }"
    if footer:
        page = ('@page { size: A4; margin: 2cm; @bottom-center { content: "%s"; font-size: 8px; color: #777; } }'
                % _css_string(footer))
    return page + _BASE_STYLE


_BASE_STYLE = """
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
          {_style(context)}
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
          {_style(context)}
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
      <head><style>{_style(context)}</style></head>
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
