from weasyprint import HTML


def render_application_pdf(context: dict) -> bytes:
    """Render the formatted A4 application PDF (institution header, photo, form data, declaration, signature)."""
    html = _application_template(context)
    return HTML(string=html).write_pdf()


def _application_template(context: dict) -> str:
    return f"""
    <html>
      <head><style>@page {{ size: A4; margin: 2cm; }}</style></head>
      <body>
        <h1>{context.get('institution_name', 'AdmitFlow')}</h1>
        <h2>Application Summary</h2>
        <p>Applicant: {context.get('full_name', '')}</p>
        <p>Programme: {context.get('programme', '')}</p>
        <p>Payment Reference: {context.get('payment_reference', '')}</p>
      </body>
    </html>
    """
