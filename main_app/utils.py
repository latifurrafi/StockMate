from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
import os
from xhtml2pdf import pisa

def render_to_pdf(template_src, context_dict={}):
    """
    Generate a PDF from an HTML template and context data
    """
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    
    # Create PDF
    pdf = pisa.pisaDocument(
        BytesIO(html.encode("UTF-8")), 
        result,
        encoding='UTF-8',
        link_callback=fetch_resources
    )
    
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

def fetch_resources(uri, rel):
    """
    Callback to handle resource files (CSS, images) for the PDF generation
    """
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    elif uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    else:
        path = os.path.join(settings.STATIC_ROOT, uri)
    
    return path 