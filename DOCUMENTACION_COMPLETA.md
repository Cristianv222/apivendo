================================================================================
                    DOCUMENTACIÓN COMPLETA - PROYECTO APP
================================================================================

INFORMACIÓN GENERAL
-------------------
Fecha de generación: 2025-09-16 18:52:04
Ubicación: /app
Python Version: Python 3.10.18
Pip Version: pip 25.2 from /usr/local/lib/python3.10/site-packages/pip (python 3.10)
Entorno Virtual: ❌ NO ACTIVO
Sistema Operativo: Linux
Usuario: Desconocido

================================================================================
                            ESTRUCTURA DEL PROYECTO
================================================================================

├── venv/ (excluido)
├── apps/ (12 elementos)
│   ├── api/ (16 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (1 elementos)
│   │   │   │   └── __init__.py (0B)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── serializers/ (5 elementos)
│   │   │   ├── __init__.py (540.0B)
│   │   │   ├── certificate_serializers.py (9.4KB)
│   │   │   ├── company_serializers.py (1.9KB)
│   │   │   ├── invoicing_serializers.py (8.0KB)
│   │   │   └── sri_serializers.py (40.6KB)
│   │   ├── tests/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── v1/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── v2/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── views/ (5 elementos)
│   │   │   ├── __init__.py (361.0B)
│   │   │   ├── auth_views.py (7.7KB)
│   │   │   ├── certificate_views.py (14.9KB)
│   │   │   ├── company_views.py (9.3KB)
│   │   │   └── sri_views.py (86.2KB)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (0B)
│   │   ├── apps.py (0B)
│   │   ├── authentication.py (10.3KB)
│   │   ├── models.py (97.0B)
│   │   ├── permissions.py (22.8KB)
│   │   ├── urls.py (20.8KB)
│   │   ├── user_company_helper.py (12.9KB)
│   │   └── views.py (0B)
│   ├── billing/ (11 elementos)
│   │   ├── migrations/ (4 elementos)
│   │   │   ├── 0001_fix_plan_purchase_fields.py (1.3KB)
│   │   │   ├── 0001_initial.py (8.2KB)
│   │   │   ├── 0002_alter_planpurchase_plan_invoice_limit_and_more.py (937.0B)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (9.9KB)
│   │   ├── apps.py (437.0B)
│   │   ├── forms.py (8.4KB)
│   │   ├── middleware.py (18.6KB)
│   │   ├── models.py (12.5KB)
│   │   ├── signals.py (6.7KB)
│   │   ├── tests.py (63.0B)
│   │   ├── urls.py (4.0KB)
│   │   └── views.py (12.9KB)
│   ├── certificates/ (13 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (2 elementos)
│   │   │   │   ├── __init__.py (0B)
│   │   │   │   └── sync_certificates.py (2.1KB)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (3 elementos)
│   │   │   ├── 0001_initial.py (6.0KB)
│   │   │   ├── 0002_add_storage_path.py (747.0B)
│   │   │   └── __init__.py (0B)
│   │   ├── services/ (2 elementos)
│   │   │   ├── __init__.py (20.0B)
│   │   │   └── certificate_reader.py (6.9KB)
│   │   ├── tests/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (24.0KB)
│   │   ├── apps.py (14.2KB)
│   │   ├── forms.py (6.4KB)
│   │   ├── models.py (22.7KB)
│   │   ├── serializers.py (25.2KB)
│   │   ├── signals.py (39.1KB)
│   │   ├── urls.py (503.0B)
│   │   └── views.py (10.7KB)
│   ├── companies/ (11 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (2 elementos)
│   │   │   │   ├── __init__.py (0B)
│   │   │   │   └── create_test_data.py (13.3KB)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (4 elementos)
│   │   │   ├── 0001_initial.py (1.8KB)
│   │   │   ├── 0002_companyapitoken.py (3.5KB)
│   │   │   ├── 0003_company_ambiente_sri_company_ciudad_and_more.py (5.9KB)
│   │   │   └── __init__.py (0B)
│   │   ├── tests/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (3.7KB)
│   │   ├── apps.py (0B)
│   │   ├── forms.py (5.6KB)
│   │   ├── models.py (20.9KB)
│   │   ├── serializers.py (684.0B)
│   │   ├── urls.py (395.0B)
│   │   └── views.py (1.7KB)
│   ├── core/ (11 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (1 elementos)
│   │   │   │   └── __init__.py (0B)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (4 elementos)
│   │   │   ├── 0001_initial.py (6.5KB)
│   │   │   ├── 0002_initial.py (3.3KB)
│   │   │   ├── 0003_add_comprehensive_audit_actions.py (2.1KB)
│   │   │   └── __init__.py (0B)
│   │   ├── tests/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (3.7KB)
│   │   ├── apps.py (372.0B)
│   │   ├── middleware.py (1.9KB)
│   │   ├── models.py (11.1KB)
│   │   ├── session_views.py (5.6KB)
│   │   ├── urls.py (8.3KB)
│   │   └── views.py (76.2KB)
│   ├── custom_admin/ (5 elementos)
│   │   ├── __init__.py (63.0B)
│   │   ├── apps.py (234.0B)
│   │   ├── models.py (89.0B)
│   │   ├── urls.py (6.7KB)
│   │   └── views.py (123.1KB)
│   ├── invoicing/ (10 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (1 elementos)
│   │   │   │   └── __init__.py (0B)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (2 elementos)
│   │   │   ├── 0001_initial.py (16.8KB)
│   │   │   └── __init__.py (0B)
│   │   ├── tests/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (5.9KB)
│   │   ├── apps.py (397.0B)
│   │   ├── models.py (11.6KB)
│   │   ├── serializers.py (1.8KB)
│   │   ├── urls.py (752.0B)
│   │   └── views.py (2.6KB)
│   ├── notifications/ (10 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (1 elementos)
│   │   │   │   └── __init__.py (0B)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (2 elementos)
│   │   │   ├── 0001_initial.py (17.0KB)
│   │   │   └── __init__.py (0B)
│   │   ├── tests/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (0B)
│   │   ├── apps.py (411.0B)
│   │   ├── models.py (13.2KB)
│   │   ├── serializers.py (514.0B)
│   │   ├── urls.py (418.0B)
│   │   └── views.py (954.0B)
│   ├── settings/ (10 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (1 elementos)
│   │   │   │   └── __init__.py (0B)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (2 elementos)
│   │   │   ├── 0001_initial.py (14.3KB)
│   │   │   └── __init__.py (0B)
│   │   ├── tests/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (6.3KB)
│   │   ├── apps.py (396.0B)
│   │   ├── models.py (11.4KB)
│   │   ├── serializers.py (340.0B)
│   │   ├── urls.py (393.0B)
│   │   └── views.py (1.1KB)
│   ├── sri_integration/ (12 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (5 elementos)
│   │   │   │   ├── __init__.py (0B)
│   │   │   │   ├── check_sri_documents.py (4.6KB)
│   │   │   │   ├── preload_certificates.py (13.3KB)
│   │   │   │   ├── process_invoices.py (11.6KB)
│   │   │   │   └── send_test_invoice.py (1.7KB)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (6 elementos)
│   │   │   ├── 0001_initial.py (17.2KB)
│   │   │   ├── 0002_sriconfiguration_purchase_settlement_sequence_and_more.py (21.3KB)
│   │   │   ├── 0003_alter_sriconfiguration_is_active.py (526.0B)
│   │   │   ├── 0004_alter_documentitem_discount_and_more.py (2.8KB)
│   │   │   ├── 0005_alter_purchasesettlement_options_and_more.py (1.0KB)
│   │   │   └── __init__.py (0B)
│   │   ├── services/ (13 elementos)
│   │   │   ├── __init__.py (705.0B)
│   │   │   ├── auto_authorization.py (18.7KB)
│   │   │   ├── certificate_manager.py (16.1KB)
│   │   │   ├── digital_signer.py (9.0KB)
│   │   │   ├── document_processor.py (56.7KB)
│   │   │   ├── email_service.py (10.2KB)
│   │   │   ├── global_certificate_manager.py (17.1KB)
│   │   │   ├── pdf_generator.py (17.2KB)
│   │   │   ├── sendgrid_service.py (2.2KB)
│   │   │   ├── simple_xml_signer.py (2.8KB)
│   │   │   ├── soap_client.py (71.4KB)
│   │   │   ├── sri_processor.py (20.0KB)
│   │   │   └── xml_generator.py (49.4KB)
│   │   ├── tests/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── admin.py (10.4KB)
│   │   ├── apps.py (416.0B)
│   │   ├── models.py (49.8KB)
│   │   ├── serializers.py (4.0KB)
│   │   ├── tasks.py (18.7KB)
│   │   ├── urls.py (659.0B)
│   │   └── views.py (30.7KB)
│   ├── users/ (11 elementos)
│   │   ├── management/ (2 elementos)
│   │   │   ├── commands/ (2 elementos)
│   │   │   │   ├── __init__.py (0B)
│   │   │   │   └── setup_oauth.py (10.9KB)
│   │   │   └── __init__.py (0B)
│   │   ├── migrations/ (4 elementos)
│   │   │   ├── 0001_initial.py (4.7KB)
│   │   │   ├── 0002_add_waiting_room_models.py (4.0KB)
│   │   │   ├── 0003_add_user_status_fields.py (1.5KB)
│   │   │   └── __init__.py (0B)
│   │   ├── tests/ (1 elementos)
│   │   │   └── __init__.py (0B)
│   │   ├── __init__.py (0B)
│   │   ├── adapters.py (9.4KB)
│   │   ├── admin.py (17.6KB)
│   │   ├── apps.py (550.0B)
│   │   ├── models.py (12.0KB)
│   │   ├── signals.py (9.1KB)
│   │   ├── urls.py (453.0B)
│   │   └── views.py (8.3KB)
│   └── __init__.py (0B)
├── certificates/ (0 elementos)
├── docs/ (5 elementos)
│   ├── api/ (0 elementos)
│   ├── deployment/ (0 elementos)
│   ├── development/ (0 elementos)
│   ├── security/ (0 elementos)
│   └── sri_integration/ (0 elementos)
├── fixtures/ (0 elementos)
├── locale/ (2 elementos)
│   ├── en/ (1 elementos)
│   │   └── LC_MESSAGES/ (0 elementos)
│   └── es/ (1 elementos)
│       └── LC_MESSAGES/ (0 elementos)
├── logs/ (4 elementos)
│   ├── celery.log (0B)
│   ├── certificates.log (10.0KB)
│   ├── sri_integration.log (670.0B)
│   └── vendo_sri.log (158.0B)
├── mediafiles/ (0 elementos)
├── scripts/ (0 elementos)
├── services/ (1 elementos)
│   └── __init__.py (0B)
├── static/ (3 elementos)
│   ├── admin/ (3 elementos)
│   │   ├── css/ (0 elementos)
│   │   ├── img/ (0 elementos)
│   │   └── js/ (0 elementos)
│   ├── api_docs/ (0 elementos)
│   └── js/ (2 elementos)
│       ├── auto-logout.js (5.0KB)
│       └── session-manager.js (14.8KB)
├── staticfiles/ (6 elementos)
│   ├── account/ (1 elementos)
│   │   └── js/ (2 elementos)
│   │       ├── account.js (437.0B)
│   │       └── onload.js (495.0B)
│   ├── admin/ (3 elementos)
│   │   ├── css/ (14 elementos)
│   │   │   ├── vendor/ (1 elementos)
│   │   │   │   └── select2/ (3 elementos)
│   │   │   │       ├── LICENSE-SELECT2.md (1.1KB)
│   │   │   │       ├── select2.css (17.0KB)
│   │   │   │       └── select2.min.css (14.6KB)
│   │   │   ├── autocomplete.css (9.0KB)
│   │   │   ├── base.css (21.6KB)
│   │   │   ├── changelists.css (6.7KB)
│   │   │   ├── dark_mode.css (2.7KB)
│   │   │   ├── dashboard.css (441.0B)
│   │   │   ├── forms.css (8.3KB)
│   │   │   ├── login.css (951.0B)
│   │   │   ├── nav_sidebar.css (2.7KB)
│   │   │   ├── responsive.css (16.2KB)
│   │   │   ├── responsive_rtl.css (1.9KB)
│   │   │   ├── rtl.css (4.7KB)
│   │   │   ├── unusable_password_field.css (663.0B)
│   │   │   └── widgets.css (11.7KB)
│   │   ├── img/ (22 elementos)
│   │   │   ├── gis/ (2 elementos)
│   │   │   │   ├── move_vertex_off.svg (1.1KB)
│   │   │   │   └── move_vertex_on.svg (1.1KB)
│   │   │   ├── calendar-icons.svg (2.4KB)
│   │   │   ├── icon-addlink.svg (331.0B)
│   │   │   ├── icon-alert.svg (504.0B)
│   │   │   ├── icon-calendar.svg (1.1KB)
│   │   │   ├── icon-changelink.svg (380.0B)
│   │   │   ├── icon-clock.svg (677.0B)
│   │   │   ├── icon-deletelink.svg (392.0B)
│   │   │   ├── icon-hidelink.svg (784.0B)
│   │   │   ├── icon-no.svg (560.0B)
│   │   │   ├── icon-unknown-alt.svg (655.0B)
│   │   │   ├── icon-unknown.svg (655.0B)
│   │   │   ├── icon-viewlink.svg (581.0B)
│   │   │   ├── icon-yes.svg (436.0B)
│   │   │   ├── inline-delete.svg (537.0B)
│   │   │   ├── LICENSE (1.1KB)
│   │   │   ├── README.txt (321.0B)
│   │   │   ├── search.svg (458.0B)
│   │   │   ├── selector-icons.svg (3.2KB)
│   │   │   ├── sorting-icons.svg (1.1KB)
│   │   │   ├── tooltag-add.svg (331.0B)
│   │   │   └── tooltag-arrowright.svg (280.0B)
│   │   └── js/ (20 elementos)
│   │       ├── admin/ (2 elementos)
│   │       │   ├── DateTimeShortcuts.js (18.9KB)
│   │       │   └── RelatedObjectLookups.js (9.5KB)
│   │       ├── vendor/ (3 elementos)
│   │       │   ├── jquery/ (3 elementos)
│   │       │   │   ├── jquery.js (278.6KB)
│   │       │   │   ├── jquery.min.js (85.5KB)
│   │       │   │   └── LICENSE.txt (1.1KB)
│   │       │   ├── select2/ (4 elementos)
│   │       │   │   ├── i18n/ (59 elementos)
│   │       │   │   │   ├── af.js (866.0B)
│   │       │   │   │   ├── ar.js (905.0B)
│   │       │   │   │   ├── az.js (721.0B)
│   │       │   │   │   ├── bg.js (968.0B)
│   │       │   │   │   ├── bn.js (1.3KB)
│   │       │   │   │   ├── bs.js (965.0B)
│   │       │   │   │   ├── ca.js (900.0B)
│   │       │   │   │   ├── cs.js (1.3KB)
│   │       │   │   │   ├── da.js (828.0B)
│   │       │   │   │   ├── de.js (866.0B)
│   │       │   │   │   ├── dsb.js (1017.0B)
│   │       │   │   │   ├── el.js (1.2KB)
│   │       │   │   │   ├── en.js (844.0B)
│   │       │   │   │   ├── es.js (922.0B)
│   │       │   │   │   ├── et.js (801.0B)
│   │       │   │   │   ├── eu.js (868.0B)
│   │       │   │   │   ├── fa.js (1023.0B)
│   │       │   │   │   ├── fi.js (803.0B)
│   │       │   │   │   ├── fr.js (924.0B)
│   │       │   │   │   ├── gl.js (924.0B)
│   │       │   │   │   ├── he.js (984.0B)
│   │       │   │   │   ├── hi.js (1.1KB)
│   │       │   │   │   ├── hr.js (852.0B)
│   │       │   │   │   ├── hsb.js (1018.0B)
│   │       │   │   │   ├── hu.js (831.0B)
│   │       │   │   │   ├── hy.js (1.0KB)
│   │       │   │   │   ├── id.js (768.0B)
│   │       │   │   │   ├── is.js (807.0B)
│   │       │   │   │   ├── it.js (897.0B)
│   │       │   │   │   ├── ja.js (862.0B)
│   │       │   │   │   ├── ka.js (1.2KB)
│   │       │   │   │   ├── km.js (1.1KB)
│   │       │   │   │   ├── ko.js (855.0B)
│   │       │   │   │   ├── lt.js (944.0B)
│   │       │   │   │   ├── lv.js (900.0B)
│   │       │   │   │   ├── mk.js (1.0KB)
│   │       │   │   │   ├── ms.js (811.0B)
│   │       │   │   │   ├── nb.js (778.0B)
│   │       │   │   │   ├── ne.js (1.3KB)
│   │       │   │   │   ├── nl.js (904.0B)
│   │       │   │   │   ├── pl.js (947.0B)
│   │       │   │   │   ├── ps.js (1.0KB)
│   │       │   │   │   ├── pt-BR.js (876.0B)
│   │       │   │   │   ├── pt.js (878.0B)
│   │       │   │   │   ├── ro.js (938.0B)
│   │       │   │   │   ├── ru.js (1.1KB)
│   │       │   │   │   ├── sk.js (1.3KB)
│   │       │   │   │   ├── sl.js (925.0B)
│   │       │   │   │   ├── sq.js (903.0B)
│   │       │   │   │   ├── sr-Cyrl.js (1.1KB)
│   │       │   │   │   ├── sr.js (980.0B)
│   │       │   │   │   ├── sv.js (786.0B)
│   │       │   │   │   ├── th.js (1.0KB)
│   │       │   │   │   ├── tk.js (771.0B)
│   │       │   │   │   ├── tr.js (775.0B)
│   │       │   │   │   ├── uk.js (1.1KB)
│   │       │   │   │   ├── vi.js (796.0B)
│   │       │   │   │   ├── zh-CN.js (768.0B)
│   │       │   │   │   └── zh-TW.js (707.0B)
│   │       │   │   ├── LICENSE.md (1.1KB)
│   │       │   │   ├── select2.full.js (169.5KB)
│   │       │   │   └── select2.full.min.js (77.4KB)
│   │       │   └── xregexp/ (3 elementos)
│   │       │       ├── LICENSE.txt (1.1KB)
│   │       │       ├── xregexp.js (317.5KB)
│   │       │       └── xregexp.min.js (159.4KB)
│   │       ├── actions.js (7.9KB)
│   │       ├── autocomplete.js (1.0KB)
│   │       ├── calendar.js (8.9KB)
│   │       ├── cancel.js (884.0B)
│   │       ├── change_form.js (606.0B)
│   │       ├── core.js (6.1KB)
│   │       ├── filters.js (978.0B)
│   │       ├── inlines.js (15.3KB)
│   │       ├── jquery.init.js (347.0B)
│   │       ├── nav_sidebar.js (3.0KB)
│   │       ├── popup_response.js (532.0B)
│   │       ├── prepopulate.js (1.5KB)
│   │       ├── prepopulate_init.js (586.0B)
│   │       ├── SelectBox.js (4.4KB)
│   │       ├── SelectFilter2.js (15.5KB)
│   │       ├── theme.js (1.6KB)
│   │       ├── unusable_password_field.js (1.4KB)
│   │       └── urlify.js (7.7KB)
│   ├── debug_toolbar/ (2 elementos)
│   │   ├── css/ (2 elementos)
│   │   │   ├── print.css (43.0B)
│   │   │   └── toolbar.css (28.8KB)
│   │   └── js/ (5 elementos)
│   │       ├── history.js (3.4KB)
│   │       ├── redirect.js (48.0B)
│   │       ├── timer.js (3.3KB)
│   │       ├── toolbar.js (14.5KB)
│   │       └── utils.js (4.6KB)
│   ├── images/ (5 elementos)
│   │   ├── frontera-logo-complete.png (33.3KB)
│   │   ├── frontera-logo-ft.png (3.4KB)
│   │   ├── frontera-logo-full.png (41.4KB)
│   │   ├── frontera-logo-hex.png (6.6KB)
│   │   └── frontera-logo-hexasd.png (6.6KB)
│   ├── js/ (2 elementos)
│   │   ├── auto-logout.js (5.0KB)
│   │   └── session-manager.js (14.8KB)
│   └── rest_framework/ (5 elementos)
│       ├── css/ (8 elementos)
│       │   ├── bootstrap-theme.min.css (22.9KB)
│       │   ├── bootstrap-theme.min.css.map (73.8KB)
│       │   ├── bootstrap-tweaks.css (3.3KB)
│       │   ├── bootstrap.min.css (118.6KB)
│       │   ├── bootstrap.min.css.map (527.8KB)
│       │   ├── default.css (1.1KB)
│       │   ├── font-awesome-4.0.3.css (21.2KB)
│       │   └── prettify.css (817.0B)
│       ├── docs/ (3 elementos)
│       │   ├── css/ (3 elementos)
│       │   │   ├── base.css (6.0KB)
│       │   │   ├── highlight.css (1.6KB)
│       │   │   └── jquery.json-view.min.css (1.3KB)
│       │   ├── img/ (2 elementos)
│       │   │   ├── favicon.ico (5.3KB)
│       │   │   └── grid.png (1.4KB)
│       │   └── js/ (3 elementos)
│       │       ├── api.js (10.1KB)
│       │       ├── highlight.pack.js (293.7KB)
│       │       └── jquery.json-view.min.js (2.6KB)
│       ├── fonts/ (9 elementos)
│       │   ├── fontawesome-webfont.eot (37.3KB)
│       │   ├── fontawesome-webfont.svg (197.4KB)
│       │   ├── fontawesome-webfont.ttf (78.8KB)
│       │   ├── fontawesome-webfont.woff (43.4KB)
│       │   ├── glyphicons-halflings-regular.eot (19.7KB)
│       │   ├── glyphicons-halflings-regular.svg (106.2KB)
│       │   ├── glyphicons-halflings-regular.ttf (44.3KB)
│       │   ├── glyphicons-halflings-regular.woff (22.9KB)
│       │   └── glyphicons-halflings-regular.woff2 (17.6KB)
│       ├── img/ (3 elementos)
│       │   ├── glyphicons-halflings-white.png (8.6KB)
│       │   ├── glyphicons-halflings.png (12.5KB)
│       │   └── grid.png (1.4KB)
│       └── js/ (8 elementos)
│           ├── ajax-form.js (3.7KB)
│           ├── bootstrap.min.js (38.8KB)
│           ├── coreapi-0.1.1.js (153.9KB)
│           ├── csrf.js (1.8KB)
│           ├── default.js (1.2KB)
│           ├── jquery-3.7.1.min.js (85.5KB)
│           ├── load-ajax-form.js (59.0B)
│           └── prettify-min.js (13.3KB)
├── storage/ (7 elementos)
│   ├── backups/ (0 elementos)
│   ├── billing/ (1 elementos)
│   │   └── receipts/ (1 elementos)
│   │       └── 2025/ (1 elementos)
│   │           └── 07/ (17 elementos)
│   │               ├── Captura_de_pantalla_2025-02-26_091205.png (309.4KB)
│   │               ├── Captura_de_pantalla_2025-02-26_091205_GS582rL.png (309.4KB)
│   │               ├── Captura_de_pantalla_2025-02-26_091205_gw2VukM.png (309.4KB)
│   │               ├── Captura_de_pantalla_2025-02-26_091205_hXI4Yc7.png (309.4KB)
│   │               ├── Captura_de_pantalla_2025-02-26_091205_o2zKDaQ.png (309.4KB)
│   │               ├── Captura_de_pantalla_2025-02-26_091205_Q6lvvR9.png (309.4KB)
│   │               ├── Captura_de_pantalla_2025-02-26_091205_wuBAP9o.png (309.4KB)
│   │               ├── Captura_de_pantalla_2025-02-26_091359.png (86.4KB)
│   │               ├── Captura_de_pantalla_2025-03-05_072046.png (39.4KB)
│   │               ├── Captura_de_pantalla_2025-05-06_174657.png (457.5KB)
│   │               ├── Captura_de_pantalla_2025-07-23_112448.png (237.6KB)
│   │               ├── motul.png (3.7KB)
│   │               ├── motul_K7KpZoP.png (3.7KB)
│   │               ├── motul_LdGuATo.png (3.7KB)
│   │               ├── ytjyhjdggj.JPG (51.5KB)
│   │               ├── ytjyhjdggj_2oZodkp.JPG (51.5KB)
│   │               └── ytjyhjdggj_NlebzyD.JPG (51.5KB)
│   ├── certificates/ (0 elementos)
│   ├── companies/ (1 elementos)
│   │   └── logos/ (1 elementos)
│   │       └── WhatsApp_Image_2025-07-13_at_19.11.07.jpeg (41.7KB)
│   ├── invoices/ (2 elementos)
│   │   ├── pdf/ (1 elementos)
│   │   │   └── 1208202501100326984000110010010000000011234567811.pdf (4.0KB)
│   │   └── xml/ (2 elementos)
│   │       ├── 1208202501100326984000110010010000000011234567811.xml (2.3KB)
│   │       └── 1208202501100326984000110010010000000011234567811_signed.xml (7.6KB)
│   ├── logs/ (7 elementos)
│   │   ├── celery_beat.log (0B)
│   │   ├── celery_worker.log (0B)
│   │   ├── certificates.log (0B)
│   │   ├── gunicorn_access.log (0B)
│   │   ├── gunicorn_error.log (0B)
│   │   ├── sri_integration.log (0B)
│   │   └── vendo_sri.log (0B)
│   └── uploads/ (1 elementos)
│       └── 2025/ (1 elementos)
│           └── 07/ (1 elementos)
│               └── 13/ (1 elementos)
│                   └── acer-predator-logo-4k-wallpaper-uhdpaper.com-4623a.jpg (1.7MB)
├── templates/ (8 elementos)
│   ├── admin/ (1 elementos)
│   │   └── custom/ (0 elementos)
│   ├── api_docs/ (0 elementos)
│   ├── billing/ (2 elementos)
│   │   ├── plan_purchase.html (18.9KB)
│   │   └── purchase_success.html (17.8KB)
│   ├── custom_admin/ (11 elementos)
│   │   ├── audit_logs/ (1 elementos)
│   │   │   └── list.html (11.4KB)
│   │   ├── billing/ (4 elementos)
│   │   │   ├── company_profiles.html (13.1KB)
│   │   │   ├── plans_list.html (16.0KB)
│   │   │   ├── purchase_detail_modal.html (10.4KB)
│   │   │   └── purchases_list.html (16.4KB)
│   │   ├── certificates/ (4 elementos)
│   │   │   ├── edit_modal.html (6.1KB)
│   │   │   ├── list.html (24.5KB)
│   │   │   ├── upload_modal.html (5.9KB)
│   │   │   └── view_modal.html (9.1KB)
│   │   ├── companies/ (3 elementos)
│   │   │   ├── form_modal.html (16.8KB)
│   │   │   ├── list.html (20.2KB)
│   │   │   └── view_modal.html (8.4KB)
│   │   ├── notifications/ (2 elementos)
│   │   │   ├── list.html (14.9KB)
│   │   │   └── settings.html (23.6KB)
│   │   ├── profile/ (4 elementos)
│   │   │   ├── change_password.html (13.6KB)
│   │   │   ├── edit.html (3.1KB)
│   │   │   ├── manage_sessions.html (12.4KB)
│   │   │   └── profile.html (14.7KB)
│   │   ├── settings/ (1 elementos)
│   │   │   └── list.html (23.8KB)
│   │   ├── sri_documents/ (1 elementos)
│   │   │   └── list.html (29.6KB)
│   │   ├── users/ (3 elementos)
│   │   │   ├── form_modal.html (9.7KB)
│   │   │   ├── list.html (21.6KB)
│   │   │   └── view_modal.html (6.8KB)
│   │   ├── base.html (34.2KB)
│   │   └── dashboard.html (12.8KB)
│   ├── dashboard/ (3 elementos)
│   │   ├── admin_dashboard.html (22.4KB)
│   │   ├── no_companies.html (7.5KB)
│   │   └── user_dashboard.html (78.0KB)
│   ├── email_templates/ (0 elementos)
│   ├── socialaccount/ (1 elementos)
│   │   └── authentication_error.html (13.3KB)
│   └── users/ (3 elementos)
│       ├── account_rejected.html (10.7KB)
│       ├── login.html (49.8KB)
│       └── waiting_room.html (12.0KB)
├── tests/ (2 elementos)
│   ├── fixtures/ (0 elementos)
│   └── __init__.py (0B)
├── utils/ (1 elementos)
│   └── __init__.py (0B)
├── vendo_sri/ (6 elementos)
│   ├── __init__.py (378.0B)
│   ├── asgi.py (425.0B)
│   ├── celery.py (8.8KB)
│   ├── settings.py (32.3KB)
│   ├── urls.py (15.1KB)
│   └── wsgi.py (425.0B)
├── .env (5.3KB)
├── .gitignore (4.0KB)
├── docker-compose.yml (1.6KB)
├── dockerfile (1.7KB)
├── DOCUMENTACION_COMPLETA.md (32.0KB)
├── documenter.py (36.0KB)
├── manage.py (687.0B)
├── requirements.txt (1003.0B)
├── startup_certificates.sh (7.6KB)
└── test_sendgrid.py (2.3KB)

================================================================================
                            ANÁLISIS DE ARCHIVOS
================================================================================

ARCHIVOS IMPORTANTES
--------------------
manage.py                 ✅ Existe (687.0B)
requirements.txt          ✅ Existe (1003.0B)
.env                      ✅ Existe (5.3KB)
.env.example              ❌ Faltante
.gitignore                ✅ Existe (4.0KB)
README.md                 ❌ Faltante
docker-compose.yml        ✅ Existe (1.6KB)
Dockerfile                ❌ Faltante
pytest.ini                ❌ Faltante
setup.cfg                 ❌ Faltante

ESTADÍSTICAS POR EXTENSIÓN
--------------------------
.py                   192 archivos ( 43.0%)
.js                   107 archivos ( 23.9%)
.html                  34 archivos (  7.6%)
.css                   26 archivos (  5.8%)
.svg                   23 archivos (  5.1%)
.png                   23 archivos (  5.1%)
.log                   11 archivos (  2.5%)
(sin extensión)         4 archivos (  0.9%)
.txt                    4 archivos (  0.9%)
.jpg                    4 archivos (  0.9%)

TOTALES
-------
Total de archivos: 447
Total de directorios: 149

================================================================================
                           APLICACIONES DJANGO
================================================================================

ESTADO DE LAS APPS
--------------------------------------------------------------------------------
App                  Estado     Básicos    Total      Archivos Existentes      
--------------------------------------------------------------------------------
notifications        Parcial    4/5      7          models.py, views.py, urls.py...
billing              Completa   5/5      12         models.py, views.py, urls.py...
api                  Parcial    2/5      16         models.py, urls.py       
users                Completa   5/5      11         models.py, views.py, urls.py...
core                 Completa   5/5      10         models.py, views.py, urls.py...
sri_integration      Completa   5/5      28         models.py, views.py, urls.py...
settings             Completa   5/5      7          models.py, views.py, urls.py...
certificates         Completa   5/5      12         models.py, views.py, urls.py...
custom_admin         Parcial    4/5      4          models.py, views.py, urls.py...
invoicing            Completa   5/5      7          models.py, views.py, urls.py...
companies            Parcial    4/5      11         models.py, views.py, urls.py...

DETALLE POR APP
==================================================

📦 App: notifications
   Ubicación: apps/notifications/
   Estado: Parcial
   Archivos básicos: 4/5
   Archivos encontrados: models.py, views.py, urls.py, apps.py, serializers.py
   ❌ Archivos faltantes: admin.py

📦 App: billing
   Ubicación: apps/billing/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, forms.py, tests.py, signals.py
   ✅ Todos los archivos básicos presentes

📦 App: api
   Ubicación: apps/api/
   Estado: Parcial
   Archivos básicos: 2/5
   Archivos encontrados: models.py, urls.py
   ❌ Archivos faltantes: views.py, admin.py, apps.py

📦 App: users
   Ubicación: apps/users/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, signals.py
   ✅ Todos los archivos básicos presentes

📦 App: core
   Ubicación: apps/core/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py
   ✅ Todos los archivos básicos presentes

📦 App: sri_integration
   Ubicación: apps/sri_integration/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, serializers.py
   ✅ Todos los archivos básicos presentes

📦 App: settings
   Ubicación: apps/settings/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, serializers.py
   ✅ Todos los archivos básicos presentes

📦 App: certificates
   Ubicación: apps/certificates/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, forms.py, serializers.py, signals.py
   ✅ Todos los archivos básicos presentes

📦 App: custom_admin
   Ubicación: apps/custom_admin/
   Estado: Parcial
   Archivos básicos: 4/5
   Archivos encontrados: models.py, views.py, urls.py, apps.py
   ❌ Archivos faltantes: admin.py

📦 App: invoicing
   Ubicación: apps/invoicing/
   Estado: Completa
   Archivos básicos: 5/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, apps.py, serializers.py
   ✅ Todos los archivos básicos presentes

📦 App: companies
   Ubicación: apps/companies/
   Estado: Parcial
   Archivos básicos: 4/5
   Archivos encontrados: models.py, views.py, urls.py, admin.py, forms.py, serializers.py
   ❌ Archivos faltantes: apps.py

================================================================================
                         CONFIGURACIÓN DJANGO
================================================================================

✅ ARCHIVO settings.py ENCONTRADO
----------------------------------------
INSTALLED_APPS       ❌ Faltante      Apps instaladas
DATABASES            ✅ Configurado   Configuración de BD
REST_FRAMEWORK       ✅ Configurado   API REST Framework
STATIC_URL           ✅ Configurado   Archivos estáticos
DEBUG                ✅ Configurado   Modo debug
SECRET_KEY           ✅ Configurado   Clave secreta

================================================================================
                         PAQUETES PYTHON
================================================================================

PAQUETES REQUERIDOS PARA SRI
----------------------------
Django                    ❌ Faltante      No instalado    (Req: 4.2.7)
djangorestframework       ❌ Faltante      No instalado    (Req: 3.14.0)
psycopg2-binary           ❌ Faltante      No instalado    (Req: 2.9.7)
python-decouple           ❌ Faltante      No instalado    (Req: 3.8)
celery                    ❌ Faltante      No instalado    (Req: 5.3.4)
redis                     ❌ Faltante      No instalado    (Req: 5.0.1)
cryptography              ❌ Faltante      No instalado    (Req: 41.0.7)
lxml                      ❌ Faltante      No instalado    (Req: 4.9.3)
zeep                      ❌ Faltante      No instalado    (Req: 4.2.1)
reportlab                 ❌ Faltante      No instalado    (Req: 4.0.7)
Pillow                    ❌ Faltante      No instalado    (Req: 10.1.0)
drf-spectacular           ❌ Faltante      No instalado    (Req: 0.26.5)
django-cors-headers       ❌ Faltante      No instalado    (Req: 4.3.1)


TODOS LOS PAQUETES INSTALADOS
-----------------------------

================================================================================
                    ESTRUCTURA DE ALMACENAMIENTO SEGURO
================================================================================

DIRECTORIOS DE STORAGE
----------------------
storage/certificates/encrypted/     ❌ Certificados .p12 encriptados 
storage/certificates/temp/          ❌ Temporal para procesamiento 
storage/invoices/xml/               ✅ Facturas XML firmadas (2 archivos)
storage/invoices/pdf/               ✅ Facturas PDF generadas (1 archivos)
storage/invoices/sent/              ❌ Facturas enviadas al SRI 
storage/logs/                       ✅ Logs del sistema (7 archivos)
storage/backups/                    ✅ Respaldos de BD (0 archivos)
media/                              ❌ Archivos de media 
static/                             ✅ Archivos estáticos (12 archivos)
uploads/                            ❌ Archivos subidos 

================================================================================
                         ANÁLISIS Y PRÓXIMOS PASOS
================================================================================

ARCHIVOS FALTANTES CRÍTICOS
---------------------------
❌ README.md

APPS DJANGO SIN CONFIGURAR
------------------------------
❌ notifications - Parcial
❌ api - Parcial
❌ custom_admin - Parcial
❌ companies - Parcial

TAREAS PRIORITARIAS
===================

1. COMPLETAR APPS DJANGO
   Crear archivos faltantes en:
   - notifications: admin.py
   - api: views.py, admin.py, apps.py
   - custom_admin: admin.py
   - companies: apps.py

2. CREAR DOCUMENTACIÓN
   - README.md con instrucciones de instalación
   - Documentación de API

COMANDOS ÚTILES
===============
# Instalar dependencias
pip install -r requirements.txt

# Aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Ejecutar servidor
python manage.py runserver

================================================================================
                                MÉTRICAS FINALES
================================================================================

PROGRESO DEL PROYECTO
---------------------
Estructura básica:       ✅ Completada (100%)
Configuración Django:    ⚠️  Parcial (80%)
Apps implementadas:      ❌ Pendiente (64%)
Documentación:           ⚠️  Iniciada (20%)

ESTADÍSTICAS GENERALES
---------------------
Total directorios:       149
Total archivos:          447
Apps Django:             11
Archivos Python:         192
Paquetes instalados:     0

================================================================================
Reporte generado automáticamente el 2025-09-16 18:52:04
Para actualizar, ejecuta: python documenter.py
================================================================================