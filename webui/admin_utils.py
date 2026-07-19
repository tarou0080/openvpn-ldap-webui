#!/usr/bin/env python3
from flask import flash, render_template, redirect, url_for
from flask_wtf.csrf import generate_csrf
from auth import get_user_from_headers, is_admin_domain, is_admin_user, get_domain_info
from config import CERT_EXPIRE_DAYS
from translations import _

def render_with_context(template_name, **kwargs):
    """Render template with common context variables"""
    context = {
        'user': get_user_from_headers(),
        'domain': get_domain_info(),
        'csrf_token': generate_csrf,
        'cert_expire_days': CERT_EXPIRE_DAYS
    }
    context.update(kwargs)
    return render_template(template_name, **context)

def require_admin():
    """Admin permission check decorator"""
    user = get_user_from_headers()
    if not is_admin_domain() or not is_admin_user(user):
        flash(_('Admin privileges are required.'), 'error')
        return redirect(url_for('user.index'))
    return None
